# Plan Revision 1 — Phase 4 Slice 3 (delta, post red-team)

**Date:** 2026-06-21
**Parent doc:** [2026-06-21-phase4-slice3-plan.md](2026-06-21-phase4-slice3-plan.md) (v1)
**Red-team:** [2026-06-21-phase4-slice3-redteam.md](2026-06-21-phase4-slice3-redteam.md) — 7 BLOCKERs / 12 WARNs / 8 MINORs / 8 MISSING-DECISIONs / verdict GO-WITH-CHANGES

This document is a **delta**. Everything in Plan v1 stands except as overridden below.

---

## 1. BLOCKERs closed mechanically (no owner sign-off needed)

| ID | Plan v1 location | Fix in Rev1 | Test plan ripple |
|---|---|---|---|
| **B-1** PyYAML `on:` → `True` | §4.E3 line 164, §4.E4 line 216 | **Quote `"on":`** in both workflow YAML skeletons. Live-verified: `yaml.safe_load('"on":\n  pull_request:')` returns `{"on": ...}` (string key). GitHub Actions accepts quoted `"on":`. | Tests B-03 / B-04 / B-05 / B-23 / C-03 / C-29 keep `data["on"]` access — unchanged. |
| **B-2** `python-version` float trap | §4.E3 + §4.E4 skeletons | **Explicit callout** above both skeletons: `python-version: "3.11"` MUST stay quoted; never bare `3.11`. Already correct in the skeletons; this is insurance against executor expansion. | Test E-09 tightened to additionally assert `not isinstance(v, (int, float))`. |
| **B-3** setup-uv@v3 stale | §4.E3 + §4.E4 + §8 non-decisions | **Bump to `astral-sh/setup-uv@v8`** (current major v8.2.0, 2026-06-03). Update tests B-18 / C-10 to assert `r"@v[6-9]\d*$"` regex (digit ≥ 6). | Test plan B-18 + C-10 regex update. |
| **B-4** `scripts/` not in `extend-exclude` | §4.E5 line 287 | **Add `"scripts"` to `extend-exclude`** → `["data", "docs", "notebooks", ".claude", "scripts"]`. Ratifies new **D16** (slice-3 lint scope respects the read-only `scripts/` guardrail). | Add new test `test_pyproject_ruff_extend_exclude_covers_scripts` — verifies `"scripts"` in the list. |
| **B-5** cache-key glob collapse | §4.E4 line 245 | **Add non-glob anchor files** to `hashFiles(...)`: `hashFiles('src/flying_probe_copilot/generator/cli.py', 'src/flying_probe_copilot/generator/**', 'src/flying_probe_copilot/parser/cli.py', 'src/flying_probe_copilot/parser/**', 'scripts/build-portfolio-data.sh', 'uv.lock')`. Anchor files are guaranteed to exist; zero-glob-match leaves hash non-empty. | Test C-16 extended to additionally assert presence of `cli.py` substring. |
| **B-6** `--all-groups` flag on stale uv | §4.E3 + §4.E4 | Closed transitively by B-3 (uv@v8 → recent uv ≥0.7 supports `--all-groups`). **Additionally pin uv version**: `with: { version: ">=0.7" }` on the setup-uv step. Belt-and-suspenders. | Test B-19 / C-13 extended to optionally assert version pin (soft). |

These six BLOCKERs are closed by Plan Rev1 alone. **The executor proceeds with them in hand.**

---

## 2. BLOCKER **B-7 + MD-2** — `ruff format --check` + `ruff check` enforcement policy on existing code

**Preflight (parent, not in Plan v1):**

