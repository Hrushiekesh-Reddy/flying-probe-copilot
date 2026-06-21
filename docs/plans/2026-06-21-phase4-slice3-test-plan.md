# Test Plan — Phase 4 Slice 3: GitHub Actions (lint + tests + screenshot recapture)

**Date:** 2026-06-21
**Phase:** 4 — Polish & Portfolio, slice 3
**Author:** Step 4 sub-agent (test-generator role)
**Step:** 4 of 12 (Test-Case Plan)
**Inputs:**
- [Brief](2026-06-21-phase4-slice3-brief.md) — D1-D4 ratified
- [Plan](2026-06-21-phase4-slice3-plan.md) — §3 file table + §4 E1-E10 Execute steps
- `pyproject.toml` (current state) — to be edited at E5
- `tests/conftest.py` + `tests/test_scripts/conftest.py` — fixture patterns to mirror
- `tests/test_scripts/test_capture_screenshots.py` — example unit test style

**Output:** This document. Behavior-level test cases ONLY. The executor (Step 7) turns these into Python.

**Scope reminder:** I am READ-ONLY. I do not edit any file except this one and I do not spawn other agents.

---

## Section A — Test environment + fixtures

### A.1 Required conftest fixtures

Plan §4.E1 proposes `_workflow_dir` (Path) + `_load_yaml(name)` helper. **That is sufficient as a baseline**, but the test plan extends with two more lightweight helpers so individual tests stay 3-8 lines each:

| Fixture / helper | Type | Scope | Purpose |
|---|---|---|---|
| `_workflow_dir` | `pathlib.Path` | session | `Path(__file__).resolve().parents[2] / ".github" / "workflows"` — repo-root anchored, immune to cwd drift |
| `_load_yaml` | callable `(name: str) -> dict` | session (memoized) | `yaml.safe_load(open(workflow_dir / name, encoding="utf-8"))` — single read per (name) per session |
| `_load_yaml_text` | callable `(name: str) -> str` | session (memoized) | Returns raw workflow file text — needed for substring checks like "GOOGLE_API_KEY does NOT appear" and for `hashFiles(...)` regex inspection where YAML parsing loses the literal string |
| `_pyproject` | `dict` | session | `tomllib.load(open(REPO_ROOT / "pyproject.toml", "rb"))` — Section D tests load it once |

**Why session-scope, not function-scope:**
- The workflow YAML files do not change during a test session — re-reading per test wastes I/O and (more importantly) hides regressions where one test mutates the loaded dict.
- To guard against mutation leakage, tests **must treat the dict as read-only** (no `.update()`, no `.pop()`, no `del`). Any test that needs to mutate makes a `copy.deepcopy` explicitly. This is a convention, not enforced by code — exec sub-agent must follow.
- `tests/test_scripts/conftest.py` precedent: that file uses `autouse=True` for env-stripping but no session-scope caches; we add session caches here for the read-heavy YAML loading.

**No autouse env-strip required** in `tests/test_ci/conftest.py` — these tests don't call any LLM or read `GOOGLE_API_KEY`. The string-search tests are the opposite: they assert the workflow files themselves do not reference the secret.

### A.2 Required imports

| Import | Why | Stdlib? |
|---|---|---|
| `pathlib.Path` | path arithmetic | Yes |
| `yaml` (PyYAML) | `yaml.safe_load` for workflow files | No — already a main dep in `pyproject.toml` line 16 (`pyyaml>=6.0`) |
| `tomllib` | parse `pyproject.toml` for ruff config checks | Yes (Python 3.11+; matches our `requires-python = ">=3.11"`) |
| `re` | regex for `hashFiles(...)` literal inspection + path-filter superset check | Yes |
| `pytest` | parametrize + fixtures | already dev-dep |

**No new dependencies required.** Notably: `yaml.safe_load` (not `yaml.load`) is mandatory — agent-conduct demands no unsafe deserializers and CI workflows have no Python tags that would warrant the full loader.

### A.3 Fixture-leakage guard

Add one **paranoid sanity test** at the top of the file:

- `test_workflow_dir_resolves_under_repo_root` — asserts `_workflow_dir.is_dir()` and that `_workflow_dir.parent.parent / "pyproject.toml"` exists. Catches a misconfigured `parents[2]` if the test file ever moves.

---

## Section B — Test cases for `.github/workflows/ci.yml`

All test functions in `tests/test_ci/test_workflow_yaml.py`. Names follow `test_<area>_<condition>_<expected>` convention (`.claude/rules/testing.md`).

