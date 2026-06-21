# Decision Gate — Phase 4 Slice 3

**Date:** 2026-06-21
**Step:** 6 of 12
**Parent:** Claude Code parent (Opus 4.7)
**Owner:** Hrushiekesh Reddy Kanjula

This is the gate that authorizes Execute (Step 7). No edits to src/, .github/, pyproject.toml, or any approval-gated file may begin before this document is committed.

---

## Coverage check

Every brief §3 deliverable + every BLOCKER / WARN / MISSING-DECISION surfaced by red-team is enumerated below with its disposition.

| Source | ID | Disposition |
|---|---|---|
| Brief §3 | ci.yml workflow | Plan §4.E3 |
| Brief §3 | screenshots.yml workflow | Plan §4.E4 |
| Brief §3 | pyproject.toml ruff add | Plan §4.E5 + D16/D17/D17.1 |
| Brief §3 | tests/test_ci/ (≥10 tests) | Plan §4.E1 (84-test plan) |
| Brief §3 | ROADMAP tick | Plan §4.E9 |
| Brief §3 | SESSION_LOG entry | Plan §10 |
| Brief §3 | DECISION_LOG entries | Plan §10 |
| Brief §3 | CLAUDE.md status flip | Plan §10 |
| Brief §3 | Plan artifacts | Plan + Rev1 + Test-plan + Red-team + this doc |
| Brief §3 | AGENT_HANDOFF_LOG entry | Plan §12 |
| Brief D1 | CI sample-DB cache | Ratified pre-Gate (AskUserQuestion #1) |
| Brief D2 | Screenshot artifacts only | Ratified pre-Gate (AskUserQuestion #2) |
| Brief D3 | Hold public flip | Ratified pre-Gate (AskUserQuestion #3) |
| Brief D4 | ruff only (no mypy) | Ratified pre-Gate (AskUserQuestion #4) |
| Plan D5 | Rule set ["E","F","W","I"] | Ratified at this Gate via D17 = A |
| Plan D6 | per-file-ignores `tests/**/*.py: E501, F401` | Ratified at this Gate via D17.1 hybrid |
| Plan D7 | If real violations: suppress + chip | **Superseded by D17/D17.1** — cleanup pass replaces it |
| Plan D8 | Sample-DB cache key composition | Ratified at this Gate (anchor-file refinement per B-5) |
| Plan D9 | Concurrency cancel-in-progress | Ratified at this Gate (W-10 surfaced as Step-11 observation) |
| Plan D10 | permissions: contents: read | Ratified at this Gate |
| Plan D11 | No coverage threshold this slice | Ratified at this Gate |
| Plan D12 | paths-ignore docs/** on ci.yml | Ratified at this Gate + extended per MD-4 |
| Plan D13 | No .gitattributes needed | Ratified — verified live (git ls-files --eol = i/lf) |
| Plan D14 | screenshot job won't run on slice-3 PR | Ratified at this Gate (correct, not a bug) |
| Plan D15 | ruff CLI flags (--output-format=github, no --fix in CI) | Ratified at this Gate |
| **Plan Rev1 D16** | **Add "scripts" to ruff extend-exclude** | **Ratified — explicit owner select** |
| **Plan Rev1 D17** | **Lint/format policy: A (cleanup pass)** | **Ratified — explicit owner select** |
| **Plan Rev1 D17.1** | **Non-auto-fixable handling: Hybrid (per-file-ignore where systemic + # noqa one-offs)** | **Ratified — explicit owner select** |
| Plan Rev1 MD-4 | Add "notebooks/**" + ".claude/**" to ci.yml paths-ignore | **Inferred ratified** ("Recommended" pattern) |
| Plan Rev1 BR | Rename worktree → feature/phase4-slice3-ci-workflows at Step 10 | **Inferred ratified** |
| Plan Rev1 BUNDLE | Cleanup + workflows in one PR | **Inferred ratified** |
| Red-team B-1 | Quote `"on":` in YAML | Mechanical — closed in Plan Rev1 |
| Red-team B-2 | python-version float trap | Mechanical — closed in Plan Rev1 |
| Red-team B-3 | setup-uv@v3 → @v8 | Mechanical — closed in Plan Rev1 |
| Red-team B-4 | scripts/ in extend-exclude | Closed by D16 ratification |
| Red-team B-5 | cache-key non-glob anchor | Mechanical — closed in Plan Rev1 |
| Red-team B-6 | uv version pin | Mechanical — closed in Plan Rev1 |
| Red-team B-7 | ruff format policy | Closed by D17 ratification |
| Red-team W-1..W-12 | Adopted per Plan Rev1 §3 | (W-3 + W-4 + W-7 + W-10 + W-11 noted) |
| Red-team M-1..M-8 | Deferred to chips per Plan Rev1 §5 | n/a slice 3 |
| Red-team MD-1..MD-8 | Resolved per Plan Rev1 §4 (some via D16-D17, some deferred to chips) | n/a slice 3 |

All deliverables, decisions, and risks accounted for.

---

## Inferred ratifications — explicit flag for owner pushback

Three "Recommended on all" smaller-call decisions were bundled in the multi-select question that returned a single explicit pick (D16 only). Per slice-1 and slice-2 precedent (owner consistently takes all "Recommended"), parent is interpreting:
- **MD-4**: Add `"notebooks/**"` + `".claude/**"` to ci.yml `paths-ignore` → **YES** (assumed)
- **BR**: Rename worktree branch at Step 10 → **YES** (assumed; matches slice 1+2 pattern)
- **BUNDLE**: Cleanup commit + workflows commit in same PR → **YES** (assumed; one coherent review)

**Owner: flag any of these if "Recommended" was not your intent.** Otherwise parent proceeds.

---

## Execute plan (with cleanup pass — D17 = A)

### E0 — One-time ruff cleanup pass (NEW; owner-ratified slice-3 exception to read-only src/)

1. `uvx --from "ruff>=0.6" ruff check --fix --select E,F,W,I --line-length 100 --target-version py311 src tests` — auto-applies 199 fixes.
2. `uvx --from "ruff>=0.6" ruff format --line-length 100 --target-version py311 src tests` — reformats 58 files.
3. `uv run pytest -q` — must report ≥566 passing / 5 skipped / 1 xfailed / ≥97% coverage. Coverage drop is a halt condition.
4. **Owner checkpoint**: parent shows `git diff --stat` + a few representative file diffs. Owner says GO or HALT.
5. If GO: stage all cleanup changes, single commit:
   ```
   chore(phase4-slice3): one-time ruff --fix + format cleanup pass

   Apply ruff check --fix (199 auto-fixes: I001, F401, F811, F841, E712, E741)
   and ruff format (58 files) against src/ + tests/ as a one-time exception
   to the slice-3 read-only src/ guardrail. D17/D17.1 ratified at Decision
   Gate 2026-06-21. Suite stays 566 passing / 5 skipped / 1 xfailed / 97%.
   ```
6. **D17.1 second commit (if needed):** parent walks the remaining ~102 non-auto-fixable errors with owner. Per-file-ignore where systemic (e.g., tests/test_generator/**: E501 if line-too-long is a fixture pattern), # noqa: E501 for one-offs. Commit titled:
   ```
   chore(phase4-slice3): suppress non-auto-fixable lint errors per D17.1
   ```

### E1 — RED — tests/test_ci/ shape tests (Plan §4.E1 + Test-plan 84 tests)
### E2 — RED — pyproject.toml ruff sentinel (Plan §4.E2)
### E3 — GREEN — Create .github/workflows/ci.yml (Plan Rev1 §1 mechanical + §3 W-1, W-2, W-5)
### E4 — GREEN — Create .github/workflows/screenshots.yml (Plan Rev1 §1 mechanical + §3 W-1, W-2)
### E5 — GREEN — Add ruff to pyproject.toml (D5/D6/D16 — approval-gated, now ratified)
### E6 — uv sync (regenerates uv.lock)
### E7 — RUN: uvx ruff check + ruff format --check; verify exit 0 (post-cleanup, must be clean)
### E8 — RUN: uv run pytest -q; verify ≥576 passing (566 baseline + 10 new ci-test minimum; test plan estimates +84)
### E9 — Tick ROADMAP Phase 4 deliverable for "GitHub Actions workflow: lint + tests on PR"
### E10 — Hand back to parent for Step 8 verification

---

## Authorizes

- Edits to `.github/workflows/` (new dir)
- Edits to `pyproject.toml` (ratified at this gate per D17/D17.1/D16)
- New `tests/test_ci/` directory and files
- **One-time src/** and tests/ edits via `ruff --fix` and `ruff format`** (ratified at this gate per D17 — slice-3 exception)
- Edits to docs/ROADMAP.md, CLAUDE.md, docs/logs/* at Step 10
- Edits to docs/plans/* artifacts

## Does NOT authorize

- Any edit to `src/flying_probe_copilot/**` beyond what `ruff --fix` and `ruff format` apply mechanically. Manual semantic edits to src/ are out of scope.
- Any edit to `.claude/**`
- Any edit to `.gitignore`, `.env.example`, `migrations/`, `src/flying_probe_copilot/db/schema.py`
- Any edit to `scripts/capture_screenshots.py`, `scripts/_capture_app.py`, `scripts/build-portfolio-data.sh`
- `git push` (owner-initiated only)
- New dependencies beyond `ruff>=0.6`

## Halt conditions for the executor

- Suite drops below 566 passing after the cleanup pass at E0 step 3
- `uv run pytest -q` regression at any later step
- Ruff surfaces a violation in `src/` post-cleanup that isn't auto-fixable AND isn't covered by D17.1 (this would mean the cleanup itself introduced something new — a real regression)
- Any edit needed outside the ratified scope above
- `yaml.safe_load` of either workflow file raises an error
- Cache key collapses to a constant in dry-run (B-5 regression)

In any of those cases, executor stops and reports back to parent — does not retry, does not work around.

---

## Gate cleared. Execute begins.

**Next action:** parent invokes the `exec` sub-agent with the full Execute scope above. Cleanup pass at E0 will surface owner checkpoint after step 4. All other steps proceed mechanically with their RED→GREEN ordering preserved.