```
$ uvx --from "ruff>=0.6" ruff format --check --line-length 100 --target-version py311 src tests
58 files would be reformatted, 41 files already formatted

$ uvx --from "ruff>=0.6" ruff check --select E,F,W,I --line-length 100 --target-version py311 --statistics src tests
100 I001  [*] unsorted-imports
 95 E501  [ ] line-too-long
 67 F401  [*] unused-import
 24 F811  [*] redefined-while-unused
  8 E401  [*] multiple-imports-on-one-line
  4 F841  [ ] unused-variable
  2 E712  [ ] true-false-comparison
  1 E741  [ ] ambiguous-variable-name
Found 301 errors.
[*] 199 fixable with the `--fix` option (6 hidden fixes can be enabled with the `--unsafe-fixes` option).

# Without isort (the noisy rule):
$ uvx --from "ruff>=0.6" ruff check --select E,F,W --line-length 100 --target-version py311 --statistics src tests
... same minus 100 I001 → 201 errors, 99 auto-fixable
```

**This is a real owner decision.** Plan v1's assumption that "ruff would be clean or surface a small N of `# noqa`-suppressible violations" is false. The codebase predates any formatter and needs a deliberate stance.

### Decision D17 — Lint/format enforcement options

| Option | What slice 3 ships | Existing-code edits | Pros | Cons |
|---|---|---|---|---|
| **A — Cleanup pass (Recommended)** | (1) Apply `ruff check --fix` (auto-fixes 199 of 301 lint errors). (2) Fix the remaining 102 non-auto-fixable manually (mostly E501 line-too-long requires per-line `# noqa: E501` or refactor — owner picks). (3) Apply `ruff format .` (reformats 58 files). (4) Re-run pytest — must stay ≥566 passing. (5) Commit the cleanup as a single commit before the CI YAML files commit. (6) Slice-3 PR is then: cleanup commit + workflows commit. | YES — ~60 src/ + tests/ files edited (mechanical). Owner ratifies as a **one-time slice-3 exception** to the no-`src/**` guardrail. | Ship a codebase that passes `ruff check` + `ruff format --check` cleanly. Future PRs get a real lint catch. Phase 4 polish narrative ("hireable") is honest. | Large diff (~60 files, mostly mechanical). PR review is heavier. |
| **B — Defer all enforcement** | `.github/workflows/ci.yml` runs `pytest` only — NO ruff step in CI. `pyproject.toml` still adds the ruff config (so local `uv run ruff check .` works for developer awareness) but CI doesn't gate on it. New D17b: "ruff is developer-side only this slice; CI enforcement deferred to a follow-up slice." | NO edits to src/ + tests/. | Cleanest scope; honors read-only `src/**` guardrail; smallest diff. | Slice 4 portfolio launch ships with no CI lint signal. Disconnect between "we added ruff" and "CI doesn't actually run it" — looks like checkbox-engineering. |
| **C — Lint only, no format** | CI runs `ruff check . --output-format=github` only (no `ruff format --check`). `[tool.ruff]` config commits but the rule set is tightened to AVOID firing on existing code: `select = ["E9", "F63", "F7", "F82"]` (syntax-error class only — undefined names, broken assertions, bad imports). Add `[tool.ruff.format]` block for developer-side autoformat but don't gate CI on it. | NO edits to src/ + tests/. | Honors read-only guardrail. CI fails on truly-broken code (undefined names, syntax errors). | Very weak signal — only catches code-is-broken errors that pytest already catches at import time. Mostly checkbox engineering. |
| **D — Split slice** | Slice 3 ships ONLY the workflow YAMLs + tests (`ci.yml` runs only `pytest`, no lint job at all; no `pyproject.toml` edit). Spin a new slice 3.5 brief for the one-time `ruff format .` + `ruff check --fix` cleanup. Then slice 3.6 ships ruff config + CI lint step. | NO edits to src/ + tests/ this slice. | Cleanest separation; each PR has narrow scope. | Adds 2 sub-slices to Phase 4 timeline. Coordination burden. |

**Parent recommendation: Option A.**

