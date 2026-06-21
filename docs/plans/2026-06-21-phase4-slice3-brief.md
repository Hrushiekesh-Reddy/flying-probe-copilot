# Session Brief — Phase 4 Slice 3: GitHub Actions (lint + tests + screenshot recapture)

**Date:** 2026-06-21
**Phase:** 4 — Polish & Portfolio
**Slice:** 3 (of 4) — CI hardening
**Tier:** Medium (full 12-step session-workflow loop)
**Branch:** worktree `claude/sweet-jones-7291db` → rename to `feature/phase4-slice3-ci-workflows` at Step 10
**Owner sign-off scope:** approval-gated `pyproject.toml` edit (add `ruff` dev-group dep + `[tool.ruff]` config); NEW `.github/workflows/` directory is **not** in the approval-gated list (fresh CI infra, no prior contract to preserve).

---

## 1. Why this slice exists

Phase 4 slice 1 (README + case-study) and slice 2 (headless screenshot capture + demo gif) shipped clean, but every test/lint/screenshot run today happens on the owner's local machine. The repo is one-deep on quality: a regression that breaks the dashboard between PRs is invisible until somebody runs `streamlit run` and looks. The Phase 4 ROADMAP still has two unchecked deliverables that close that gap:

> - [ ] GitHub Actions workflow: lint + tests on PR
> - [ ] Repo flipped to public after guardrails checklist passes

This slice closes the **first** of those two — automated lint + tests + screenshot recapture on every PR. The **second** (public flip) is explicitly held to slice 4 (see §6 Decision D3 ratified at brief time) so the repo flip lands the same day as the blog/LinkedIn/portfolio launch, when traffic actually arrives.

Practically: after this slice, every PR runs `ruff` lint + the full 566-test suite on Linux + Python 3.11; every PR that touches `src/flying_probe_copilot/ui/**`, `src/flying_probe_copilot/analytics/**`, `scripts/capture_screenshots.py`, or `scripts/_capture_app.py` additionally recaptures the 6 dashboard JPGs + demo gif and uploads them as CI artifacts the reviewer can download and eyeball before merge.

---

## 2. Decisions already ratified (pre-Decision-Gate, owner-confirmed at brief time via AskUserQuestion)

| # | Decision | Choice | Why |
|---|---|---|---|
| D1 | CI sample-DB strategy | **Cache build artifact** (actions/cache) | Build hash-keyed on generator + parser source. Fast (~5 s on hit), zero repo bloat, zero binary drift. Build runs only when generator/parser code changes; ~3-min cost amortized. |
| D2 | Recaptured-screenshot disposition | **CI artifacts only** | Workflow uploads JPGs/gif as artifacts; reviewer downloads + eyeballs + commits manually if desired. No bot-as-author commits, no PAT scope, simpler audit trail. |
| D3 | Public-flip timing | **Hold until slice 4** | Repo flip + blog + LinkedIn + resume bullet coordinate as one launch event, not separate flips. Slice 3 is CI hygiene; slice 4 is portfolio launch. |
| D4 | Lint stack | **ruff only** | Codebase is untyped; mypy would surface dozens-to-hundreds of issues that need annotating-or-ignoring (a separate project, not slice 3). Ruff covers lint + format check in one fast tool. Mypy revisit window: post-Phase 4 if owner ever annotates `src/`. |

These are firm. Decision Gate (Step 6) will surface only **new** decisions that emerge during Plan + Test-Case Plan + Red-Team.

---

## 3. Deliverables (Definition of Done)

### CI infra (NEW — not in approval-gated list)
- **`.github/workflows/ci.yml`** — runs on every PR to `dev` or `main`:
  - **Job 1: lint** — `ruff check .` + `ruff format --check .` on ubuntu-latest, Python 3.11. Fails the job on any violation. Annotates inline on the PR diff (`--output-format=github`).
  - **Job 2: tests** — `uv sync --frozen --all-groups` → `uv run pytest -q --cov=src --cov-report=term`. Same Python 3.11 / ubuntu-latest. Caches the uv venv directory keyed on `uv.lock` hash. Posts coverage to job summary (no third-party uploader; PR comment is overkill for slice 3).
  - Both jobs run in **parallel** (no needs).
