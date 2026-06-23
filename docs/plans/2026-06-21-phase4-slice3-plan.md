# Plan — Phase 4 Slice 3: GitHub Actions (lint + tests + screenshot recapture)

**Date:** 2026-06-21
**Phase:** 4 — Polish & Portfolio, slice 3
**Tier:** Medium (12-step loop)
**Branch:** worktree `claude/sweet-jones-7291db` → rename to `feature/phase4-slice3-ci-workflows` at Step 10
**Author:** parent (per `.claude/rules/session-workflow.md` — planning is parent-only)
**Inputs:** [brief](2026-06-21-phase4-slice3-brief.md) (D1–D4 ratified) + Step 2 Explore report

---

## 1. Goal contract

**By end of slice 3:**

1. **Two NEW workflow files** under `.github/workflows/`:
   - `ci.yml` — lint (ruff) + tests (pytest 566-suite + coverage) on every PR to `dev` or `main`, single Python 3.11 / ubuntu-latest runner, parallel jobs.
   - `screenshots.yml` — path-filtered screenshot recapture on PRs touching `src/flying_probe_copilot/ui/**`, `src/flying_probe_copilot/analytics/**`, `docs/knowledge-base/**`, `scripts/capture_screenshots.py`, `scripts/_capture_app.py`. Uploads 6 JPGs + `demo.gif` as artifacts (14-day retention).
2. **One approval-gated `pyproject.toml` edit** — add `ruff>=0.6` to `[dependency-groups].dev` + `[tool.ruff]` and `[tool.ruff.format]` blocks (minimal rule set `["E", "F", "W", "I"]`).
3. **One NEW test package** `tests/test_ci/` with shape-validation tests for both YAML files.
4. **Suite green locally** — 566 passing / 5 skipped / 1 xfailed / 97% coverage **plus ≥10 new test-ci tests** = 576+ passing.
5. **Zero edits** to `src/flying_probe_copilot/**`, `.claude/**`, `.gitignore`, `.env.example`, `migrations/`, `scripts/capture_screenshots.py`, `scripts/_capture_app.py`, `scripts/build-portfolio-data.sh`, KB docs, or any existing test file.
6. **Documentation synced**: SESSION_LOG, DECISION_LOG, ROADMAP tick, CLAUDE.md status flip, AGENT_HANDOFF_LOG entry, plan artifacts.

**Not committed to slice 3** (out per brief §6):
- Repo public flip (slice 4)
- Branch-protection rules (slice 4)
- Mypy / strict typing
- Coverage-threshold gate (`--cov-fail-under=N`)
- Codecov / Coveralls
- Windows / macOS matrix
- Auto-commit of recaptured screenshots

---

## 2. Decision Index (what owner ratified vs what's pending)

### Already ratified at brief time (D1–D4)
| ID | Decision | Choice |
|---|---|---|
| D1 | CI sample-DB strategy | Cache build artifact (hash-keyed) |
| D2 | Recaptured-screenshot disposition | CI artifacts only |
| D3 | Public-flip timing | Hold until slice 4 |
| D4 | Lint stack | ruff only (no mypy) |

### Pending Step 6 (anticipated — surfaced by this Plan)
| ID | Decision | Recommended | Alternatives |
|---|---|---|---|
| D5 | Ruff rule set | `["E", "F", "W", "I"]` — pycodestyle + pyflakes + warnings + isort | Add `B` (bugbear) + `UP` (pyupgrade) + `SIM` (simplify) — more catches but higher Execute risk |
| D6 | Ruff per-file ignores | `tests/**`: `E501` (line length), `F401` (unused import) | None |
| D7 | If ruff surfaces real violations on Execute | Suppress per-line with `# noqa: <code>  # tracked in BUG-NNN` + create BUG_LOG entry + chip | Fix in-slice (scope creep) OR relax rule (loses catch) |
| D8 | Sample-DB cache key composition | `src/flying_probe_copilot/generator/**` + `src/flying_probe_copilot/parser/**` + `scripts/build-portfolio-data.sh` + `uv.lock` | Drop `uv.lock` (more cache hits but invariant looser) |
| D9 | `concurrency` cancel-in-progress | YES on both workflows — saves minutes on rapid pushes | NO — preserves run history per push |
| D10 | `permissions:` block | `contents: read` only (least privilege) | Default (broader, lazier) |
| D11 | Coverage threshold in ci.yml | NONE this slice (no `--cov-fail-under`) | Add `--cov-fail-under=95` (gates regressions but burns slice 4 follow-up) |
| D12 | `paths-ignore: docs/**` on ci.yml | YES — docs-only PRs skip tests | NO — every PR runs tests |
| D13 | `.gitattributes` add | NOT in slice 3 — `scripts/build-portfolio-data.sh` is LF in git index per `git ls-files --eol` (i/lf, w/crlf only in Windows working tree). ubuntu-latest checks it out LF. **NO action needed.** Downgrades Explore report's B-2 risk. | Add forward-safety `.gitattributes` (separate slice / chip) |
| D14 | Screenshot job paths-filter expectation | Job will NOT run on the slice-3 PR (no `src/ui/**` etc. paths touched). First live run = next UI-touching PR after slice 3 merges. **This is correct, not a bug.** | Force-run job in slice 3 PR via `workflow_dispatch` |
| D15 | Ruff CLI flags | `ruff check . --output-format=github` (inline PR annotations) + `ruff format --check .` (no auto-fix in CI) | `ruff check . --fix` (auto-fixes; conflicts with strict-review policy) |