Reasoning:
1. Phase 4 is "polish & portfolio". A codebase with 301 lint errors and 58 unformatted files is not portfolio-grade. Slice 4 (public flip) lands a public repo; the first reviewer instinct is `ruff check .` — a red signal there torches the recruiter narrative.
2. The 199 auto-fix + 58 format = ~257 mechanical changes. The 102 non-auto-fix are mostly E501 (line-too-long) — owner can choose per-line `# noqa: E501  # long literal string` or refactor on a case-by-case basis. Realistic effort: ~20-30 min for the manual review.
3. The test suite (566 passing, 97% coverage) is the safety net. Auto-format + auto-fix should not break behavior; if it does, the suite catches it.
4. The slice-3 read-only `src/**` guardrail was a fence against silent scope creep — owner-ratified one-time exception is the right way to cross it.

**Sub-question (if Option A is chosen) — D17.1 — what to do with the 102 non-auto-fixable errors?**

| Sub-option | Detail |
|---|---|
| **A.1.a (Recommended)** | Apply auto-fix + format; for each remaining E501 / F841 / E712 / E741, owner decides per file at Decision Gate (likely: `# noqa: E501` for long literal strings; refactor F841 / E712 / E741 if trivial; `# noqa` if not). |
| A.1.b | Apply auto-fix + format; add per-file-ignores for the remaining categories (`tests/**.py: E501, F841, F811, E712`) to suppress without per-line `# noqa`. Less precise; "lint that doesn't catch much for tests/". |
| A.1.c | Apply auto-fix + format; manually refactor every remaining error to satisfy the rule. Highest effort; biggest behavioral risk. |

**Parent recommendation: A.1.a + A.1.b hybrid** — auto-fix + format, then add **narrow per-file-ignores** scoped to specific files where the violations are systemic (e.g., `tests/test_generator/**: E501` if the long lines are all in test fixtures), with per-line `# noqa` only as a fallback for one-offs.

### What slice 3 looks like under each D17 option

| Option | New file count | Edited file count | Approval-gated edits | Slice-3 PR diff size |
|---|---|---|---|---|
| A (Recommended) | 4 (workflows + tests) | ~62 (workflows + tests + ruff cleanup + format) | pyproject.toml + ~60 src/+tests/ files (one-time exception) | ~+1500 / -1500 lines |
| B | 4 | 1 (pyproject.toml) | pyproject.toml | ~+250 / -0 lines |
| C | 4 | 1 (pyproject.toml) | pyproject.toml | ~+260 / -0 lines |
| D | 4 (workflows + tests only, no ruff config) | 0 | None | ~+220 / -0 lines |

**If owner picks B, C, or D**, the Plan v1 §4.E5 / E6 / E7 steps simplify dramatically. The executor's TDD ordering changes; new Plan Rev2 needed.

**If owner picks A**, Plan Rev1 stands AND the executor gets a new Step E0 (preflight + cleanup) before E1, plus an owner-checkpoint after E0 to review the cleanup diff before committing.

---

## 3. WARNINGs adopted into Plan Rev1

| ID | Fix |
|---|---|
| W-1 | Add `restore-keys: \|\n  sample-duckdb-` to the cache step in screenshots.yml. Soft-match fallback for stale caches. |
| W-2 | Drop literal `ci-` / `screenshots-` prefix from `concurrency.group` template. New value: `group: ${{ github.workflow }}-${{ github.ref }}`. Update tests B-11 / C-25 / E-04 to assert presence of `github.workflow` and `github.ref`. |
| W-3 + MD-7 | **Drop `actions/setup-python@v5`** from both jobs. `setup-uv@v8` installs Python via its `python-version:` input. Drop test E-08 (it would assert a step that no longer exists). Update Plan §4.E3 + §4.E4 step ordering: checkout → setup-uv (with python-version) → uv sync → ... |
| W-5 | Change CI's pytest flag from `--cov=src` to `--cov=src/flying_probe_copilot` to match `pyproject.toml`'s existing addopts. Update test B-09. |
| W-6 | Make `_load_yaml(name)` return `copy.deepcopy(yaml.safe_load(...))` per call to prevent test cross-mutation. ~2 LOC change to the conftest fixture. |
| W-8 | Change pyproject's per-file-ignores key from `"tests/**"` to `"tests/**/*.py"` — pin the glob explicitly. |
| W-9 | Test D-02 uses regex (`re.match(r"^\d+(\.\d+)*$", version)`) instead of importing `packaging.version`. Stdlib only. |
| W-12 | Test C-19 defensively asserts `"id" in cache_step` first, with a clear error message before reading the `if:` expression. |