| # | Test name | What it tests | How it asserts | Why it matters |
|---|---|---|---|---|
| B-01 | `test_ci_yml_exists` | `.github/workflows/ci.yml` is a file | `(_workflow_dir / "ci.yml").is_file()` | Foundation: every other ci.yml test relies on it; pinpoints "file missing" vs "file malformed" |
| B-02 | `test_ci_yml_parses` | `yaml.safe_load` returns a dict with `"name"`, `"on"`, `"jobs"` top-level keys | `set(data) >= {"name", "on", "jobs"}` and `data["name"] == "ci"` | Catches YAML indentation errors; pins the workflow name visible in the Actions UI |
| B-03 | `test_ci_yml_triggers_on_pull_request` | `on.pull_request` is defined | `"pull_request" in data["on"]` (note: PyYAML may parse `on:` as bool `True`; assert that the loader returns dict, not the special `True` key — handled by D-3 documented in Section H) | If absent, CI never runs; the whole slice is dead |
| B-04 | `test_ci_yml_targets_dev_and_main` | `on.pull_request.branches` is a list containing both `"dev"` and `"main"` | `set(data["on"]["pull_request"]["branches"]) >= {"dev", "main"}` | Brief §8 + Plan E3 contract — feature → dev → main flow |
| B-05 | `test_ci_yml_paths_ignore_docs` | `on.pull_request.paths-ignore` contains `"docs/**"` AND `"**/*.md"` | Both substrings present in the list | D12 ratified: docs-only PRs skip CI |
| B-06 | `test_ci_yml_has_lint_job` | `jobs.lint` exists with `runs-on` + `steps` | `"lint" in data["jobs"]`; `"runs-on" in data["jobs"]["lint"]`; `"steps" in data["jobs"]["lint"]` | Foundation for B-07/B-08; pinpoints "missing job" |
| B-07 | `test_ci_yml_has_tests_job` | `jobs.tests` exists with `runs-on` + `steps` | Same shape as B-06 for `"tests"` | Foundation for B-08/B-09 |
| B-08 | `test_ci_yml_lint_job_runs_ruff_check_and_format` | At least one step's `run` contains `ruff check`; another contains `ruff format --check` | Iterate `jobs.lint.steps`, collect every `step.get("run", "")`, assert two predicates against joined text | D15 ratified: ruff check (lint) + ruff format --check (no auto-fix). Catches accidental swap to `ruff format` (without `--check` flag, would auto-mutate) |
| B-09 | `test_ci_yml_tests_job_runs_pytest_with_coverage` | At least one step's `run` invokes `pytest` AND `--cov=src` | Same iteration pattern; assert both substrings appear in the same `run` step (not just somewhere in the job) | Catches the regression of running pytest without coverage (Plan §1 acceptance criterion: ≥97%) |
| B-10 | `test_ci_yml_uses_python_311` | Every `setup-python` action uses `python-version: "3.11"` | Filter steps where `step.get("uses", "").startswith("actions/setup-python")`; assert `step["with"]["python-version"] == "3.11"` (string, NOT float — `3.11` as float gets coerced to `3.1`, breaking the runner) | Brief §8 non-decision: 3.11 only. Catches the YAML-float-coercion trap |
| B-11 | `test_ci_yml_concurrency_cancel_in_progress` | Top-level `concurrency.cancel-in-progress` is True AND `concurrency.group` is set | `data["concurrency"]["cancel-in-progress"] is True` and `data["concurrency"]["group"]` is a non-empty str | D9 ratified: saves CI minutes on rapid-fire pushes |
| B-12 | `test_ci_yml_permissions_contents_read` | Top-level `permissions.contents` is `"read"` | `data["permissions"]["contents"] == "read"` | D10 ratified: least privilege. Catches a sloppy `write-all` regression |
| B-13 | `test_ci_yml_both_jobs_use_ubuntu_latest` | Every job's `runs-on` is `"ubuntu-latest"` | For job in `data["jobs"].values()`: `job["runs-on"] == "ubuntu-latest"` | Brief §8 non-decision; catches matrix-creep |
| B-14 | `test_ci_yml_both_jobs_have_timeout_minutes` | Every job declares `timeout-minutes` as a positive int | For job in `data["jobs"].values()`: `isinstance(job.get("timeout-minutes"), int) and job["timeout-minutes"] > 0` | R1 mitigation (Plan §8): catches infinite-hang regression; specific value (5 vs 15) NOT asserted (range freedom for tuning) |
| B-15 | `test_ci_yml_tests_job_timeout_at_least_10` | `jobs.tests.timeout-minutes >= 10` | Direct compare | Soft floor — the full 566-test suite + cold uv-cache install fits in <10 min today; lower than that risks flake. NOT a ceiling (executor can pick 15 per Plan §4.E3) |
| B-16 | `test_ci_yml_lint_job_timeout_at_most_10` | `jobs.lint.timeout-minutes <= 10` | Direct compare | Ruff on this codebase runs in seconds; a 30-min lint timeout would be a copy-paste bug |
| B-17 | `test_ci_yml_uses_actions_checkout_v4` | Every `actions/checkout` step pins `@v4` (not v3 which deprecates 2024-12) | Filter `step.get("uses", "")` starts with `actions/checkout`; assert ends with `@v4` | Brief §8 + GH deprecation calendar |
| B-18 | `test_ci_yml_installs_uv_via_setup_uv_action` | At least one step in EACH job uses `astral-sh/setup-uv@v3` | Per job: any step with `uses` starting `astral-sh/setup-uv` AND ending `@v3` | Plan E3 contract; catches manual `pip install uv` regression (slower, less deterministic) |
| B-19 | `test_ci_yml_uv_sync_uses_frozen_and_all_groups` | At least one `run` step in each job invokes `uv sync` with both `--frozen` AND `--all-groups` | Per job: any `step.get("run", "")` contains all three substrings | `--frozen` enforces lockfile determinism; `--all-groups` includes dev (ruff, pytest, playwright); both required by Plan §4.E3 |
| B-20 | `test_ci_yml_no_google_api_key_reference` | The raw file text does NOT contain `GOOGLE_API_KEY` | `"GOOGLE_API_KEY" not in _load_yaml_text("ci.yml")` | Guardrail §7.3 (brief): no API keys in CI. Catches an accidental "test with real LLM" step |
| B-21 | `test_ci_yml_no_anthropic_api_key_reference` | Same for `ANTHROPIC_API_KEY` | `"ANTHROPIC_API_KEY" not in _load_yaml_text("ci.yml")` | Same guardrail; covers the backup LLM provider |
| B-22 | `test_ci_yml_no_secrets_block_at_all` | The string `secrets.` does not appear in raw file | `"secrets." not in _load_yaml_text("ci.yml")` | Stronger guardrail: slice 3 needs no secret at all. If a future slice adds one, it should land in a separate workflow file with explicit owner approval |
| B-23 | `test_ci_yml_no_push_trigger` | `on.push` is NOT present | `"push" not in data["on"]` | Brief §8 non-decision: PR triggers only. Catches the accidental "run on every push to dev too" regression that doubles CI minutes |
| B-24 | `test_ci_yml_lint_job_uses_github_output_format` | At least one ruff-check step uses `--output-format=github` | Substring search in lint job `run` text | D15 ratified: inline PR annotations. Catches the silent regression where output-format defaults to plain text (no inline annotations) |
| B-25 | `test_ci_yml_tests_job_runs_pytest_quiet` | At least one pytest step uses `-q` (or the longer `--quiet`) | Substring search in tests job `run` text | Plan E3 contract; not load-bearing but anchors the verbosity contract — extremely loud pytest output blows the GH Actions log limit on a full failure run |

