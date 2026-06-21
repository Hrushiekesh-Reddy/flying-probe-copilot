# Red-Team — Phase 4 Slice 3: GitHub Actions (lint + tests + screenshot recapture)

**Date:** 2026-06-21
**Phase:** 4 — Polish & Portfolio, slice 3
**Author:** Step 5 sub-agent (Verify Plan / adversarial red-team)
**Step:** 5 of 12
**Mandate:** READ-ONLY. Try to break the plan + test plan. No code edits.

**Inputs reviewed:**
- `CLAUDE.md` (slice 2 status block)
- `.claude/rules/agent-conduct.md`, `session-workflow.md`, `testing.md`
- `docs/GUARDRAILS.md`
- `docs/plans/2026-06-21-phase4-slice3-brief.md`
- `docs/plans/2026-06-21-phase4-slice3-plan.md` (§2 D1–D15, §3 file table, §4 E1–E10)
- `docs/plans/2026-06-21-phase4-slice3-test-plan.md` (84 tests, Section H open questions)
- `pyproject.toml`, `scripts/build-portfolio-data.sh`, `scripts/capture_screenshots.py`
- `tests/conftest.py`, `tests/test_scripts/conftest.py`

**Live verification performed:**
- `python -c "import yaml; yaml.safe_load('on:\n  pull_request:')"` → key is **`True`**, not `"on"`. Reproduced trap.
- `python -c "import yaml; yaml.safe_load('python-version: 3.11')"` → value is **`float 3.11`**, not str. Reproduced trap.
- `git ls-files --eol scripts/*.sh` → `i/lf` confirmed. D13 stands.
- WebFetch `https://github.com/astral-sh/setup-uv` → **current major is v8** (v8.2.0 as of 2026-06-03). Plan pins `@v3` — three majors stale.
- WebFetch GitHub Actions docs → `paths-ignore` semantics confirmed: PR touching both ignored + non-ignored paths **runs** the workflow. No silent-skip risk on mixed PRs.
- `ls .github/` → directory does not yet exist. Greenfield confirmed.
- Quote-style heuristic across `src/`: ~28:1 double:single. Ruff format default (double-quote) will not blanket-rewrite the codebase.

---

## Section 1 — Top-line verdict

**GO-WITH-CHANGES.** The plan is structurally sound: D1–D15 are coherent, the file table is complete, the TDD ordering is correct, and the test plan's 84 cases cover the workflow surface comprehensively. But **7 BLOCKERs** would cause the slice to either (a) fail at first CI run with a cryptic error (YAML float coercion, `on:` key trap, stale `setup-uv@v3`), (b) silently pass while masking a bug (ruff format false-pass on uninstalled tool, cache-key collapse on zero-glob-match, missing `scripts/` in `extend-exclude`), or (c) leak through the existing-code-edit guardrail (ruff format auto-rewriting `src/**` without owner sign-off). **Plan Revision 1 is required before Execute.** Six of the seven BLOCKERs are one-line fixes; the seventh (B-7: ruff format policy on existing code) needs Decision Gate ratification.

---

## Section 2 — BLOCKERs (must fix before Execute)

### B-1: PyYAML `on:` parses as boolean `True`, not string `"on"`

- **What.** YAML 1.1 (which PyYAML follows by default) lists `on`, `off`, `yes`, `no`, `true`, `false` as boolean tokens. Bare `on:` in the workflow YAML, loaded via `yaml.safe_load`, becomes the **Python boolean `True`** as a dict key. Live-verified: `list(yaml.safe_load("on:\n  pull_request:").keys()) == [True]`. So `data["on"]` raises `KeyError`; the access pattern that works is `data[True]`.
- **Where in the plan.** Plan §4.E3 + §4.E4 skeletons use bare `on:` (lines 164, 216 of the plan doc). Test plan §H.1 flagged this but **deferred resolution to red-team**. Tests B-03/B-04/B-05/B-23/C-03/C-29 all use `data["on"]` / `"on" in data["on"]` / `data["on"]["pull_request"]` — all would `KeyError` or assert `False` at GREEN.
- **Why it's a blocker.** Every `on`-related test in Sections B + C (≈10 tests) is wrong-by-construction. The workflow YAML itself would still work on GitHub (Actions runner handles YAML 1.1 correctly), so the bug only shows up in the test suite — but the suite breaking RED→GREEN cycle would force the executor to either (a) rewrite all `on`-access tests mid-Execute (scope creep against D7), or (b) deduce that the workflow YAML must be `"on":` quoted (untested combination).
- **Suggested closure.** **Plan Revision 1: explicitly quote `"on":` in both ci.yml and screenshots.yml skeletons.** Live-verified: `yaml.safe_load('"on":\n  pull_request:')` returns `{"on": {"pull_request": None}}` (string key). GitHub Actions accepts quoted `"on":` per spec. Update test plan Appendix B triple-check item #5 to reflect resolution. No fixture helper needed.