**WARNINGs NOT adopted** (kept as observations):
- W-4 (paths-ignore comment) — clarifying comment is fine but doesn't change behavior. Optional executor add.
- W-7 (E-08 drop) — closed by W-3 adoption.
- W-10 (cancel-in-progress on screenshots.yml) — keep D9 as-is; surface as Step-11 manual-QA observation.
- W-11 (workflow file count) — keep test E-11 as a hard pin per test plan H.8.

---

## 4. MISSING DECISIONs surfaced for Step 6

| # | Decision | Recommendation | Why ask owner |
|---|---|---|---|
| **D16** | Add `"scripts"` to `extend-exclude` | YES (per B-4 closure) | Codifies the read-only `scripts/` guardrail at the lint layer. |
| **D17** | Ruff/format enforcement policy on existing code | Option A (cleanup pass) | Decides whether slice 3 ships a hireable codebase or defers the cleanup. Owner-only call. |
| **D17.1** | (if D17 = A) How to handle 102 non-auto-fixable errors | Hybrid A.1.a + A.1.b | Owner-only call (depends on D17 = A). |
| MD-4 | `paths-ignore` scope for ci.yml | Add `"notebooks/**"`, `".claude/**"`. DO NOT add `data/**` (gitignored) or `docs/img-ci/**` (CI never commits). | Defensive — avoids unnecessary CI runs on notebook/governance edits. |
| MD-3 | `setup-uv` version pin | Already closed by B-3/B-6 (uv@v8 + version: ">=0.7"). No owner ask needed. | n/a — bundled in B-3. |
| MD-5 | `screenshots.yml` post-merge trigger | DEFER to slice 4 (chip). | Out of scope this slice. |
| MD-6 | Test marker for the 84 tests | NO marker (per H.6 — 0.4s is negligible). | Cosmetic; parent-decision. |
| MD-8 | Cancel-in-progress observation | Keep D9 (uniform cancel). | Cosmetic; parent-decision. |

---

## 5. MINORs deferred (chips at Step 10)

- M-1 (commit-SHA action pinning) — chip for slice 4 around public flip
- M-2 (`actions: read` permission) — not needed slice 3
- M-3 (cache restore/save split) — not needed slice 3
- M-4 (skip draft PRs) — chip for slice 4
- M-5 (`name:` on every step) — quality-of-life; executor adds where natural
- M-6 (assert `--cov-report=term`) — adopt in test plan B-26
- M-7 (setup-uv built-in python) — closed by W-3 adoption
- M-8 (CI status badge in README) — chip for after first green CI run

---

## 6. Updated §3 file table (delta from Plan v1)

Plan v1 §3 row 6 (`pyproject.toml`) is updated to reflect the BLOCKER closures:

```toml
[dependency-groups]
dev = [
    "playwright>=1.49",
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "ruff>=0.6",
]

[tool.ruff]
line-length = 100
target-version = "py311"
extend-exclude = ["data", "docs", "notebooks", ".claude", "scripts"]  # +scripts (B-4/D16)

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
# per-file-ignores depends on D17 outcome — see §2

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["E501", "F401"]  # W-8: explicit glob

[tool.ruff.format]
# defaults
```

**If D17 = A:** ALSO commit a `[tool.ruff.lint.per-file-ignores]` section for whatever the remaining 102 non-auto-fixable categories shake out to, scoped per directory (e.g., `"src/flying_probe_copilot/ui/views.py" = ["E501"]` if the long lines are unavoidable in Plotly call chains).