### Coverage check (every brief §3 deliverable mapped to a Plan step)

| Brief §3 item | Plan step | File touched |
|---|---|---|
| `.github/workflows/ci.yml` | Step 7.E3 | NEW |
| `.github/workflows/screenshots.yml` | Step 7.E4 | NEW |
| `pyproject.toml` ruff add | Step 7.E5 | approval-gated |
| ROADMAP tick | Step 7.E10 | exec writes |
| CLAUDE.md status flip | Step 10 | parent writes |
| SESSION_LOG entry | Step 10 | parent writes |
| DECISION_LOG entries | Step 10 | parent writes |
| Plan artifacts | Step 1 + Step 3 (this doc) + Step 7 | all committed |

All deliverables covered.

---

## 3. What / Why / Where / When file table

| # | File | Action | What | Why | Where in repo | Step | Approval-gated? |
|---|---|---|---|---|---|---|---|
| 1 | `tests/test_ci/__init__.py` | CREATE | Empty package marker | pytest discovery | NEW `tests/test_ci/` | 7.E1 | No |
| 2 | `tests/test_ci/conftest.py` | CREATE | Shared `_workflow_dir` + `_load_yaml(name)` fixtures | DRY across the test module | NEW | 7.E1 | No |
| 3 | `tests/test_ci/test_workflow_yaml.py` | CREATE | ≥10 unit tests validating YAML shape + path filters + Python version + concurrency + permissions + artifact upload | G4 verification gate; covers each workflow's contract | NEW | 7.E1 (RED), 7.E3/E4 turn GREEN | No |
| 4 | `.github/workflows/ci.yml` | CREATE | lint job (`ruff check . --output-format=github` + `ruff format --check .`) + tests job (`uv sync --frozen --all-groups` + `uv run pytest -q --cov=src --cov-report=term`). ubuntu-latest, Python 3.11. `concurrency` + `permissions: contents: read`. `paths-ignore: docs/**`. | Brief §3 ci.yml deliverable | NEW `.github/workflows/` | 7.E3 | No (greenfield) |
| 5 | `.github/workflows/screenshots.yml` | CREATE | screenshot job. Triggers on `pull_request` to `dev`/`main` with `paths:` filter for UI/analytics/KB/capture-scripts. Steps: checkout → uv → sync → playwright install w/ deps chromium → actions/cache (sample DB) → bash sample-DB build (cache miss only) → run capture → upload-artifact. Timeout 15 min. `concurrency` cancel-in-progress. | Brief §3 screenshots.yml deliverable + D1 D2 | NEW `.github/workflows/` | 7.E4 | No (greenfield) |
| 6 | `pyproject.toml` | EDIT | Add `ruff>=0.6` to `[dependency-groups].dev` (alphabetized **before** `pytest`). Add `[tool.ruff]` block (`line-length = 100`, `target-version = "py311"`, `extend-exclude = ["data", "docs", "notebooks", ".claude"]`). Add `[tool.ruff.lint]` block (`select = ["E", "F", "W", "I"]`). Add `[tool.ruff.lint.per-file-ignores]` (`"tests/**" = ["E501", "F401"]`). Add `[tool.ruff.format]` block (defaults — no extra config). | D4 (ruff only) + D5 (minimal set) + D6 (test ignores) | Existing | 7.E5 | **YES** (declared at brief, ratified at Step 6) |
| 7 | `uv.lock` | EDIT (regen) | Auto-regenerated by `uv sync` after pyproject change | Lock determinism | Existing | 7.E6 | No (autogen) |
| 8 | `docs/ROADMAP.md` | EDIT | Tick `[ ] GitHub Actions workflow: lint + tests on PR` → `[x] (Phase 4 slice 3, 2026-06-21)` | Bookkeeping | Phase 4 §159-164 area | 10 | No |
| 9 | `CLAUDE.md` | EDIT | Status block: "slice 2 IN PR" → "slice 3 IN PR"; append session-log line | Bookkeeping | Status + session-log section | 10 | No (per `.claude/rules/agent-conduct.md` — `CLAUDE.md` is a documentation file, not in the approval-gated table) |
| 10 | `docs/logs/SESSION_LOG.md` | EDIT | New entry at top, ~70 lines | Bookkeeping | Top | 10 | No |
| 11 | `docs/logs/DECISION_LOG.md` | EDIT | D1–D15 entry block | Bookkeeping | Top | 10 | No |
| 12 | `docs/logs/AGENT_HANDOFF_LOG.md` | EDIT | New handoff to slice 4 at top | Bookkeeping | Top | 12 | No |
| 13 | `docs/plans/2026-06-21-phase4-slice3-brief.md` | already created | Slice brief | — | — | 1 | No |
| 14 | `docs/plans/2026-06-21-phase4-slice3-plan.md` | already created (this) | — | — | — | 3 | No |
| 15 | `docs/plans/2026-06-21-phase4-slice3-test-plan.md` | CREATE | Step 4 artifact | — | — | 4 | No |
| 16 | `docs/plans/2026-06-21-phase4-slice3-redteam.md` | CREATE | Step 5 artifact | — | — | 5 | No |
| 17 | `docs/plans/2026-06-21-phase4-slice3-decision-gate.md` | CREATE | Step 6 artifact | — | — | 6 | No |
| 18 | `docs/plans/2026-06-21-phase4-slice3-exec-report.md` | CREATE | Step 7-8 artifact | — | — | 7-8 | No |
| 19 | `docs/plans/2026-06-21-phase4-slice3-manual-qa.md` | CREATE | Step 11 owner script | — | — | 11 | No |