### B-2: PyYAML coerces `python-version: 3.11` to float `3.11`

- **What.** YAML 1.1 (and 1.2) treats unquoted `3.11` as a number. `yaml.safe_load("python-version: 3.11")["python-version"]` returns **float `3.11`** of type `float`. The `actions/setup-python` action stringifies it as `"3.11"` (so live CI may happen to work), but: (a) float `3.11` is not exactly representable in IEEE-754 — Python prints it as `3.11`, but on edge OSes the rounding can surface as `3.1100000000000003`; (b) `setup-python` historically has interpreted bare numerics as "latest 3.x" rather than "exactly 3.x.y" — behavior has shifted across action versions; (c) Section E-09's test `isinstance(v, str) and v == "3.11"` **fails** on the float — the test would never go GREEN.
- **Where in the plan.** Plan §4.E3 + §4.E4 skeletons: `with: { python-version: "3.11" }` — actually, looking at lines 184 and 238, these ARE already quoted (`"3.11"`). **The plan is correct.** But the test plan's B-10 / C-11 / E-09 assume the workflow YAML is correct; they enforce the contract. **HOWEVER**, the plan §4.E3 also has `with: { enable-cache: true }` for `setup-uv` — `true` is a bool, which is fine. The issue: **if the executor expands the inline `{python-version: "3.11"}` to a multi-line `with:` block without preserving the quotes**, the float trap reactivates. Common ambiguity in TDD-driven YAML scaffolding.
- **Why it's a blocker.** B-10 / C-11 / E-09 will catch this **only after** the float-bug ships. If the executor unquotes in any iteration, suite goes red. Worse: the lint job's first sub-step would say "could not find Python 3.1" with an opaque setup-python error.
- **Suggested closure.** **Plan Revision 1: add an explicit note to §4.E3 and §4.E4: "`python-version` MUST be a quoted string `"3.11"` in all expansions; never bare `3.11`."** Add an executor-visible callout at the top of both skeletons. Also tighten test E-09 to additionally assert `not isinstance(v, (int, float))`.

### B-3: `astral-sh/setup-uv@v3` is three majors stale

