# Session Brief — Phase 4 Slice 2: Headless Screenshot Capture + Demo GIF

**Date:** 2026-06-21
**Phase:** 4 — Polish & Portfolio
**Slice:** 2 (of N) — auto-capture infrastructure
**Tier:** Medium (full 12-step session-workflow loop)
**Branch:** feature/phase4-slice2-screenshots (rename worktree branch `claude/condescending-ishizaka-3c597d` at Step 10)
**Owner sign-off scope:** approval-gated `pyproject.toml` dep add (Playwright + gif assembler) + approval-gated `README.md` edit (embed gif).

---

## 1. Why this slice exists

Phase 4 slice 1 shipped a portfolio-grade README anchored on a 2×3 hero strip of six dashboard screenshots (`docs/img/screenshot-*.jpg`) plus a `docs/case-study.md` writeup. The screenshots were captured **by hand** — owner launched `streamlit run` against the live Gemini key and snipped six pages in the browser. Slice 1's case-study §retrospective explicitly flags this as the next improvement:

> "Capture screenshots from CI, not by hand. … A CI-driven headless Playwright run would have been a one-time setup that paid off every time the dashboard's visual design changes. Slice 1.5 candidate."

Slice 2 closes that loop. Every future dashboard change (Phase 4 polish, post-portfolio additions, dependency-driven visual drift) gets one-command screenshot recapture instead of a six-page manual snip. The slice also lands the **`docs/img/demo.gif`** animated walkthrough — the second piece of portfolio media a recruiter expects to see embedded in a README (after the static hero strip).

GitHub Actions wiring is **explicitly out-of-scope** for this slice (separate Phase 4 deliverable: `lint + tests on PR`). The capture script must be CI-ready (headless, deterministic, idempotent, exit-coded), but the slice ships the script + assets, not the workflow that runs them.

---

## 2. Decisions already ratified (pre-Decision-Gate, owner-confirmed at brief time)

| # | Decision | Choice | Why |
|---|---|---|---|
| D1 | Scope boundary | **Script + demo gif (no GH Actions this slice)** | Matches CLAUDE.md slice-2 phrasing; bounds blast radius; GH Actions is a distinct Phase-4 deliverable that needs lint + test policy thinking first. |
| D2 | Co-Pilot page capture method | **Stub `answer_question` at capture time** | Capture script monkeypatches the chat backend to return a canned grounded answer + citation. No live API call, runs in any environment incl. future CI. Same pattern as `tests/test_ui/test_chat_smoke.py` (`_smoke_chat` wrapper). Authenticity preserved (canned answer cites a real `failure-modes/*.md` chunk). |
| D3 | Headless tool | **Playwright (`playwright-python`)** | Full-browser fidelity (sidebar, page nav, Plotly hover state). Used by Streamlit's own e2e suite. Named in slice-1 case-study. Approval-gated dev-group dep add to `pyproject.toml`. |

These are firm. Decision Gate (Step 6) will surface only **new** decisions that emerge during Plan + Test-Case Plan + Red-Team.

---

## 3. Deliverables (Definition of Done)

### Code
- **`scripts/capture_screenshots.py`** — Python CLI; subcommands `screenshots` + `gif`. Takes `--db` path + `--port` (default 8501) + `--out` (default `docs/img/`). Launches `streamlit run ui/app.py` headless, drives Playwright through all 6 pages, captures each to `screenshot-{overview,yield,pareto,spc,anomalies,copilot}.jpg`, then assembles the gif from a recorded navigation trace. Monkeypatches `ui.chat.answer_question` before launching Streamlit. Exit code 0 on full success, non-zero if any page fails to render or any expected output file is missing.
- **`scripts/__init__.py`** — make the dir importable for tests.
- **6 regenerated screenshots in `docs/img/screenshot-*.jpg`** — same filenames, dimensions ≥ slice-1 hand-captured ones, README links unchanged.
- **`docs/img/demo.gif`** — animated walkthrough cycling the 6 pages (e.g., 2 s per page, ~12 s total loop). README embeds it above the hero strip.