- **`.github/workflows/screenshots.yml`** — runs on PRs to `dev` or `main` whose changed paths match `src/flying_probe_copilot/ui/**`, `src/flying_probe_copilot/analytics/**`, `docs/knowledge-base/**`, `scripts/capture_screenshots.py`, `scripts/_capture_app.py`. Uses `paths:` filter, not a separate job-level skip.
  - **Job: capture** — ubuntu-latest, Python 3.11. Steps:
    1. Checkout
    2. Install uv
    3. `uv sync --frozen --all-groups`
    4. `uv run playwright install --with-deps chromium`
    5. **Restore-or-build sample DB** via actions/cache, key = hash of `src/flying_probe_copilot/generator/**` + `src/flying_probe_copilot/parser/**` + `scripts/build-portfolio-data.sh`. Cache miss → run a Linux-compatible variant of `scripts/build-portfolio-data.sh` inline (or call it via `bash`).
    6. `uv run python scripts/capture_screenshots.py all --db data/db/sample.duckdb --out docs/img-ci/`
    7. `actions/upload-artifact@v4` → name `recaptured-dashboard-screenshots`, retention 14 days
  - Job-level timeout 15 min (allows for cold cache + sample-DB build + capture).

### Lint config (approval-gated)
- **`pyproject.toml`** — declared edits at Plan time, owner-ratified before Execute:
  - Add `ruff>=0.6` to `[dependency-groups].dev` (alphabetized)
  - Add `[tool.ruff]` block — minimal-defaults config (line-length 100, target-version py311, default rule selection `["E", "F", "W", "I", "B", "UP"]`, exclusions for `data/`, `docs/`, `notebooks/`, `.claude/`)
  - Add `[tool.ruff.format]` block — defaults (no aggressive reformat)

### Test fixes (if ruff surfaces violations)
- Slice 3 lands ruff *configured to pass* the existing codebase or with **explicit `# noqa` markers** on intentional patterns. Plan + red-team will decide between (a) tighter rule set + per-file ignores, or (b) loose rule set + zero suppressions. **Tightening rules is out-of-slice-3** — surface as chips.

### Docs
- **`docs/ROADMAP.md`** — tick "GitHub Actions workflow: lint + tests on PR" (Phase 4 deliverable).
- **`CLAUDE.md` status block** — flip from "slice 2 IN PR" to "slice 3 IN PR".
- **`docs/logs/SESSION_LOG.md`** — new entry at top.
- **`docs/logs/DECISION_LOG.md`** — D1-D4 above + anything new from Step 6.
- **`docs/plans/2026-06-21-phase4-slice3-{brief,plan,decision-gate,test-plan,redteam,exec-report,manual-qa}.md`** — artifacts.
- **`docs/logs/AGENT_HANDOFF_LOG.md`** — Step 12 entry pointing at slice 4.

### What we are NOT touching (slice guardrail)
- `src/flying_probe_copilot/**` — read-only this slice
- `.claude/**` — read-only this slice
- `.gitignore` / `.env.example` / `migrations/` / `db/schema.py` — read-only this slice
- `scripts/capture_screenshots.py` / `scripts/_capture_app.py` — read-only this slice (CI calls them; no edits)
- Any KB doc in `docs/knowledge-base/**`
- Tests under `tests/test_scripts/**`, `tests/test_ui/**`, `tests/test_rag/**`, etc. — read-only

---

## 4. Success criteria (verification gates)

| Gate | Criterion | How measured |
|---|---|---|
| G1 — Suite still green locally | **566 passing / 5 skipped / 1 xfailed / 97%** baseline held — no test changes this slice | `uv run pytest -q` |
| G2 — Ruff passes locally on existing code | `uv run ruff check .` exit 0; `uv run ruff format --check .` exit 0 | local invocation |
| G3 — Workflow YAML parses | `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` exit 0 (and same for screenshots.yml) | tested via tests/ folder |
| G4 — CI workflow logic test-covered | At least the path-filter rules + matrix shape + step ordering are validated by a unit test (PyYAML-loaded → assertions on dict shape) | `uv run pytest tests/test_ci/` |
| G5 — Live CI run goes green on the slice-3 PR | First push to `feature/phase4-slice3-ci-workflows` triggers CI; both ci.yml jobs go green; screenshots.yml triggers on the PR's own diff (since the PR adds workflow files, paths-filter behavior is the question — see §6 below) | manual GitHub UI watch (owner Step 11) |
| G6 — Guardrails preserved | No real-customer data; no Keysight/IPC verbatim text in any new file; no `.env` value committed; `GOOGLE_API_KEY` not referenced in CI (screenshots use the canned-answer shim) | `grep -niE "IPC-A-610\|J-STD-001\|Keysight\|i3070\|HP3070\|GOOGLE_API_KEY"` on new files |
| G7 — Triple-check clean | Step 9 parent independent read finds no Plan-vs-Executed drift | Step 9 |
| G8 — No `.claude/**` or `src/**` edits | `git diff --name-only origin/dev...HEAD` shows zero hits under those paths | grep |