- **What.** Plan §4.E3 / §4.E4 / §8 non-decisions pin `astral-sh/setup-uv@v3`. WebFetch on `https://github.com/astral-sh/setup-uv` (2026-06-21) confirms **current major is v8** (v8.2.0 released 2026-06-03). The intermediate majors v4–v7 may all still resolve (GitHub Actions doesn't garbage-collect old tags), but a slice that bills itself as "CI hardening" and ships a 3-year-old action pin is failing a basic posture test. Worse: `setup-uv@v3` predates the action's stable cache-key contract — `enable-cache: true` may behave differently than expected (cache key includes lockfile hash automatically since v5; earlier versions required explicit `cache-dependency-glob`).
- **Where in the plan.** Plan §2 (non-decisions table is in brief §8), §4.E3 line 181, §4.E4 line 235. Tests B-18, C-10 hard-pin `@v3`.
- **Why it's a blocker.** (a) Posture / portfolio signal — slice 4 is a public launch event; a stale action pin invites first reviewer comment. (b) Cache-contract drift: if `setup-uv@v3` doesn't auto-hash `uv.lock`, the `uv sync --frozen` step won't benefit from caching and CI wall-clock balloons from ~30s warm to ~90s every run. (c) Tests B-18 and C-10 hard-pin `@v3` — a future bump requires test edits, inverting the "test the contract not the version" maxim.
- **Suggested closure.** **Plan Revision 1: bump to `astral-sh/setup-uv@v8`** (or use a `@v6` floor if the owner wants conservative). Update plan §4.E3 / §4.E4 skeletons. Update test plan B-18 + C-10 to assert `@v` followed by a digit ≥ 6 (regex: `r"@v[6-9]\d*$"`) rather than exact `@v3`. Also: brief §8 line 152 currently says "Use **uv** in CI" — keep that, just bump the version.

### B-4: `[tool.ruff].extend-exclude` omits `scripts/` — every CI run lints `scripts/_capture_app.py` + `capture_screenshots.py` + `build-portfolio-data.sh`

- **What.** Plan §4.E5 sets `extend-exclude = ["data", "docs", "notebooks", ".claude"]`. The `scripts/` directory contains the 432 LOC capture pipeline (`_capture_app.py`, `capture_screenshots.py`) plus a bash file. Ruff will lint the two Python files. **Brief §3 explicitly marks `scripts/capture_screenshots.py` and `scripts/_capture_app.py` as read-only this slice** (line 77). If ruff surfaces a real violation on those files, D7 says "suppress with `# noqa` + chip" — but that requires editing the file, which violates the read-only guardrail.
- **Where in the plan.** Plan §4.E5 lines 286-299; brief §3 lines 73-79; D7 wording in §2.
- **Why it's a blocker.** Two outcomes, both bad: (a) ruff is clean on scripts/ today → fine, until a future slice 4 capture-pipeline edit introduces a violation that blocks an unrelated PR; (b) ruff fires today → executor must either edit `scripts/_capture_app.py` (violates read-only guardrail) or relax `[tool.ruff.lint]` rules (loses the catch). The deadlock is unsolvable mid-Execute without a Plan revision.
- **Suggested closure.** **Plan Revision 1: choose one — (a) ADD `"scripts"` to `extend-exclude` for slice 3** (consistent with the "scripts is read-only" guardrail; gives the capture pipeline a clean grace period; ratify as new D16) **OR (b) explicitly re-scope brief §3 to allow `# noqa` edits to scripts/ files** (and only `# noqa`, nothing else) as a slice-3 exception (worse — opens an edit channel on a deliberately frozen surface). Recommended: **(a)**. Add new D16 to Plan §2 Decision Index and Test-Plan D-06/D-07 family with a `test_pyproject_ruff_extend_exclude_covers_scripts` test.

### B-5: `hashFiles(...)` cache key with `**` globs collapses to a constant when zero files match

- **What.** Plan §4.E4 cache key: `sample-duckdb-${{ hashFiles('src/flying_probe_copilot/generator/**', 'src/flying_probe_copilot/parser/**', 'scripts/build-portfolio-data.sh', 'uv.lock') }}`. GitHub Actions doc on `hashFiles`: returns SHA-256 of matched files' contents; **if zero files match, returns empty string**. Then the cache key becomes literally `sample-duckdb-` (constant). Effect: every PR shares the same cache slot regardless of generator code changes — silent staleness. Verification: `find src/flying_probe_copilot/generator -name "*.py"` returns 5 files. `find src/flying_probe_copilot/parser -name "*.py"` returns 4 files. Both currently match. **Risk:** any future slice that renames `generator/` or `parser/` to a new path (e.g., `pkg/generator/`) silently kills the cache invariant. The CI keeps "working" but ships a stale `sample.duckdb` for screenshots.
- **Where in the plan.** Plan §4.E4 line 245; D8 in §2; test plan C-15..C-17 assert hashFiles + substrings.
- **Why it's a blocker.** Silent staleness on screenshot artifacts is the highest-stakes failure mode of this slice — reviewer can't tell from the PR comment whether the rebuild ran. The cache-key shape is the only line of defense.
- **Suggested closure.** **Plan Revision 1: tighten the cache key with a non-glob anchor.** Two options: (a) include a directly-named file in each glob root (e.g., `'src/flying_probe_copilot/generator/cli.py'` — guaranteed to exist or the generator is broken), so even zero-match globs leave the hash non-empty; (b) prefix the key with a date or commit-SHA salt (e.g., `sample-duckdb-${{ github.sha }}-${{ hashFiles(...) }}` — but this thrashes the cache too aggressively). Recommended: **(a)** — add `cli.py` for each module as a single-file anchor. Update test plan C-16 to also assert the anchor file substrings.

### B-6: `uv sync --frozen --all-groups` is wrong — the correct flag is `--all-extras` for extras and `--all-groups` only for dependency-groups; verify the flag exists in the uv version targeted by `setup-uv@v3`

- **What.** Plan §4.E3 + §4.E4 use `uv sync --frozen --all-groups`. The `--all-groups` flag for dependency-groups was added in uv 0.5.x (late 2024). `setup-uv@v3` predates this — it pins older uv defaults. If the action installs a uv version that doesn't recognize `--all-groups`, every CI run fails at `uv sync` with `error: unexpected argument '--all-groups'`. Even if v3's bundled uv happens to be recent enough, **the flag wasn't documented as stable until 0.5.4**, and `setup-uv@v3` may pin a uv version below that.
- **Where in the plan.** Plan §4.E3 line 185, §4.E4 line 239; D-19 test asserts both `--frozen` AND `--all-groups`.
- **Why it's a blocker.** B-3 (setup-uv stale) compounds this: bumping to `setup-uv@v8` brings recent uv, which makes `--all-groups` reliable. But if the executor chooses to keep `@v3` for risk-aversion reasons, this flag is brittle. Worse: the dev group has playwright (CI needs it for screenshots.yml). If `--all-groups` is silently dropped, `playwright` doesn't install, and the screenshots job fails at `uv run playwright install` with `command not found`.
- **Suggested closure.** **Plan Revision 1: explicitly specify a uv version floor.** Either: (a) bump `setup-uv@v8` per B-3, which transitively guarantees recent uv (≥0.7); (b) add `with: { version: ">=0.5.4" }` to the setup-uv step to pin the uv version; (c) replace `--all-groups` with the older-stable `--all-extras` + restructure dependency-groups as extras. Recommended: **(a)** + **(b)** as belt-and-suspenders. Update tests B-19 / C-13 to assert the version pin.

### B-7: `ruff format --check .` policy on existing code — silent autoreformat risk and no preflight verification

- **What.** Plan §4.E7 runs `ruff format --check .` in CI; Plan §4.E5 declares `[tool.ruff.format]` with defaults. Ruff format's defaults are double-quote / 4-space indent / 88-char line (overridden to 100 in `[tool.ruff].line-length`). The codebase was developed without a formatter — there is no preflight evidence that `ruff format --check .` will be clean on existing `src/`, `tests/`, `scripts/`. **A single misaligned dict or extra blank line means CI fails on first PR.** Worse: D7 says "suppress with `# noqa`" — but `# noqa` doesn't suppress formatter violations (only lint). The only resolutions are (a) `ruff format .` (auto-rewrite the entire codebase — a massive untested change), (b) `--isolated` runs on subdirs only, (c) accept the failure. **None are in the plan.**
- **Where in the plan.** Plan §4.E7 line 309-313; D5/D6/D7 in §2; brief §3 line 62 "configured to pass the existing codebase OR with explicit `# noqa` markers" — but the `# noqa` clause is wrong for formatter rules.
- **Why it's a blocker.** A heuristic check on `src/` shows quote-style is double-dominant (~28:1) so blanket quote rewriting is unlikely. But indent / trailing-comma / line-wrap differences will exist — Streamlit-heavy `ui/views.py` has long Plotly call chains likely formatted by hand. If `ruff format --check .` fails on first run, executor's options are: (a) violate read-only `src/` guardrail to auto-format, (b) drop the format step (loses the catch), (c) restrict format to a narrower scope. All three are scope-creep at Execute time.
- **Suggested closure.** **Plan Revision 1 (requires Decision Gate ratification at Step 6 as a new D17):** add a preflight Execute step E0 that runs `uv run ruff format --check .` against the current codebase BEFORE the workflow files commit, and decide policy: (a) if clean → keep `ruff format --check .` in CI; (b) if dirty → either run `ruff format .` once (with owner approval to edit `src/**` as a one-time format pass, ratified as new D17), or drop `ruff format --check .` from ci.yml and leave only `ruff check .` (lint without format). Either resolution requires owner sign-off because option (b)(i) edits the read-only `src/**` surface. **Do not Execute until the preflight result is known.**

---

## Section 3 — WARNINGs (should fix, won't block)

### W-1: Cache scope is per-branch by default — feature-branch first run never hits `main` cache

- **What.** GitHub Actions cache scoping rule: a cache uploaded on branch X is readable by branch X and any branch created from X (after the cache upload). PRs from feature branches CAN read the base branch's cache, but only if the cache was uploaded after the feature branch was created. The slice-3 PR creates the workflow files for the first time — so the first cache upload happens on the slice-3 branch. Subsequent feature branches won't read it until merged.
- **Where in the plan.** Plan §4.E4; D8.
- **Why not a blocker.** First-run cache miss is the expected baseline. R3 (Plan §8) flags cache thrash but doesn't go this granular.
- **Suggested closure.** Add `restore-keys:` fallback so partial-match caches are usable: `restore-keys: |\n  sample-duckdb-` — lets feature branches with no exact match still pull a stale cache and rebuild incrementally. Update test plan C-15..C-17 to optionally also assert `restore-keys` presence (soft).

### W-2: Concurrency group `ci-${{ github.workflow }}-${{ github.ref }}` has redundant prefix

- **What.** `github.workflow` is already the workflow name (`ci`). Plan §4.E3 line 171 sets `group: ci-${{ github.workflow }}-${{ github.ref }}`. This expands to `ci-ci-refs/pull/123/merge` — the `ci-` prefix is duplicated. Functional, but ugly in the UI.
- **Where in the plan.** Plan §4.E3 line 171; §4.E4 line 225.
- **Why not a blocker.** Concurrency still works; just visually noisy.
- **Suggested closure.** Drop the literal `ci-` / `screenshots-` prefix: `group: ${{ github.workflow }}-${{ github.ref }}`. Update tests B-11 / C-25 / E-04 to assert presence of `github.workflow` and `github.ref`, not the literal prefix.

### W-3: `actions/setup-python@v5` is redundant with `astral-sh/setup-uv` (which can install Python)

- **What.** `setup-uv` (v6+) has `python-version:` input — installs Python via uv's own download. Plan stacks `setup-uv` THEN `setup-python` — two Python installs per job, with `setup-python` overriding PATH. Net: ~15-30s wasted per job × 3 jobs × every PR.
- **Where in the plan.** Plan §4.E3 + §4.E4 step ordering.
- **Why not a blocker.** Works correctly; just slower than needed.
- **Suggested closure.** Drop `actions/setup-python@v5`; pass `python-version: "3.11"` to `setup-uv` instead. Reduces CI wall-clock and removes Test E-08's purpose. If kept, test plan H.10 (setup-uv-before-setup-python) becomes load-bearing — add it.

### W-4: `paths-ignore: ["docs/**", "**/*.md"]` on ci.yml — README at repo root is `*.md` so a README-only PR correctly skips, but a `pyproject.toml`-only PR (no `*.md`, no `docs/**`) **runs** — fine; but a mixed PR touching `README.md + tests/foo.py` ALSO runs (per GitHub semantics), which is intended

- **What.** Confirmed via WebFetch: `paths-ignore` skips only when ALL changed paths match an ignore pattern. So a docs-only PR skips; mixed PRs run. Test plan B-05 asserts both patterns present — correct.
- **Where in the plan.** Plan §4.E3.
- **Why not a blocker.** Semantics are right; just call them out so the executor doesn't second-guess.
- **Suggested closure.** Add a comment in ci.yml: `# paths-ignore skips only when ALL changed paths match; mixed PRs still run.` Update test plan H.2 to note this is resolved.

### W-5: Test plan asserts `--cov=src` but the existing pytest addopts already has `--cov=src/flying_probe_copilot`

- **What.** `pyproject.toml` line 37: `addopts = "--cov=src/flying_probe_copilot --cov-report=term-missing"`. CI runs `uv run pytest -q --cov=src --cov-report=term`. Two cov sources collide: pytest-cov accepts multiple `--cov=` flags but the resulting coverage is the union — which actually undermines the `>=97%` floor because adding the top-level `src` directory may pick up new files outside the package and dilute the percentage. Test B-09 asserts `--cov=src`, but the local addopts uses `--cov=src/flying_probe_copilot`.
- **Where in the plan.** Plan §4.E3 line 198; test B-09.
- **Why not a blocker.** Suite passes either way; the 97% number may drift downward but not catastrophically.
- **Suggested closure.** Make CI's `--cov=src/flying_probe_copilot` match the local addopts; update B-09 to assert the full package path. (Or: rely entirely on the addopts and drop `--cov=` from CI's run.)