**Subtotal Section B: 25 test cases.**

---

## Section C — Test cases for `.github/workflows/screenshots.yml`

| # | Test name | What it tests | How it asserts | Why it matters |
|---|---|---|---|---|
| C-01 | `test_screenshots_yml_exists` | File is present | `(_workflow_dir / "screenshots.yml").is_file()` | Foundation |
| C-02 | `test_screenshots_yml_parses` | `yaml.safe_load` returns dict with `name`, `on`, `jobs` and `name == "screenshots"` | Standard shape + name | Catches YAML errors; pins UI name |
| C-03 | `test_screenshots_yml_triggers_on_pull_request_to_dev_and_main` | `on.pull_request.branches` contains both `"dev"` and `"main"` | Same as B-04 | Mirrors ci.yml branch-targeting contract |
| C-04 | `test_screenshots_yml_paths_filter_covers_ui_analytics_kb_scripts` | `on.pull_request.paths` is a SUPERSET of the 5 required globs | `expected = {"src/flying_probe_copilot/ui/**", "src/flying_probe_copilot/analytics/**", "docs/knowledge-base/**", "scripts/capture_screenshots.py", "scripts/_capture_app.py"}`; `expected <= set(data["on"]["pull_request"]["paths"])` | Brief §3 + Plan §3 row 5: any of these 5 should retrigger recapture. Subset (not equality) so executor can add more paths without breaking the test |
| C-05 | `test_screenshots_yml_paths_filter_excludes_docs_md` | The path list does NOT contain `"docs/**"` or `"**/*.md"` (those would over-trigger) | Negative assertion: `"docs/**" not in paths` and `"**/*.md" not in paths` | Catches the copy-paste bug where ci.yml's `paths-ignore` accidentally appears as screenshots.yml's `paths` |
| C-06 | `test_screenshots_yml_has_capture_job` | `jobs.capture` exists with `runs-on` + `steps` + `timeout-minutes` | Shape check | Foundation |
| C-07 | `test_screenshots_yml_capture_job_runs_on_ubuntu_latest` | `jobs.capture.runs-on == "ubuntu-latest"` | Direct compare | Brief §8 |
| C-08 | `test_screenshots_yml_timeout_minutes_15` | `jobs.capture.timeout-minutes == 15` | Exact int compare | Brief §3 + R4 mitigation (Plan §8). Exact value pinned because the budget is tight (~3-4 min cold capture + sample-DB build + dep install) |
| C-09 | `test_screenshots_yml_uses_actions_checkout_v4` | Checkout step pins `@v4` | Same logic as B-17 | GH deprecation calendar |
| C-10 | `test_screenshots_yml_uses_setup_uv_v3` | uv setup uses `astral-sh/setup-uv@v3` | Per B-18 logic | Plan E4 contract |
| C-11 | `test_screenshots_yml_uses_setup_python_311` | setup-python pins `"3.11"` (string) | Per B-10 | Same trap (float coercion) |
| C-12 | `test_screenshots_yml_installs_playwright_with_deps_chromium` | A `run` step contains `playwright install --with-deps chromium` | Substring search across capture job's `run` steps | Plan E4: `--with-deps` pulls libnss3/libatk1.0 (required on bare ubuntu-latest). `chromium` not `all` (faster install) |
| C-13 | `test_screenshots_yml_uv_sync_uses_frozen_and_all_groups` | uv sync uses `--frozen` AND `--all-groups` | Per B-19 | Required: dev group has playwright |
| C-14 | `test_screenshots_yml_uses_actions_cache_v4_for_sample_db` | At least one step uses `actions/cache@v4` with `path: data/db/sample.duckdb` | Filter steps where `step.get("uses", "").startswith("actions/cache")`; assert ends with `@v4`; assert `step["with"]["path"]` contains `data/db/sample.duckdb` | D1 + D8 ratified: cache the sample DB. v4 because v3 deprecates 2025 |
| C-15 | `test_screenshots_yml_cache_key_uses_hashFiles` | The cache step's `key` references `hashFiles(...)` | `re.search(r"hashFiles\(", step["with"]["key"])` | D8: cache must be content-keyed, not constant (constant key = stale-forever cache = silent bug) |
| C-16 | `test_screenshots_yml_cache_key_includes_generator_parser_buildscript` | The cache key's `hashFiles(...)` includes substrings for generator, parser, and build-portfolio-data.sh | Substring search inside the cache `key` value: `"generator/**"`, `"parser/**"`, `"build-portfolio-data.sh"` | D8 ratified composition. Catches the "I forgot the parser" key drift that ships a stale DB |
| C-17 | `test_screenshots_yml_cache_key_includes_uv_lock` | Cache key references `uv.lock` | Substring search | D8 explicitly chose to include `uv.lock` (a dep bump could change ingest behavior). Asserting it is in the key locks D8 into the workflow |
| C-18 | `test_screenshots_yml_build_db_step_runs_on_cache_miss_only` | The "build sample DB" step has an `if:` referencing `cache-hit != 'true'` | Iterate steps; find the one whose `run` contains `build-portfolio-data.sh`; assert its `if` contains both `cache-hit` and `!= 'true'` | D1: build runs ONLY on cache miss. Without the `if:`, the build runs every time, defeating the cache. Specific quote-syntax for `'true'` because YAML conflates `true` (bool) with `'true'` (string), and GH's expression engine requires the string form |
| C-19 | `test_screenshots_yml_build_db_step_references_cache_step_id` | The `if:` references `steps.<id>.outputs.cache-hit` where `<id>` matches the cache step's `id` field | Find cache step's `id`; assert build step's `if` contains `steps.{id}.outputs.cache-hit` | Catches the typo `steps.cache.outputs.cache-hit` when the cache step's id is actually `cache-db`. Cross-step reference integrity |
| C-20 | `test_screenshots_yml_invokes_capture_script_all_mode` | A `run` step invokes `scripts/capture_screenshots.py all` | Substring search | Brief §3 + Plan E4: full hero strip + gif, not a single page |
| C-21 | `test_screenshots_yml_capture_script_uses_out_flag` | The capture script invocation includes `--out` and points at a path under `docs/img-ci/` | Substring search for `--out docs/img-ci` | Plan E4: outputs go to `docs/img-ci/`, NOT `docs/img/` (which is the committed location). Catches the "I overwrote the committed screenshots with the CI ones" disaster |
| C-22 | `test_screenshots_yml_uploads_artifact_with_retention_14` | At least one `actions/upload-artifact@v4` step has `retention-days: 14` | Filter steps with `uses` starting `actions/upload-artifact`; assert `@v4`; assert `with.retention-days == 14` | D2 + Brief §3: 14 days is enough for reviewer eyeball cycle. NOT 7 (too short on weekend PRs), NOT 90 (wasteful) |
| C-23 | `test_screenshots_yml_upload_artifact_name_is_descriptive` | The artifact name matches the contract `"recaptured-dashboard-screenshots"` | `step["with"]["name"] == "recaptured-dashboard-screenshots"` | Plan E4 contract; reviewer searches the Actions UI by this name |
| C-24 | `test_screenshots_yml_upload_artifact_path_is_docs_img_ci` | The artifact path is `docs/img-ci/` (matches C-21 output dir) | `"docs/img-ci" in step["with"]["path"]` | Cross-step coherence: if the capture writes to `docs/img-ci/` but upload reads from `docs/img/`, the artifact is empty — silent regression |
| C-25 | `test_screenshots_yml_concurrency_cancel_in_progress` | Top-level `concurrency.cancel-in-progress` is True | Per B-11 | D9: saves CI minutes on rapid pushes — UI iteration is the screenshot workflow's main caller |
| C-26 | `test_screenshots_yml_permissions_contents_read` | Top-level `permissions.contents == "read"` | Per B-12 | D10: least privilege; D2 explicitly chose artifacts-only over PAT-write |
| C-27 | `test_screenshots_yml_no_google_api_key_reference` | Raw text does NOT contain `GOOGLE_API_KEY` | Substring on `_load_yaml_text("screenshots.yml")` | Guardrail §7.3 + brief §3 invariant: the shim covers the Co-Pilot capture, no real key needed |
| C-28 | `test_screenshots_yml_no_anthropic_api_key_reference` | Same for `ANTHROPIC_API_KEY` | Substring | Same guardrail |
| C-29 | `test_screenshots_yml_no_push_trigger` | `on.push` not present | `"push" not in data["on"]` | Mirror of B-23; recapture should fire on PR only |
| C-30 | `test_screenshots_yml_no_secrets_block` | `secrets.` substring absent | Substring | Mirror of B-22 |