**G5 caveat:** the first CI run on the slice-3 branch is the gate that validates the workflows end-to-end. If it fails, fix-forward on the same branch — do not stash + redesign locally.

---

## 5. Tier rationale — Medium

| Factor | Slice 3 | Tier |
|---|---|---|
| New module | 1 (`.github/workflows/`) | Medium |
| New approval-gated dep | 1 (`ruff`) | Medium |
| Approval-gated file edits | 1 (`pyproject.toml`) | Medium |
| Code surface | ~150-250 LOC YAML + ~50-100 LOC tests | Medium |
| Subagent fan-out | Standard 4 (Explore, Test-Case Plan, Verify Plan, Execute) | Medium |
| Decision Gate | Yes — D1-D4 ratified + likely 2-4 more from red-team | Medium |
| Test plan complexity | Low-medium (YAML shape tests + lint-config sanity) | Small ↑ |
| Touches production code | No (zero edits to `src/flying_probe_copilot/**`) | Small ↓ |
| First-time integration risk | High — first CI run on this repo | Medium ↑ |

Net: **Medium**, full 12-step loop. Step 4 test-case plan + Step 5 red-team are non-skippable because CI is a new entry point and a first-time integration.

---

## 6. Out-of-scope (chips at Step 10)

| Item | Why deferred | Future chip |
|---|---|---|
| Repo flip to public | D3 ratified — slice 4 launch event | Yes (slice 4) |
| Blog post / LinkedIn post / resume bullet | Slice 4 portfolio promotion | Yes (slice 4) |
| `docs/DEMO.md` walkthrough script | Slice 4 portfolio promotion | Yes (slice 4) |
| Mypy / strict typing | D4 — out of scope this slice | Maybe (post-Phase-4) |
| Branch-protection rules requiring CI pass | GitHub settings change, not code | Maybe (slice 4, around public flip) |
| Coverage thresholds enforcement (e.g., `--cov-fail-under=95`) | First-CI integration risk; let coverage drift be reviewed manually before adding a hard floor | Maybe |
| Codecov / Coveralls integration | Adds a third-party dep; job-summary table covers slice-3 needs | No |
| Windows + macOS runners in matrix | Repo is Linux-friendly; the owner's local dev is Windows but CI green on Linux is sufficient gating | No |
| `pre-commit` hook for ruff | A separate developer-ergonomics task; CI lint failure is enough for slice 3 | Maybe |
| Recapture auto-commit (D2 alternative) | D2 explicitly chose artifacts-only | No |
| Inline-comment annotation of coverage diff | Overkill for slice 3 | No |
| `--no-verify` git hook bypass | Forbidden by `.claude/rules/agent-conduct.md` | Never |

---

## 7. Hard guardrails reminder (re-stated from `CLAUDE.md`)

1. **No real customer log data ever.** CI runs against a freshly-built synthetic `sample.duckdb` (gitignored; rebuilt from generator/parser code via `actions/cache` keyed on those sources).
2. **No Keysight/IPC verbatim.** CI workflows are pure infrastructure code; nothing references copyrighted docs.
3. **No API keys in CI.** `GOOGLE_API_KEY` is not set in the workflow. Screenshot capture uses the existing `scripts/_capture_app.py` monkeypatch shim — the same path tests use today.
4. **No edits to `src/flying_probe_copilot/**`** this slice. If ruff flags a real bug, log to BUG_LOG, `spawn_task` it, do not fix in-slice.
5. **No production deploys, no cloud, no real frontend.** CI runs unit tests + lint + screenshot capture, then uploads artifacts. No deployment step exists.

---

## 8. Non-decisions (parent-pre-decided with notice)