### W-6: Test plan §G.4 parametrize encouragement conflicts with §A.1 "treat dict as read-only" convention

- **What.** Parametrizing tests over `["ci.yml", "screenshots.yml"]` is fine, but the session-scope `_load_yaml(name)` is memoized — parametrized tests that each iterate over a dict's `jobs` may share mutable subviews. A parametrized test that does `for step in job["steps"]: step.pop("id")` would mutate the cached dict, breaking a later test. The convention is documented (§A.1) but not enforced.
- **Where in the plan.** Test plan §A.1 + §G.4.
- **Why not a blocker.** Convention-discipline issue, not a functional bug.
- **Suggested closure.** Either (a) make `_load_yaml` return `copy.deepcopy(...)` per call (small I/O cost; safest), or (b) freeze the dict via `MappingProxyType` (read-only at the Python level). Recommended: (a) — pytest fixtures rarely justify the complexity of (b).

### W-7: Test E-08 hard-pins `actions/setup-python@v5` — but W-3 recommends dropping setup-python entirely

- **What.** If W-3 is closed, E-08 becomes a test for a non-existent step.
- **Where.** Test plan E-08.
- **Why not a blocker.** Conditional — depends on W-3 resolution.
- **Suggested closure.** If W-3 is accepted, drop E-08; else keep.