**Subtotal Section C: 30 test cases.**

---

## Section D — Test cases for `pyproject.toml` ruff config

All test functions in `tests/test_ci/test_workflow_yaml.py` (per Plan §4.E2: exec may split into `test_pyproject_lint.py` — either is acceptable; test names below are file-agnostic).

| # | Test name | What it tests | How it asserts | Why it matters |
|---|---|---|---|---|
| D-01 | `test_pyproject_declares_ruff_dev_dep` | `[dependency-groups].dev` contains an entry whose string starts with `"ruff"` AND has a version constraint (`>=`, `~=`, `==`, `^`) | Iterate dev list; check `any(s.startswith("ruff") and any(op in s for op in (">=", "~=", "==", "^")) for s in dev)` | Plan §4.E5: must be `ruff>=0.6`. Tighter than just "ruff in list" — catches an unpinned `"ruff"` that breaks lock determinism |
| D-02 | `test_pyproject_ruff_dev_dep_floor_at_least_0_6` | The ruff entry's lower bound is ≥ 0.6 | Parse the constraint string; compare to `Version("0.6")` using `packaging.version.Version` (already imported by `tests/test_scripts/test_capture_screenshots.py` precedent — confirmed importable) | D5 ratified ruleset uses ruff lint API; 0.6+ is the first stable version with the `--output-format=github` flag |
| D-03 | `test_pyproject_ruff_section_exists` | `[tool.ruff]` table is present | `"ruff" in pyproject["tool"]` and `isinstance(pyproject["tool"]["ruff"], dict)` | Foundation for D-04..D-09 |
| D-04 | `test_pyproject_ruff_target_version_py311` | `[tool.ruff].target-version == "py311"` | Direct compare | Matches `project.requires-python = ">=3.11"`. Catches the drift where target stays on py38 (old default) and ruff auto-applies syntax modernization the runtime can't take |
| D-05 | `test_pyproject_ruff_line_length_set` | `[tool.ruff].line-length` is a positive int | `isinstance(..., int) and ... > 0` | Plan E5 specifies 100; we assert positive-int (not exact 100) so executor can tune within the line-length policy without breaking the test. **EXCEPTION:** also assert `>= 88` (Black default) and `<= 120` (ergonomic ceiling) — outside that range is a typo |
| D-06 | `test_pyproject_ruff_extend_exclude_covers_data_docs_notebooks` | `[tool.ruff].extend-exclude` contains `"data"`, `"docs"`, `"notebooks"` | Subset check on the list | Plan E5 + brief §3: ruff should not blow up on generated synthetic data or third-party notebook patterns |
| D-07 | `test_pyproject_ruff_extend_exclude_covers_claude_dir` | extend-exclude contains `".claude"` | Subset check | `.claude/` has its own hook scripts; ruff lint of governance code is out-of-scope this slice (D7 spirit: don't surface unrelated issues) |
| D-08 | `test_pyproject_ruff_lint_section_exists` | `[tool.ruff.lint]` table exists | Nested-dict access | Foundation for D-09/D-10 |
| D-09 | `test_pyproject_ruff_lint_select_contains_core_rules` | `[tool.ruff.lint].select` is a list containing all of `{"E", "F", "W", "I"}` | `{"E", "F", "W", "I"} <= set(select)` | D5 minimal ruleset; superset allowed (executor can add `B`/`UP`/`SIM` if owner ratifies at Step 6) |
| D-10 | `test_pyproject_ruff_lint_select_excludes_unknown_codes` | All entries in `select` match `^[A-Z]+[0-9]*$` | `all(re.match(r"^[A-Z]+[0-9]*$", code) for code in select)` | Catches typos like `"e"` (lowercase, ignored silently by ruff) or `"E5O1"` (letter-O typo) |
| D-11 | `test_pyproject_ruff_tests_have_per_file_ignores` | `[tool.ruff.lint.per-file-ignores]` has `"tests/**"` key with at least `"E501"` | `"E501" in ignores["tests/**"]` | D6 ratified: test files routinely exceed line-length for parametrize matrices and long descriptive names |
| D-12 | `test_pyproject_ruff_tests_per_file_ignores_includes_f401` | per-file-ignores for `tests/**` includes `"F401"` (unused import) | Subset check | D6: test files often `import` modules only to assert the module is importable (e.g., `tests/test_scripts/` precedent line 33 `from playwright.sync_api import sync_playwright  # noqa: F401`). Without F401 in ignores, every such test needs a manual `# noqa` |
| D-13 | `test_pyproject_ruff_format_block_exists` | `[tool.ruff.format]` is a table (can be empty for defaults) | `isinstance(pyproject["tool"]["ruff"]["format"], dict)` | Plan E5: empty-but-present table signals "we considered formatter config and chose defaults" — empty means the table CAN be absent in TOML, but presence is required so the format step in ci.yml has an explicit declaration |
| D-14 | `test_pyproject_dev_deps_remain_alphabetized` | The `[dependency-groups].dev` list is sorted alphabetically | `dev == sorted(dev)` | Plan §4.E5 brief: `ruff>=0.6` is inserted "alphabetized last". Catches a future regression where someone appends out-of-order. Order: `playwright`, `pytest`, `pytest-cov`, `ruff` |
| D-15 | `test_pyproject_no_mypy_dev_dep_added` | No entry in `[dependency-groups].dev` starts with `mypy` | `not any(s.startswith("mypy") for s in dev)` | D4 ratified: ruff only, no mypy this slice. Catches scope creep at the dep level |
| D-16 | `test_pyproject_project_requires_python_311_unchanged` | `project.requires-python == ">=3.11"` (unchanged) | Direct compare | Slice 3 must NOT bump Python floor — defense for "I went and added 3.12 syntax in ruff config" |
| D-17 | `test_pyproject_existing_main_deps_unchanged` | All 10 entries in `project.dependencies` from the pre-slice baseline are still present | Subset check against the hardcoded list in the test | Slice 3 should add ZERO main deps. Catches the regression where someone adds `mypy-extensions` to main and the linter never flags it because mypy isn't required |

**Subtotal Section D: 17 test cases.**

---

## Section E — Cross-workflow tests

These belong in `test_workflow_yaml.py` adjacent to the per-file sections; they assert invariants spanning BOTH workflow files.

| # | Test name | What it tests | How it asserts | Why it matters |
|---|---|---|---|---|
| E-01 | `test_no_workflow_uses_secrets_google_api_key` | Neither `ci.yml` nor `screenshots.yml` references `secrets.GOOGLE_API_KEY` | For each: `"secrets.GOOGLE_API_KEY" not in _load_yaml_text(name)` AND `"GOOGLE_API_KEY" not in _load_yaml_text(name)` | Guardrail; double-coverage of B-20 + C-27 but at the cross-workflow level so adding a third workflow file later still triggers this test (parametrize over a hardcoded workflow list) |
| E-02 | `test_no_workflow_uses_secrets_anthropic_api_key` | Same for `ANTHROPIC_API_KEY` | Mirror of E-01 | Backup-LLM secret coverage |
| E-03 | `test_no_workflow_uses_any_secrets_substring` | The bare string `secrets.` does not appear in either workflow | `"secrets." not in _load_yaml_text(name)` for each | Strongest form: if any secret is added in a future PR, the developer must consciously edit this test, surfacing the change at review time |
| E-04 | `test_both_workflows_have_concurrency_block` | Both files declare a top-level `concurrency` block | For each: `"concurrency" in data` AND `data["concurrency"].get("cancel-in-progress") is True` | D9 universal; mirrors B-11 + C-25 but as a cross-file invariant |
| E-05 | `test_both_workflows_have_permissions_contents_read` | Both have top-level `permissions.contents == "read"` | For each: `data.get("permissions", {}).get("contents") == "read"` | D10 universal; mirrors B-12 + C-26 |
| E-06 | `test_both_workflows_pin_jobs_to_ubuntu_latest` | Every job in every workflow uses `runs-on: ubuntu-latest` | Nested iteration | Brief §8; mirrors B-13 + C-07 |
| E-07 | `test_both_workflows_use_actions_checkout_v4` | Every `actions/checkout` step pins `@v4` | Nested iteration over jobs + steps | GH deprecation; mirrors B-17 + C-09 — cross-file ensures a third workflow file later inherits the rule |
| E-08 | `test_both_workflows_use_actions_setup_python_v5` | Every `actions/setup-python` step pins `@v5` | Same pattern | Catches drift to v4 (deprecates 2024-12). NOT covered by B/C individually because the test name didn't pin a version |
| E-09 | `test_both_workflows_set_python_version_as_string_not_float` | `setup-python.with.python-version` is always a string `"3.11"`, never the float `3.11` | `isinstance(v, str)` AND `v == "3.11"` | THE classic GH Actions trap. YAML `3.11` parses as float 3.11 which prints as `3.1` and matches Python 3.1 (nonexistent on runner) → install failure with cryptic error. Quoting is mandatory. Mirrors B-10 + C-11 but at the type level |
| E-10 | `test_both_workflows_have_top_level_name_field` | Both have `data["name"]` as a non-empty string | `isinstance(data["name"], str) and data["name"]` | Pin the Actions-UI display name; catches the missing-name regression that surfaces a workflow as `.github/workflows/ci.yml` instead of `ci` in the UI |
| E-11 | `test_workflow_file_count_is_exactly_two` | `_workflow_dir` contains exactly 2 `*.yml` files: `ci.yml` and `screenshots.yml` | `set(p.name for p in _workflow_dir.glob("*.yml")) == {"ci.yml", "screenshots.yml"}` | Guardrail: catches an accidental third workflow being added without owner sign-off (e.g., a copy-paste `ci copy.yml`). Forces explicit decision at Step 6 if a new workflow is needed |

**Subtotal Section E: 11 test cases.**

---

## Section F — Tests explicitly excluded (out-of-scope)

The following test ideas were considered and rejected. Documented here so red-team (Step 5) can confirm they should remain excluded.

| # | Excluded test | Why excluded |
|---|---|---|
| F-01 | Assert specific commit SHAs for actions (e.g., `actions/checkout@a5ac7e51b41094c92402da3b24376905380afc29`) | Security-scanning tools (Dependabot, GHCR scanners) do this better. SHA-pinning at the test level creates maintenance churn on every action minor bump |
| F-02 | Assert exact `steps` order by integer index (e.g., `steps[0].uses == "actions/checkout@v4"`) | Brittle to reordering. Use predicate-presence (`any(s["uses"].startswith(...))`) for the contracts that matter. Relative-order checks via a sentinel scan would be added only if a specific bug demanded it |
| F-03 | Assert exact `timeout-minutes` values to the minute (e.g., `lint.timeout-minutes == 5`) | Range checks (B-15, B-16) are enough. Executor needs latitude to tune within sane bounds without breaking the test |
| F-04 | Parse `act` (local GH Actions runner) output to simulate full CI run | `act` is a dev-experience chip per brief §6, not slice 3 scope. Real CI run at Step 11 is the integration test |
| F-05 | Assert ruff rule set EXACTLY equals `["E", "F", "W", "I"]` (no extras) | D5 explicitly leaves room for owner to expand to `B`/`UP`/`SIM` at Step 6. Subset check (D-09) covers the floor; ceiling would block legitimate expansion |
| F-06 | Test that `uv run ruff check .` exit 0 on the codebase | This is a Step 7 Execute concern, not a unit test. Would also be slow + non-deterministic across ruff minor releases. Plan §4.E7 covers it as part of Execute |
| F-07 | Test that the workflows actually trigger correctly in a real GH event | Plan §4 Step 11 (Manual QA) covers via owner pushing the branch. Unit tests for the GH event-routing system would mock more than they assert |
| F-08 | Test the `actions/cache` save logic (does it write back on failure?) | GH Actions cache behavior is well-documented; testing it would mean asserting against a documentation contract. R3 mitigation is observational, not test-mocked |
| F-09 | Test the artifact upload's max file size limit | GH Actions limit is 10 GB per artifact; our 6 JPGs + 748 KB gif is ~1.5 MB. Asserting a soft limit creates false security |
| F-10 | Test that `playwright install --with-deps` installs the exact right system packages | OS-package decisions live in Playwright's own repo; testing them here would couple slice 3 to upstream details |
| F-11 | Test the cache miss path actually rebuilds the DB (i.e., run `build-portfolio-data.sh` in test) | Slice 3 invariant: scripts/ is read-only. Running the script in unit tests is a behavioral test of the script, not the workflow YAML |
| F-12 | Test the YAML linter (`yamllint`) passes on both files | `yaml.safe_load` already catches syntax errors at parse time (B-02, C-02). `yamllint` adds style rules out-of-scope for slice 3 |
| F-13 | Test that the workflows behave correctly when the `dev` branch doesn't exist (initial-repo case) | This repo has `dev` (D3, established Phase 0). Defensive test for an impossible state |
| F-14 | Assert ruff `format` rule details (quote-style, indent-style, etc.) | D-13 asserts the `[tool.ruff.format]` table exists with defaults. Asserting specifics would lock down ergonomics the owner may want to tune |
| F-15 | Cross-check that `docs/img-ci/` is in `.gitignore` | Plan §4.E4 explicitly defers `.gitignore` edit. The path is CI-only; never exists locally |
| F-16 | Test that the workflows pass `actionlint` (third-party static checker) | Adds a third-party install to CI; D11 spirit (no third-party uploaders this slice) |
| F-17 | Test that the workflows post a PR comment with coverage | Brief §3 explicitly defers PR comments to slice 4. Job-summary is in-scope; comment is out |

---

## Section G — Estimated complexity

### G.1 Test count

| Section | Test count |
|---|---|
| A (env / paranoid sanity) | 1 (`test_workflow_dir_resolves_under_repo_root`) |
| B (ci.yml) | 25 |
| C (screenshots.yml) | 30 |
| D (pyproject.toml ruff) | 17 |
| E (cross-workflow) | 11 |
| **Total new tests** | **84** |

This exceeds the brief's "≥10 new test-ci tests" and the Plan's "15+ baseline" — comfortably. Excluding any single section still satisfies the brief floor; the comprehensiveness is deliberate because CI is a one-shot integration where regressions are invisible until the next PR.

### G.2 LOC estimate

| Item | LOC |
|---|---|
| `tests/test_ci/__init__.py` | 1 (empty) |
| `tests/test_ci/conftest.py` | ~50 (4 fixtures + memoized helpers + 1 sanity test) |
| `tests/test_ci/test_workflow_yaml.py` | ~480 (84 tests × ~5 LOC + section headers + imports) |
| **Total** | **~530 LOC** |

Average LOC per test: 5-7 (assertion-rich, fixture-dense). Outliers:
- D-02 (version parsing): ~10 LOC (parse + compare)
- C-19 (cross-step `id` reference integrity): ~12 LOC (two-pass scan)
- C-18 (build-step `if` condition): ~10 LOC (find step + multi-substring assert)

### G.3 Fixtures beyond the baseline `_workflow_dir` / `_load_yaml`

- `_load_yaml_text(name)` — needed for raw-string substring tests (B-20..22, C-15..17, C-27..28, E-01..03)
- `_pyproject` — needed for Section D (tomllib-loaded dict)

Both are session-scope, memoized. Both are read-only — tests must NOT mutate.

### G.4 Parametrize candidates (reduce duplication)

Several tests are natural `@pytest.mark.parametrize` candidates. The executor MAY collapse:

- E-01 + E-02 → one parametrized test over `["GOOGLE_API_KEY", "ANTHROPIC_API_KEY"]`
- E-04 / E-05 / E-06 / E-07 / E-08 / E-09 / E-10 → parametrize over `[("ci.yml", ...), ("screenshots.yml", ...)]` to halve LOC
- B-17 + B-18 + C-09 + C-10 → parametrize across (workflow, action-prefix, expected-version) tuples

If executor parametrizes, the test count in pytest's output may show fewer functions (e.g., 60) but the parametrize cases must still each have a distinct identifier in the test ID for failure isolation. Total **84 cases** stands; the function count is flexible.

### G.5 Estimated wall-clock

84 tests × ~5 ms each (pure-YAML / pure-TOML, no I/O after session-scope load) = **~0.4 s suite-time**. Negligible against the existing 566-test baseline.

---

## Section H — Open questions for Step 5 (red-team) and Step 6 (Decision Gate)

These are test-related decisions I could not resolve from the brief + plan + Explore report. They will likely surface as red-team findings or new decisions at Step 6.

### H.1 PyYAML `on:` key trap

PyYAML 6.x parses bare `on:` (without quotes) as the YAML boolean `True`, not the string `"on"`. So `data["on"]` may KeyError; correct access could be `data[True]`. The workflow YAML in Plan §4.E3 uses bare `on:`. **Test plan assumes the executor quotes `"on":` or that PyYAML 6 handles it via the default loader.** Worth verifying in red-team — and if quote is required, B-03/C-03 must use `data.get("on") or data.get(True)`.

**Recommended resolution:** Plan E3/E4 explicitly quote `"on":` in the workflow YAML so `data["on"]` works. (Alternative: every test uses a helper `_get_on(data)` that handles both.)

### H.2 Should `paths-ignore` use `"**/*.md"` separately from `"docs/**"`?

Plan §4.E3 shows both. README is at repo root, not under `docs/`, so a README-only PR would re-trigger CI if only `docs/**` were excluded. B-05 asserts both are present. Red-team should confirm there's no scenario where excluding `"**/*.md"` accidentally skips a test-code PR (no — `.md` is not `.py`).

### H.3 Cache `id` field naming — `cache-db` vs `cache-sample` vs `db-cache`

C-18/C-19 assume the cache step has an `id` (so the build step's `if:` can reference `steps.<id>.outputs.cache-hit`). Plan §4.E4 uses `id: cache-db`. Test plan asserts the cross-reference works regardless of the name — the test reads the `id` dynamically and asserts the `if:` matches. **No new decision needed; just confirmation that the executor follows the dynamic-id pattern.**

### H.4 Should D-14 (alphabetized dev deps) be a soft warning or a hard fail?

Soft alphabetization is a style preference; a hard test makes future inserts annoying. **Recommended: hard test (D-14 stays).** Justification: the current 4-entry list is small enough that alphabetization is trivially maintainable; the test catches the lazy-append regression that snowballs over years.

### H.5 Should the test plan assert `--cov-report=term` (or `term-missing`) explicitly?

`pyproject.toml` line 37 declares `addopts = "--cov=src/flying_probe_copilot --cov-report=term-missing"`. The CI tests job runs `uv run pytest -q --cov=src --cov-report=term`, which OVERRIDES the addopts. B-09 only asserts `--cov=src`. Should we also assert `--cov-report=term` so the CI summary is visible?

**Recommended:** Add a B-26 if red-team agrees: `test_ci_yml_tests_job_emits_coverage_report` — assert `--cov-report=term` or `--cov-report=term-missing` appears in the pytest run step. Decision for Step 6.

### H.6 Should we test that `[tool.ruff.lint.per-file-ignores]` covers `notebooks/**` and `data/**`?

D-07 covers `extend-exclude`. Should per-file-ignores ALSO list `notebooks/**`? Strictly: `extend-exclude` already removes notebooks from the lint corpus, so per-file-ignores would be dead config. **Recommended: leave the test plan as-is (no test for notebooks per-file-ignores).** Confirm with red-team.

### H.7 D-02 `packaging.version` import

`packaging` is a transitive dep (pulled in by pip/setuptools/many libs); we don't declare it explicitly. `tests/test_scripts/test_capture_screenshots.py` line 43 already imports it without issue. **Recommended: rely on the transitive availability.** If red-team flags it, the alternative is a regex compare (looser but stdlib-only).

### H.8 Should `test_workflow_file_count_is_exactly_two` (E-11) be a hard pin or a soft floor?

Hard pin (`== {"ci.yml", "screenshots.yml"}`) catches accidental adds AND legitimate adds. Soft floor (`>= {...}`) catches only accidental removes. **Recommended: hard pin (E-11 stays as written).** A legitimate new workflow file in a future slice forces an explicit test update, surfacing the decision at review.

### H.9 Should there be a test that the workflow YAML files have a trailing newline?

Git convention; many tools complain on no-trailing-newline. **Recommended: skip.** Trailing-newline rules belong in `.editorconfig` / ruff format, not in CI shape tests. Out of scope.

### H.10 Should we test that `actions/setup-python` runs AFTER `astral-sh/setup-uv` in each job?

Order matters: uv brings its own Python installer if asked, and `setup-python` overrides PATH. Plan §4.E3 ordering is `checkout → setup-uv → setup-python → uv sync`. Wrong order = uv installs its own Python and `setup-python` orphans. **Recommended: add a soft B-27 / C-32 if red-team confirms.** Step-order assertions are usually brittle (F-02 excludes them), but this specific ordering is a known footgun. **Suggest moving to red-team for confirmation; if green-lit, add: `test_<workflow>_setup_uv_before_setup_python`** — assert the index of the `setup-uv` step is less than the index of the `setup-python` step.

### H.11 Should D-01..D-17 live in a separate file `tests/test_ci/test_pyproject_lint.py`?

Plan §4.E2 leaves the choice to the executor. Argument for separation: failure surfaces clearly as "pyproject" vs "workflow YAML". Argument against: 17 tests in their own file is overhead. **Recommended: defer to executor.** Either works; the test count is the contract, not the file split.

### H.12 Should we test that `playwright install` uses `--with-deps chromium`, NOT `--with-deps all`?

C-12 asserts `--with-deps chromium`. Should we also assert `--with-deps all` is NOT used (since it's much slower)? **Recommended: skip the negative assertion.** Positive assertion (C-12) already catches the regression — if someone changes to `--with-deps all`, C-12 fails because the substring `chromium` is missing. Negative tests bloat the suite.

---

## Appendix A — Mapping back to Plan §4.E1 baseline

The Plan §4.E1 listed 15 baseline tests (then 16 with the screenshots cross-check). The test plan maps them 1-to-1 plus extensions:

| Plan E1 baseline | Section / # | Notes |
|---|---|---|
| `test_ci_yml_exists` | B-01 | Identical |
| `test_ci_yml_parses` | B-02 | Extended to also assert `name == "ci"` |
| `test_ci_yml_triggers_on_pull_request` | B-03 | Identical + H.1 caveat |
| `test_ci_yml_targets_dev_and_main` | B-04 | Identical |
| `test_ci_yml_has_lint_job` | B-06 | Identical |
| `test_ci_yml_has_tests_job` | B-07 | Identical |
| `test_ci_yml_lint_job_runs_ruff_check_and_format` | B-08 | Identical (with D15 ratification |
| `test_ci_yml_tests_job_runs_pytest_with_coverage` | B-09 | Identical |
| `test_ci_yml_uses_python_311` | B-10 | Identical (with the float-coercion trap noted) |
| `test_ci_yml_concurrency_cancel_in_progress` | B-11 | Identical (D9) |
| `test_ci_yml_permissions_contents_read` | B-12 | Identical (D10) |
| `test_ci_yml_paths_ignore_docs` | B-05 | Identical (D12) |
| `test_screenshots_yml_exists` | C-01 | Identical |
| `test_screenshots_yml_parses` | C-02 | Identical |
| `test_screenshots_yml_paths_filter_covers_ui_analytics_kb_scripts` | C-04 | Identical |
| `test_screenshots_yml_timeout_minutes_15` | C-08 | Identical |
| `test_screenshots_yml_installs_playwright_with_deps_chromium` | C-12 | Identical |
| `test_screenshots_yml_uses_actions_cache_for_sample_db` | C-14 | Extended to assert `@v4` pin |
| `test_screenshots_yml_uploads_artifact_with_retention_14` | C-22 | Identical |
| `test_screenshots_yml_no_google_api_key_reference` | C-27 | Identical |
| `test_no_workflow_uses_secrets_google_api_key` | E-01 | Identical (D10/D2 spirit) |
| `test_screenshots_yml_uses_hashFiles_in_cache_key` | C-15 | Identical (D8) |
| `test_screenshots_yml_build_step_only_on_cache_miss` | C-18 | Identical + C-19 cross-ref check |
| `test_screenshots_yml_invokes_capture_script` | C-20 | Extended to assert `all` mode |
| `test_pyproject_declares_ruff_dev_dep` | D-01 | Identical |
| `test_pyproject_ruff_target_version_py311` | D-04 | Identical |
| `test_pyproject_ruff_line_length_set` | D-05 | Identical |
| `test_pyproject_ruff_extend_exclude_covers_data_docs` | D-06 + D-07 | Split: docs/data/notebooks (D-06) + `.claude` (D-07) |
| `test_pyproject_ruff_lint_select_contains_core_rules` | D-09 | Identical |
| `test_pyproject_ruff_tests_have_per_file_ignores` | D-11 + D-12 | Split: E501 (D-11) + F401 (D-12) |
| `test_pyproject_ruff_format_block_exists` | D-13 | Identical |
| `test_no_workflow_uses_secrets_anthropic_api_key` | E-02 | Identical |
| `test_both_workflows_have_concurrency_block` | E-04 | Identical |
| `test_both_workflows_pin_to_ubuntu_latest` | E-06 | Identical |

**All 30 of the brief / plan baseline tests are covered.** The additional 54 tests (84 total - 30) are the extensions documented inline in their respective sections — primarily covering: ubuntu-latest invariance, timeout floors/ceilings, action version pinning (checkout v4, setup-uv v3, setup-python v5, cache v4, upload-artifact v4), cross-step `id` reference integrity, no-secrets defense in depth, ruff config completeness, and the pyproject baseline-preservation invariant.

---

## Appendix B — Triple-check budget hint for Step 9

Parent's Step 9 read should focus on:

1. **Section B-10 / C-11 / E-09** — the `"3.11"` string-vs-float trap. Read the actual YAML files (not the test) to confirm the value is quoted.
2. **Section C-18 / C-19** — the cache `if:` condition. Read the cache step + build step together; they must reference each other by ID.
3. **Section D-14** — alphabetized dev list. Read `pyproject.toml` directly.
4. **Section E-11** — exactly two workflow files. `Glob("*.yml", path=".github/workflows")` and count.
5. **Section H.1** — the `on:` key in PyYAML. Run `python -c "import yaml; print(list(yaml.safe_load(open('.github/workflows/ci.yml')).keys()))"` and confirm the key is `"on"` (string), not `True`.

Estimated parent read time: ~8 min (matches Plan §7).

---

## Appendix C — Handoff to Step 5 (red-team)

Red-team should adversarially review:

1. The **84 tests** for coverage holes (what contract is not asserted?)
2. The **17 excluded tests** in Section F — should any be reinstated?
3. The **12 open questions** in Section H — close each at Step 6 Decision Gate
4. **Section A.1 fixture scoping** — is session-scope safe given the no-mutation convention?
5. **D-02 `packaging.version` transitive import** — risky?
6. **H.1 PyYAML `on:` parsing** — verify with a quick `python -c` smoke against an actual GH Actions YAML snippet

Red-team artifact: `docs/plans/2026-06-21-phase4-slice3-redteam.md`.

---

**END OF TEST PLAN**