**Files explicitly NOT touched** (re-stated for the executor):
- `src/flying_probe_copilot/**` — any file
- `.claude/**` — any file
- `.gitignore` — see D13
- `.env.example` — approval-gated, no need
- `migrations/` — approval-gated, no need
- `src/flying_probe_copilot/db/schema.py` — approval-gated, no need
- `scripts/capture_screenshots.py` — CI calls but does not edit
- `scripts/_capture_app.py` — CI calls but does not edit
- `scripts/build-portfolio-data.sh` — CI calls but does not edit (D13 confirms no need)
- Any existing `tests/test_*/` directory or file
- README.md — slice-2 already embeds the gif; no badge add this slice (deferred chip — CI status badge after first green run)

---

## 4. Ordered Execute steps (TDD)

The Execute sub-agent runs these in order. **Each step is RED before GREEN.**

### E1. RED — `tests/test_ci/` test module + conftest
1. Create `tests/test_ci/__init__.py` (empty).
2. Create `tests/test_ci/conftest.py` with a `_workflow_dir` fixture pointing at `Path(".github/workflows")` and a `_load_yaml(name)` helper.
3. Create `tests/test_ci/test_workflow_yaml.py` with **15 test functions** per the [test plan](2026-06-21-phase4-slice3-test-plan.md):
   - `test_ci_yml_exists`
   - `test_ci_yml_parses`
   - `test_ci_yml_triggers_on_pull_request`
   - `test_ci_yml_targets_dev_and_main`
   - `test_ci_yml_has_lint_job`
   - `test_ci_yml_has_tests_job`
   - `test_ci_yml_lint_job_runs_ruff_check_and_format`
   - `test_ci_yml_tests_job_runs_pytest_with_coverage`
   - `test_ci_yml_uses_python_311`
   - `test_ci_yml_concurrency_cancel_in_progress`
   - `test_ci_yml_permissions_contents_read`
   - `test_ci_yml_paths_ignore_docs`
   - `test_screenshots_yml_exists`
   - `test_screenshots_yml_parses`
   - `test_screenshots_yml_paths_filter_covers_ui_analytics_kb_scripts`
   - `test_screenshots_yml_timeout_minutes_15`
   - `test_screenshots_yml_installs_playwright_with_deps_chromium`
   - `test_screenshots_yml_uses_actions_cache_for_sample_db`
   - `test_screenshots_yml_uploads_artifact_with_retention_14`
   - `test_screenshots_yml_no_google_api_key_reference`
   - `test_no_workflow_uses_secrets_google_api_key`

   (≥15 baseline; test plan may add more — minimum 10 per goal contract.)