### W-8: `[tool.ruff.lint.per-file-ignores]` "tests/**" — pattern needs to be relative to repo root and may need a `*` glob too

- **What.** Ruff's per-file-ignores keys are glob patterns matching file paths relative to the ruff invocation directory. `"tests/**"` matches `tests/test_ci/foo.py` but NOT `tests/test_ci/__init__.py` (the `**` recursive glob in ruff requires careful disambiguation between `tests/**` and `tests/**/*.py`). Verification needed.
- **Where.** Plan §4.E5; D-11 / D-12 tests.
- **Why not a blocker.** Likely works; ruff's glob semantics changed in 0.5 to be more permissive. But the test plan asserts presence of the key, not that the pattern actually matches the right files.
- **Suggested closure.** Either (a) verify by running `ruff check --show-files` (out of slice — chip), or (b) use the safer `"tests/**/*.py"` pattern. Recommended: **(b)** — pin the pattern explicitly.

### W-9: Test plan §H.7 `packaging.version` transitive import is genuinely fragile

- **What.** `packaging` is pulled in by setuptools / pip-internal — but uv-only environments may not ship it as a transitive. The test plan H.7 admits this; the recommendation is "rely on transitive availability". A clean `uv sync --frozen --all-groups` may not install `packaging` directly.
- **Where.** Test plan D-02 + H.7.
- **Why not a blocker.** Falls back to regex if `packaging` missing; alternative exists.
- **Suggested closure.** Use a regex-based version compare in D-02 (5 LOC) and drop the `packaging` import. Stdlib only. Closes H.7.