| Pre-decision | Why parent-decided |
|---|---|
| Runner OS = **ubuntu-latest** | Standard, free-tier-friendly, matches Streamlit's own CI; Windows-only bugs caught locally are NOT slice-3 scope. |
| Python = **3.11** (single version, no matrix) | `pyproject.toml` declares 3.11+; matrix expansion buys CI time + flakiness without buying coverage signal slice 3 needs. |
| Use **uv** in CI (not pip) | Matches local-dev contract; `uv sync --frozen` is faster + lock-deterministic. |
| Use **actions/cache@v4** for venv keyed on `uv.lock` | Standard. Re-cache on lock change. |
| Use **actions/upload-artifact@v4** for screenshots | Replaces v3 (deprecated 2024-12). |
| Workflow trigger on PRs to **`dev` and `main`** (not push) | Matches repo branching policy — work happens on feature branches, PRs target `dev`; main only sees PR from `dev`. Push triggers would CI-run every local commit on `dev` and `main`, wasting minutes. |
| YAML uses **2-space indent** + comments | GitHub Actions convention. |
| Workflow files **alphabetized + named after their function** (`ci.yml`, `screenshots.yml`) | Discoverable in the Actions tab UI. |
| No reusable workflows / no composite actions slice 3 | Single repo, no fan-out; abstraction = overhead. |
| **Always-recapture** Co-Pilot screenshot via the existing shim — no special-case "skip the Co-Pilot page in CI" mode | The shim is the whole point of slice-2 design (no live API call). |
| Coverage report = **terminal output → job summary** | Hard threshold is out-of-slice; visibility is in-scope. |
| `paths-ignore` for `docs/**` on `ci.yml` so doc-only PRs skip tests | Pragmatic — docs-only changes don't break tests. |

---

## 9. Expected duration

| Step | Estimate |
|---|---|
| 1 — Brief (this doc) | done |
| 2 — Explore | 6 min |
| 3 — Plan + What/Why/Where/When | 12 min |
| 4 — Test-case plan | 8 min |
| 5 — Red-team | 12 min |
| 6 — Decision Gate | 5 min (owner sync) |
| 7 — Execute (TDD) | 30-40 min (2 workflow files + ruff config + tests + local ruff run + iterate any violations) |
| 8 — Verify Execution | 8 min |
| 9 — Triple Check | 8 min |
| 10 — Docs + commit | 12 min |
| 11 — Manual QA (owner pushes branch + watches first CI run) | 10-15 min (cold-cache first run takes ~5-8 min on GH Actions) |
| 12 — Handoff | 3 min |
| **Total** | **~115-140 min** parent time, **~5-8 min** first-CI wall-clock |

---

## 10. Open questions for Step 6 (Decision Gate) — anticipated

These are NOT pre-ratified. They will surface during Plan + Red-Team and need owner sign-off at the Decision Gate:

1. **Sample-DB cache key shape** — hash `src/generator/**` + `src/parser/**` + `scripts/build-portfolio-data.sh`, or also include `pyproject.toml`? More keys = more cache misses but tighter invariant.
2. **Linux-port of `build-portfolio-data.sh`** — script is already bash, so likely runs on ubuntu-latest as-is. If it has Windows-isms (drive letters, `bash.exe` paths), Plan rewrites or wraps it. Red-team to verify.
3. **Ruff rule set** — start with `["E", "F", "W", "I"]` (only the four most universal categories) and `[tool.ruff.lint.per-file-ignores]` for `tests/**`, or be more ambitious with `["B", "UP", "SIM"]` added? The bigger the set, the more violations on existing code.
4. **What to do if ruff surfaces real bugs on existing code** — fix in-slice (scope creep), suppress with `# noqa: <code>  # tracked-in-BUG_LOG-XYZ` (preserves discipline), or relax the rule (loses the catch)? Default: **suppress with BUG_LOG entry**, fix in a follow-up chip.
5. **Workflow `permissions:` block** — minimal-permissions hardening (`contents: read` only). Should slice 3 also set `pull-requests: write` for the (future) PR-comment posting? Probably no — chip for slice 4 if/when comments are added.
6. **`concurrency:` block** — cancel-in-progress on the same PR to avoid duplicate runs on rapid-fire pushes. Default: yes; saves CI minutes; no downside on this repo's PR cadence.

---

## 11. Next-session pointer

After slice 3 merges to `dev` → `main`:
- **Slice 4 (final Phase 4 slice)** — portfolio promotion:
  - Final guardrails audit (run the §8 `docs/GUARDRAILS.md` checklist top-to-bottom; `git log --all -- data/real/` etc.)
  - Repo flip to public (GitHub Settings → Visibility)
  - `docs/DEMO.md` walkthrough script
  - Blog post draft
  - LinkedIn post draft
  - Resume bullet drafted
  - Branch-protection rules (require CI pass on PRs to `main`)

Slice 4 likely Small or Medium depending on whether blog/LinkedIn copy is owner-authored or AI-drafted.