4. **Run `uv run pytest tests/test_ci/ -q`** — must fail all 15+ (workflow files don't exist yet).

### E2. RED — pyproject.toml ruff sentinel test
1. Add a single test `test_pyproject_declares_ruff_dev_dep` in `tests/test_ci/test_workflow_yaml.py` (or a separate `test_pyproject_lint.py` — exec chooses) that loads `pyproject.toml` via `tomllib` and asserts:
   - `"ruff"` substring present in `[dependency-groups].dev` array
   - `[tool.ruff]` table exists
   - `[tool.ruff.lint].select` contains `{"E", "F", "W", "I"}`
   - `[tool.ruff.format]` table exists
2. **Run `uv run pytest tests/test_ci/ -q`** — must fail (no ruff config yet).

### E3. GREEN — Create `.github/workflows/ci.yml`

Skeleton (executor expands fully):

```yaml
name: ci
on:
  pull_request:
    branches: [dev, main]
    paths-ignore:
      - "docs/**"
      - "**/*.md"
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
permissions:
  contents: read
jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with: { enable-cache: true }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: uv sync --frozen --all-groups
      - run: uv run ruff check . --output-format=github
      - run: uv run ruff format --check .
  tests:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with: { enable-cache: true }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: uv sync --frozen --all-groups
      - run: uv run pytest -q --cov=src --cov-report=term
```

**Notes:**
- `astral-sh/setup-uv@v3` is the official uv installer action — handles the lockfile-keyed cache.
- `paths-ignore` is broad on purpose (docs-only PRs skip CI).
- Both jobs use `timeout-minutes` to fail-fast on hangs.
- No `--cov-fail-under` (D11).

**Run the 15+ ci.yml tests** — these GREEN now.

### E4. GREEN — Create `.github/workflows/screenshots.yml`

Skeleton (executor expands fully):

```yaml
name: screenshots
on:
  pull_request:
    branches: [dev, main]
    paths:
      - "src/flying_probe_copilot/ui/**"
      - "src/flying_probe_copilot/analytics/**"
      - "docs/knowledge-base/**"
      - "scripts/capture_screenshots.py"
      - "scripts/_capture_app.py"
concurrency:
  group: screenshots-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
permissions:
  contents: read
jobs:
  capture:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with: { enable-cache: true }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: uv sync --frozen --all-groups
      - name: Restore sample DuckDB
        id: cache-db
        uses: actions/cache@v4
        with:
          path: data/db/sample.duckdb
          key: sample-duckdb-${{ hashFiles('src/flying_probe_copilot/generator/**', 'src/flying_probe_copilot/parser/**', 'scripts/build-portfolio-data.sh', 'uv.lock') }}
      - name: Build sample DB (cache miss)
        if: steps.cache-db.outputs.cache-hit != 'true'
        run: bash scripts/build-portfolio-data.sh
      - run: uv run playwright install --with-deps chromium
      - name: Capture screenshots + gif
        run: uv run python scripts/capture_screenshots.py all --db data/db/sample.duckdb --out docs/img-ci/
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: recaptured-dashboard-screenshots
          path: docs/img-ci/
          retention-days: 14
```

**Notes:**
- Cache key includes `uv.lock` because a dep bump could change ingest behavior (D8 recommendation).
- `playwright install --with-deps chromium` ensures libnss3, libatk1.0, etc. on ubuntu-latest.
- Output dir `docs/img-ci/` is **NOT** committed (gitignore covers `docs/img-ci/**` if needed — but since CI runs in a fresh checkout, no dirty state). Add `docs/img-ci/` to `.gitignore`? **NO** — out of scope (would be approval-gated and CI doesn't push so the local dir never exists).

**Run the screenshots.yml tests** — these GREEN now.

### E5. GREEN — Approval-gated `pyproject.toml` edit

**This step requires the Step 6 owner ratification of D5/D6/D15 to be in hand.** Exec sub-agent halts and reports "blocked on owner ratification" if any of those are unresolved.

Add to `pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "playwright>=1.49",
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "ruff>=0.6",
]
```

(Insert `ruff>=0.6` alphabetized last in the array.)

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
extend-exclude = ["data", "docs", "notebooks", ".claude"]

[tool.ruff.lint]
select = ["E", "F", "W", "I"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["E501", "F401"]

[tool.ruff.format]
# defaults — line-ending = "auto", quote-style = "double", indent-style = "space"
```

**Run the pyproject sentinel test** — GREEN.

### E6. uv sync
1. `uv sync --frozen` — wait, no — pyproject changed, so `uv sync` (without `--frozen`) regenerates lockfile with ruff added.
2. Verify `uv.lock` updated (ruff>=0.6 pinned).
3. Re-run pyproject sentinel test.

### E7. Run ruff on the codebase
1. `uv run ruff check .` — capture exit code + violation count + first 20 lines of output to `docs/plans/2026-06-21-phase4-slice3-exec-report.md`.
2. `uv run ruff format --check .` — same.
3. **Branch A (exit 0)**: continue to E8.
4. **Branch B (violations)**: per D7, per-line `# noqa: <code>  # tracked in BUG-NNN` suppress + add BUG_LOG entry. Exec sub-agent stops and reports to parent for triage before any code edits.

### E8. Full suite green
1. `uv run pytest -q` — must report **576+ passing / 5 skipped / 1 xfailed / 97%+**.
2. If coverage drops below 97% on `src/`, FAIL — investigate.
3. Capture output in exec-report.

### E9. Bookkeeping (small)
1. Tick `docs/ROADMAP.md` Phase 4 deliverable for "GitHub Actions workflow: lint + tests on PR" → `[x] (Phase 4 slice 3, 2026-06-21)`.

### E10. Hand back to parent for Step 8 verification

---

## 5. Test cases (delegated to Step 4)

Test plan lives at [2026-06-21-phase4-slice3-test-plan.md](2026-06-21-phase4-slice3-test-plan.md). The test-generator subagent populates that file with the full RED-test list. The E1 step's 15+ tests above are the minimum guarantee.

---

## 6. Red-team scope (delegated to Step 5)

[2026-06-21-phase4-slice3-redteam.md](2026-06-21-phase4-slice3-redteam.md). Adversarial review of: YAML syntax, path-filter completeness, secret leakage in workflow logs, cache-key thrash, ruff rule-set realism, screenshot job timeout adequacy, Plan-vs-brief drift.

---

## 7. Triple-check budget (Step 9)

Parent reads (no sub-agent): both YAML files line-by-line, `pyproject.toml` diff, the 15+ test names, the exec-report Branch A/B decision trace. ~10 min.

---

## 8. Risk register (top 5, after Step 2 Explore)

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | First CI run on slice-3 PR fails due to YAML typo or missed secret | HIGH | Test plan E1 validates shape + parse; manual `python -c "import yaml; yaml.safe_load(...)"` smoke at Step 9; owner pushes early at Step 11 to catch in minutes |
| R2 | Ruff surfaces real violations in existing code → Execute scope creep | HIGH | D5 minimal rule set + D7 suppress-and-chip policy; exec sub-agent **must halt and report** if violations found |
| R3 | Sample-DB cache thrashes on every PR (key includes too much) | MED | D8 cache key composition reviewed at Step 5 red-team; can be tuned in slice 4 if observed flaky |
| R4 | Screenshot job times out at 15 min on cold runner | MED | Brief §3 timeout = 15 min; Explore F estimate = 3-4 min cold, well within budget; chip exists if hits ceiling |
| R5 | Workflow added in a PR does not run on that PR (path filter for screenshots.yml correctly NOT triggered on slice-3 PR) | LOW | D14 ratifies this is correct, not a bug; G5 caveat in brief is for ci.yml only |

---

## 9. Definition of Done re-stated (for the executor)

- [ ] All 19 files in §3 touched per the Action column
- [ ] `uv run ruff check .` exit 0 (or all violations suppressed with BUG_LOG entries per D7)
- [ ] `uv run ruff format --check .` exit 0
- [ ] `uv run pytest -q` reports ≥576 passing / 5 skipped / 1 xfailed / ≥97% coverage
- [ ] `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` exit 0
- [ ] Same for `screenshots.yml`
- [ ] No new entries under `src/flying_probe_copilot/**` or `.claude/**`
- [ ] Exec-report includes ruff dry-run output + suite output + a diff summary
- [ ] Plan-vs-Executed table at Step 8 is clean (no drift)

---

## 10. Handoff to Step 4

Next action: spawn **test-generator subagent** with the test list from §4.E1 + §4.E2 expanded to behavior-level cases. Test-plan artifact path: `docs/plans/2026-06-21-phase4-slice3-test-plan.md`.