### W-10: `concurrency: cancel-in-progress: true` on screenshots.yml — owner's UI iteration workflow gets killed mid-capture

- **What.** D9 ratified cancel-in-progress for both workflows. For ci.yml (cheap, ~2-3 min), cancelling is correct. For screenshots.yml (cold-cache run ~5-8 min, hot run ~3-4 min), cancelling mid-capture on rapid pushes means: every quick "fix typo in CSS" iteration kills the previous in-flight capture. Net: the latest push always has to do a fresh ~5-min capture. The UI iteration workflow (slice 2 use case) wants to see screenshots from each push, not just the latest — cancel-in-progress strips that signal.
- **Where.** Plan §4.E4 line 224-226; D9.
- **Why not a blocker.** D9 is owner-ratified; this is a tunability concern.
- **Suggested closure.** Surface as a Step 6 decision tweak: **cancel-in-progress on ci.yml only; preserve in-flight runs on screenshots.yml** (UI reviewers want each push's artifact). Alternatively: keep D9 as-is and chip a follow-up if the owner observes the friction.

### W-11: Test plan E-11 `test_workflow_file_count_is_exactly_two` will fire false-positive on `.github/workflows/dependabot.yml` (or any future bot config)

- **What.** Dependabot config sometimes lives in `.github/workflows/` (incorrect but common); also CodeQL, Stale-bot, etc. Hard `==` pin in E-11 means any future workflow addition forces a test update. Owner-conscious by design (per H.8), but at the cost of being noisy.
- **Where.** Test plan E-11 + H.8.
- **Why not a blocker.** Trade-off is documented.
- **Suggested closure.** Keep H.8's resolution (hard pin), but add a comment in the test that documents the intent: "Any additional workflow file requires explicit owner sign-off at Decision Gate."

### W-12: Brief / plan don't specify the `Restore sample DuckDB` step's `id` field; test C-19 depends on it

- **What.** Plan §4.E4 line 241 shows `id: cache-db` — good. But test C-19 reads the cache step's `id` dynamically and asserts the build step's `if:` matches. If the executor renames `id` between the cache step and the `if:`, the test catches it. **However**, the test relies on the cache step having `id:` set at all. If the executor forgets `id:`, C-19 errors with `KeyError`, not a clean assertion fail.
- **Where.** Plan §4.E4; test plan C-18 + C-19.
- **Why not a blocker.** Caught at test time.
- **Suggested closure.** C-19 should defensively assert `"id" in cache_step` first with a clear error message; otherwise fall through to KeyError on a missing-id workflow.

---

## Section 4 — MINORs (nice-to-haves)

- **M-1.** Pin action versions to commit SHAs for supply-chain hardening (out of scope per F-01; reconsider in slice 4 around public flip).
- **M-2.** Add `permissions: { actions: read }` so the workflow can read its own artifacts (useful if a future job needs to download a prior artifact; not strictly required slice 3).
- **M-3.** Use `actions/cache/restore` + `actions/cache/save` split for explicit save-on-success-only semantics (vs. the default `actions/cache@v4` which saves on job end regardless).
- **M-4.** Add `if: github.event.pull_request.draft == false` to skip CI on draft PRs (saves minutes; chip for slice 4).
- **M-5.** Add a `name:` to every step in ci.yml (currently only the cache step in screenshots.yml has names) for cleaner CI log UI.
- **M-6.** Test plan §H.5 (assert `--cov-report=term` explicitly) — add as B-26 per the test plan's own recommendation; one-line addition.
- **M-7.** Use `setup-uv`'s built-in `python-version:` input (W-3) — eliminates the redundant setup-python step.
- **M-8.** Add a CI status badge to README at slice 3 end (currently deferred to slice 4); it's a one-line README edit, no approval gating concern.

---

## Section 5 — MISSING DECISIONs (not yet in §2 D5–D15)

| # | Decision | Why needed | Recommendation |
|---|---|---|---|
| MD-1 | **`extend-exclude` for `scripts/`** | Resolves B-4; brief §3 marks scripts/ read-only this slice | Add `"scripts"` to `extend-exclude`. Make it a new D16. |
| MD-2 | **Ruff format policy on existing code** | Resolves B-7; preflight run determines whether ci.yml can include `ruff format --check` at all | New D17. Three options: (a) preflight clean → keep `--check`; (b) preflight dirty → run `ruff format .` once with owner approval to edit src/ (slice-3 exception); (c) drop `ruff format --check` from CI, keep only `ruff check`. |
| MD-3 | **`setup-uv` version pin** | Resolves B-3 + B-6 | Bump to `@v8` (current). Add explicit `with: { version: ">=0.7" }` to pin uv version. Update D8 cache-key composition language to match. |
| MD-4 | **`paths-ignore` scope for ci.yml** | Should `notebooks/**`, `.claude/**`, `docs/img-ci/**`, `data/synthetic/**` also be in `paths-ignore` since they're irrelevant to test outcomes? | Add `"notebooks/**"`, `".claude/**"`. **Do NOT add** `docs/img-ci/**` (CI never commits there; non-issue) or `data/**` (gitignored). |
| MD-5 | **`screenshots.yml` trigger on push to dev/main post-merge** | Currently runs on PR only. After merge, the merged-state artifacts don't exist. Slice 4 portfolio launch may want post-merge artifacts. | **Defer** to slice 4 (chip); D14 covers slice-3 scope. |
| MD-6 | **Test-marker for the 84 new tests** | Test plan §G.5 says ~0.4s suite-time — negligible. But should `@pytest.mark.ci_config` be added so the 84 tests can be skipped on slow runs? | **No** — 0.4s doesn't justify a marker; the tests are pure-Python no-I/O. Closes the "should we mark" question. |
| MD-7 | **`actions/setup-python` retention vs drop** | Resolves W-3 | Drop; let `setup-uv` install Python. Closes E-08. |
| MD-8 | **`cancel-in-progress` per-workflow vs uniform** | Resolves W-10 | Keep uniform per D9 ratified; surface as observation for slice-4 review. |

---

## Section 6 — Things the Plan got right

- **TDD ordering (E1 RED → E3 GREEN → E7 lint run).** The plan correctly orders tests-first, file-creation-second; the executor cannot bypass the RED gate. This is exactly what `.claude/rules/testing.md` mandates.
- **Approval-gated-file discipline.** `pyproject.toml` is correctly flagged in §3 row 6 and §4.E5 explicitly halts the executor if D5/D6/D15 are unresolved. The brief + plan are aligned with `.claude/rules/agent-conduct.md`.
- **D14 (paths-filter on slice-3 PR).** Correctly identifies that `screenshots.yml` won't trigger on the slice-3 PR itself (no `src/ui/**` paths touched) — this is by design, not a bug. Pre-emptively closes a likely Step-11 owner confusion.
- **D13 (no `.gitattributes` needed).** Confirmed live: `git ls-files --eol scripts/build-portfolio-data.sh` returns `i/lf`. ubuntu-latest checks out LF. The Plan's reasoning holds.
- **Guardrails coverage (B-20..C-30, E-01..E-03).** Defense-in-depth on `GOOGLE_API_KEY` / `ANTHROPIC_API_KEY` / `secrets.` absence is strong. Multiple overlapping tests at workflow-level, cross-workflow-level, and raw-text-search level. A future "let me add a quick LLM eval to CI" attempt would trip ≥3 tests immediately. Excellent posture.
- **Out-of-scope chip discipline.** Brief §6 and Plan §1's "Not committed to slice 3" list correctly defer public-flip, branch-protection, coverage threshold, codecov, matrix expansion, pre-commit hook. All are real items, all are correctly named, none leak into Execute.

---

## Section 7 — Suggested order of fix (Plan Revision 1)

1. **B-1** (PyYAML `on:` → quote in workflow YAML) — one-line YAML edit; unblocks ~10 tests.
2. **B-2** (python-version float trap — explicit callout) — one-line plan-doc note; cheap insurance.
3. **B-3 + B-6 + MD-3** (setup-uv@v3 → @v8, pin uv version) — single coordinated change; unblocks `--all-groups` and modernizes posture.
4. **B-4 + MD-1** (add `"scripts"` to extend-exclude) — one-line pyproject edit; resolves the read-only-scripts deadlock.
5. **B-7 + MD-2** (ruff format preflight + policy decision) — **requires Decision Gate ratification**; cannot be unilaterally closed by the executor. Owner-blocking.
6. **B-5** (cache key non-glob anchor) — one-line workflow YAML edit + test plan C-16 extension.
7. **W-3 + MD-7** (drop setup-python) — cleanup, follows B-3.
8. **W-1** (restore-keys fallback) — soft, one-line YAML addition.
9. **W-5** (cov path consistency) — one-line CI YAML edit; align with pyproject addopts.
10. **W-6** (deepcopy in `_load_yaml`) — one-line test-conftest tweak.
11. **W-8** (`"tests/**/*.py"` instead of `"tests/**"`) — one-line pyproject edit; pin glob explicitly.
12. **W-9** (drop `packaging.version`, use regex) — 5-LOC test-D-02 tweak.
13. W-2, W-4, W-7, W-10, W-11, W-12, MD-4..MD-8 + Minors — bundle into Plan Revision 1 as cleanup; non-blocking.

**Plan Revision 1 estimated effort:** ~15 min (parent). All BLOCKERs except B-7 close mechanically; B-7 needs a 5-min owner conversation at Decision Gate.

---

## Counts

- **BLOCKERs:** 7
- **WARNINGs:** 12
- **MINORs:** 8
- **MISSING DECISIONs:** 8

**Verdict: GO-WITH-CHANGES — Plan Revision 1 required.**

---

**END OF RED-TEAM**