### Tests
- **`tests/test_scripts/test_capture_screenshots.py`** — unit tests for the pure-helper layer of the capture script (the parts that don't actually launch Playwright). Behavior-level: stub-builder produces a canned `Answer`; gif-assembler emits a valid GIF89a from N input JPGs; CLI arg parsing rejects invalid paths; missing-output-file detector raises. The real Playwright launch is **not** unit-tested in CI (lives behind an env gate similar to `RAG_RUN_MODEL_TESTS`, e.g. `CAPTURE_RUN_PLAYWRIGHT=1`) — final decision in Step 6.
- **`tests/test_scripts/__init__.py`** — package marker.
- **`tests/test_scripts/test_capture_real.py`** (env-gated) — end-to-end smoke that the actual capture produces 6 non-empty JPGs + a valid GIF; skipped by default.

### Docs
- **`README.md`** — embed `docs/img/demo.gif` above (or just after) the existing hero strip. Approval-gated edit.
- **`docs/ROADMAP.md`** — Phase 4 deliverable line for "README polished with architecture diagram + dashboard screenshot strip" already ticked; add a note "(gif added 2026-06-21 — slice 2)". No new deliverable row.
- **`docs/case-study.md`** — strike (or footnote-resolve) the "Slice 1.5 candidate" line in §retrospective now that slice 2 closes it.
- **`CLAUDE.md` status block** — flip from "slice 1 IN PR" to "slice 2 IN PR". Session-log line appended.
- **`docs/logs/SESSION_LOG.md`** — new entry at top.
- **`docs/logs/DECISION_LOG.md`** — D1/D2/D3 above + whatever surfaces at Step 6.
- **`docs/plans/2026-06-21-phase4-slice2-{brief,plan,decision-gate,test-plan,manual-qa,triple-check}.md`** — artifacts.

### Dependencies (approval-gated)
- **`pyproject.toml`** — add to `[dependency-groups].dev`:
  - `playwright>=1.49` (current GA; supports Python 3.11+ + Chromium headless)
  - `pillow>=10.0` OR `imageio[ffmpeg]>=2.34` for gif assembly — Plan + Step 6 picks one
- **`uv.lock`** — auto-updated by `uv sync`
- **Browser binaries** — `playwright install chromium` is a one-time runtime install, NOT committed to repo. README Quickstart gets a one-line note.

---

## 4. Success criteria (verification gates)

| Gate | Criterion | How measured |
|---|---|---|
| G1 — Suite green | **524 passing / 3 skipped / 1 xfailed / 97%** baseline held, plus ≥4 new unit tests for the capture script | `uv run pytest -q` |
| G2 — Capture runs end-to-end | `python scripts/capture_screenshots.py screenshots --db data/db/sample.duckdb` produces 6 non-empty JPGs in `docs/img/` with dimensions ≥ slice-1 baselines | manual run + file-stat check (or env-gated test) |
| G3 — Gif assembles | `python scripts/capture_screenshots.py gif --out docs/img/demo.gif` produces a valid GIF89a | `file docs/img/demo.gif` |
| G4 — Co-Pilot page renders without live key | Capture works with `GOOGLE_API_KEY` unset | `unset GOOGLE_API_KEY && python scripts/capture_screenshots.py screenshots` |
| G5 — README renders | Embedded gif + hero strip both display on GitHub.com after PR push | manual GitHub render check (post-PR) |
| G6 — Idempotency | Running the capture script twice in a row yields byte-different but visually-equivalent JPGs (timestamps in dashboard differ ⇒ bytes differ); no orphan tmp files; exit 0 both runs | manual |
| G7 — Guardrails preserved | No real-customer data; no Keysight/IPC verbatim text in any new file; no `.env` value committed; `playwright install` is *invoked* not *vendored* | `grep -niE "IPC-A-610|J-STD-001|Keysight|i3070|HP3070"` audit on new files |
| G8 — Triple-check clean | Step 9 parent independent read finds no Plan-vs-Executed drift | Step 9 |

---

## 5. Tier rationale — Medium

| Factor | Slice 2 | Tier |
|---|---|---|
| New module | 1 (scripts/) | Medium |
| New approval-gated dep | 1-2 (playwright + gif lib) | Medium |
| Approval-gated file edits | 2 (pyproject.toml, README.md) | Medium |
| Code surface | ~150-250 LOC capture script + ~80-150 LOC tests | Medium |
| Subagent fan-out | Standard 4 (Explore, Test-Case Plan, Verify Plan, Execute) | Medium |
| Decision Gate | Yes — has ratified D1-D3 + likely 2-4 more emerging | Medium |
| Test plan complexity | Low (pure helpers + 1 env-gated smoke) | Small ↑ |
| Binary asset assembly | gif (new mode) | Medium |
| Touches production code | No (zero edits to `src/flying_probe_copilot/**`) | Small ↓ |

Net: **Medium**, full 12-step loop. Step 4 test-case plan + Step 5 red-team are non-skippable because the capture script is the first new entry point in `scripts/` and the first time we depend on Playwright.

---

## 6. Out-of-scope (chips at Step 10)

| Item | Why deferred | Future chip |
|---|---|---|
| GitHub Actions workflow `screenshots.yml` | Phase 4 lists `lint + tests on PR` as a separate deliverable; bundling them couples policy decisions. | Yes |
| `lint + tests on PR` GH Actions | Same; needs ruff/black/uv-cache strategy decision. | Yes |
| Demo gif narration / audio | Out of `gif` format. Could ship `docs/img/demo.mp4` in a future slice if portfolio site demands. | Maybe |
| Re-capture trigger on `ui/**` PR diff | Requires GH Actions. | Yes |
| Replacing slice-1 screenshots with **higher-resolution** auto-captured ones | Resolution match is sufficient; bumping is a separate UX call. | No |
| Repo flip to public | Phase 4 final-slice deliverable; needs full guardrails audit pass. | Maybe (Phase 4 slice 4) |
| Blog post / LinkedIn post / resume bullet | Phase 4 final-slice deliverables. | Maybe (Phase 4 slice 4) |

---

## 7. Hard guardrails reminder (re-stated from `CLAUDE.md`)

1. **No real customer log data ever.** Capture runs against `data/db/sample.duckdb` (synthetic).
2. **No Keysight/IPC verbatim.** Capture screenshots show the dashboard's own UI — no manual text overlays from copyrighted docs.
3. **No API keys committed.** Capture script must work with `GOOGLE_API_KEY` unset (D2 stub).
4. **No edits to `src/flying_probe_copilot/**`** this slice. If a screenshot reveals a visual bug, log to BUG_LOG, spawn_task it, do not fix in-slice.
5. **No production deploys, no cloud, no real frontend.** Streamlit + local capture only.

---

## 8. Non-decisions (parent-pre-decided with notice)

| Pre-decision | Why parent-decided |
|---|---|
| Output format JPG (not PNG) | Matches existing slice-1 README links; switching formats is a churn-only edit. |
| File names `screenshot-{overview,yield,pareto,spc,anomalies,copilot}.jpg` | Same — preserves README links unchanged. |
| Animation rate ~2 s per page, ~12 s total | Standard portfolio-gif cadence; final number can be a script CLI flag. |
| Single Chromium headless backend | Firefox/WebKit add no fidelity for a Streamlit dashboard. |
| Capture happens against `data/db/sample.duckdb` (gitignored) | Same DB the owner used for slice-1; reproducible via `parser` CLI. |
| Capture script's `--port` defaults to a high random port to avoid clashing with an already-running `streamlit run` on :8501 | Operational ergonomics. |
| Capture script auto-launches and auto-terminates the Streamlit subprocess (no manual "start a server first" step) | One-command UX. |
| Capture script writes a `.run-id` next to assets noting `git rev-parse HEAD` + `uv sync --frozen` lock-hash for provenance | Cheap, useful for "why does this gif look different" debugging. |

---

## 9. Expected duration

| Step | Estimate |
|---|---|
| 1 — Brief (this doc) | done |
| 2 — Explore | 5 min |
| 3 — Plan + What/Why/Where/When | 10 min |
| 4 — Test-case plan | 8 min |
| 5 — Red-team | 10 min |
| 6 — Decision Gate | 5 min (owner sync) |
| 7 — Execute (TDD) | 30-45 min (script + helpers + gif assembler + tests + actual capture) |
| 8 — Verify Execution | 8 min |
| 9 — Triple Check | 8 min |
| 10 — Docs + commit | 12 min |
| 11 — Manual QA (owner) | 5 min |
| 12 — Handoff | 3 min |
| **Total** | **~110-130 min** parent time |

---

## 10. Next-session pointer

After slice 2 merges to `dev`:
- **Slice 3** (queued): test/coverage hardening + remaining Phase 4 chips. BUG-010 and BUG-012 closed in PR #31 already; chips remaining: GH Actions workflow, lint pipeline, repo-public flip.
- **Slice 4** (queued): portfolio promotion — blog post + LinkedIn + resume bullet + final guardrails audit + flip-to-public.