**If D17 = B / C / D:** `[tool.ruff.lint].select` value changes; section §2 D17 table specifies.

---

## 7. Updated §4 Execute steps (delta from Plan v1)

**If D17 = A (recommended):**

Insert **new Step E0 — Preflight + cleanup pass** before E1:

1. `uvx --from "ruff>=0.6" ruff check --fix --select E,F,W,I --line-length 100 --target-version py311 src tests` — applies the 199 auto-fixes.
2. `uvx --from "ruff>=0.6" ruff format --line-length 100 --target-version py311 src tests` — reformats the 58 files.
3. `uv run pytest -q` — must stay ≥566 passing. If any test fails, halt and surface the failure to parent.
4. **Owner checkpoint** — show the diff (`git diff --stat`) for owner review BEFORE the next commit. Owner says GO or HALT.
5. If GO: stage the cleanup. Single commit titled `chore(phase4-slice3): one-time ruff --fix + format cleanup pass`.
6. Then proceed to E1 (RED tests for workflow YAMLs).
7. **Owner sub-decision (D17.1):** for the 102 non-auto-fixable, owner picks per-line `# noqa` vs per-file-ignores vs refactor. Implemented in a SECOND cleanup commit after E0.

All other Execute steps (E1-E10) proceed as in Plan v1 with the Rev1 deltas baked in (quote `"on":`, drop setup-python, etc.).

**If D17 = B / C / D:** Plan v1 §4.E5 `[tool.ruff.lint].select` value changes; §4.E7 `ruff format --check .` step is REMOVED. Plan Rev2 needed.

---

## 8. Owner decision sheet for Step 6

Bring these to the owner via `AskUserQuestion` at Step 6 Decision Gate:

| # | Question | Recommended | Alternatives |
|---|---|---|---|
| D16 | Add `"scripts"` to ruff's `extend-exclude`? | YES | NO |
| D17 | Ruff/format enforcement on existing code | **A — Cleanup pass** | B (defer all), C (lint-only narrow set), D (split slice) |
| D17.1 (if A) | How to handle 102 non-auto-fixable errors | **Hybrid (per-file-ignore where systemic, `# noqa` for one-offs)** | All-per-line-noqa, all-per-file-ignores, refactor-each |
| MD-4 | Add `"notebooks/**"` + `".claude/**"` to ci.yml paths-ignore | YES | NO |
| BR | Worktree branch rename → `feature/phase4-slice3-ci-workflows` at Step 10 | YES (matches slice 1/2 pattern) | Keep `claude/sweet-jones-7291db` name |
| BUNDLE | If D17 = A, slice-3 PR bundles cleanup + CI workflows in one PR | YES (one coherent PR) | Two PRs (cleanup first, then workflows) |

Other D5-D15 stand from Plan v1 §2 unchanged.

---

## 9. Definition of Done updates

§9 of Plan v1 still applies, **with these additions if D17 = A:**

- [ ] `uvx ruff check src tests` exit 0 (or all violations suppressed per D17.1)
- [ ] `uvx ruff format --check src tests` exit 0
- [ ] Cleanup commit has its own clear title `chore(phase4-slice3): one-time ruff --fix + format cleanup pass`
- [ ] No pytest behavior regression after cleanup (566 → 566 still)
- [ ] Owner reviewed cleanup diff before commit

If D17 = B / C / D, the corresponding lines drop.

---

## 10. Handoff to Step 6

Next action: **owner Decision Gate** on D16, D17, D17.1 (if A), MD-4, BR, BUNDLE. Parent runs `AskUserQuestion` with the recommendations above as defaults. No Execute starts until owner ratifies. The 6 mechanical BLOCKER closures (B-1 through B-6) and 8 adopted WARNs are baked into Plan Rev1 and do NOT need owner confirmation — they fix things the owner would otherwise discover at first CI run.
