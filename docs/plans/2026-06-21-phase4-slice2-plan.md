# Plan — Phase 4 Slice 2: Headless Screenshot Capture + Demo GIF

**Date:** 2026-06-21
**Author:** parent (Step 3, not delegated)
**Inputs:** `2026-06-21-phase4-slice2-brief.md`, Step 2 Explore report
**Tier:** Medium (full 12-step loop)

---

## Goal Contract

**WHEN** an engineer runs `python scripts/capture_screenshots.py all --db data/db/sample.duckdb`,
**THEN** the script will (a) launch a headless Streamlit instance against `data/db/sample.duckdb` on a free random port with the Co-Pilot backend monkeypatched to a canned grounded `Answer`, (b) drive Playwright Chromium through all 6 dashboard pages clicking the sidebar nav links by visible label, (c) write `docs/img/screenshot-{overview,yield,pareto,spc,anomalies,copilot}.jpg` (each ≥ 60 KB and ≥ 1280×800), (d) assemble those six JPGs into `docs/img/demo.gif` (~12 s loop, 2 s/frame), (e) tear down the Streamlit subprocess cleanly, and (f) exit 0 — or fail with a non-zero exit and a diagnostic message naming the first missing artifact.
**SO THAT** README hero-strip and demo-gif media stays fresh through one command on any dashboard or dep change, no manual snipping, no live Gemini key needed.

**Negative-space contract** (what the slice will NOT do):
- Will not modify `src/flying_probe_copilot/**` (no production-code touch).
- Will not add a GitHub Actions workflow.
- Will not require `GOOGLE_API_KEY`.
- Will not auto-generate `data/db/sample.duckdb` if missing — aborts cleanly with a "run scripts/build-portfolio-data.sh first" message.
- Will not commit `playwright` browser binaries (only the Python package).
- Will not introduce new screenshot file names — must reuse the 6 names the README already links.

---

## What / Why / Where / When table

> Per `.claude/skills/session-workflow/SKILL.md` Step 3 requirement.
> Files outside this table are off-limits to the Step-7 executor unless explicitly logged and surfaced.

| # | What | Why | Where (file:line) | When (which Plan step creates/edits it) |
|---|------|-----|---|---|
| F1 | New CLI: `scripts/capture_screenshots.py` | Slice-2 deliverable — single entry point for screenshot + gif capture. Subcommands `screenshots`, `gif`, `all`. | `scripts/capture_screenshots.py` (NEW) | Plan steps 4–9 |
| F2 | New shim app for Streamlit: `scripts/_capture_app.py` | Monkeypatches `chat.answer_question` to a canned `Answer` then calls `app.main()`. Lets Streamlit run the real dashboard without the Co-Pilot needing a live key. Underscore-prefixed because it's an internal helper. | `scripts/_capture_app.py` (NEW) | Plan step 3 |
| F3 | New `scripts/__init__.py` | Make `scripts/` importable from tests so `from scripts import capture_screenshots` works. | `scripts/__init__.py` (NEW) | Plan step 1 |
| F4 | New test module: `tests/test_scripts/test_capture_screenshots.py` | Unit tests for pure helpers — canned-Answer builder, gif assembler, CLI arg parsing, missing-output detector. Does NOT launch Playwright (kept fast, deterministic). | `tests/test_scripts/test_capture_screenshots.py` (NEW) | Plan steps 4–8 (RED first per step) |
| F5 | New `tests/test_scripts/__init__.py` | Package marker. | `tests/test_scripts/__init__.py` (NEW) | Plan step 1 |
| F6 | New env-gated smoke: `tests/test_scripts/test_capture_real.py` | End-to-end Playwright smoke gated on `CAPTURE_RUN_PLAYWRIGHT=1`. Pattern mirrors `tests/test_rag/test_eval.py`. Always-skipped in normal `uv run pytest`. | `tests/test_scripts/test_capture_real.py` (NEW) | Plan step 10 |
| F7 | New JPGs in `docs/img/` | Replace slice-1 hand-captured JPGs with byte-fresh auto-captured ones (same 6 filenames). | `docs/img/screenshot-{overview,yield,pareto,spc,anomalies,copilot}.jpg` (REPLACE) | Plan step 11 (capture invocation) |
| F8 | New `docs/img/demo.gif` | Animated walkthrough cycling the 6 pages. | `docs/img/demo.gif` (NEW) | Plan step 11 |
| F9 | `pyproject.toml` dev-group dep add — **approval-gated** | Add `playwright>=1.49` to `[dependency-groups].dev`. Pillow is already locked (12.2.0) for gif assembly. | `pyproject.toml` `[dependency-groups].dev` block (EDIT — gated) | Step 6 Decision Gate ratifies; Plan step 0 applies |
| F10 | `uv.lock` regeneration | Auto-result of `uv sync` after pyproject edit. Committed for reproducibility. | `uv.lock` (REGENERATE) | Plan step 0 |
| F11 | `README.md` — embed gif — **approval-gated** | Add a single line above the hero strip: `![Demo walkthrough](docs/img/demo.gif)`. Owner-approved at Step 6. | `README.md` between line 14 (intro) and line 16 (hero-strip table) — exact edit point ratified at Step 6 | Plan step 12 |
| F12 | `docs/case-study.md` retrospective edit | Strike the "Slice 1.5 candidate" line now that slice 2 ships it. | `docs/case-study.md:123` (the "Capture screenshots from CI…" sentence) | Plan step 13 |
| F13 | `docs/ROADMAP.md` — gif annotation | Phase 4 deliverable line for "README polished … screenshot strip" gets " (+ demo gif 2026-06-21 — slice 2)" suffix. No new row. | `docs/ROADMAP.md:157` | Plan step 13 |
| F14 | `CLAUDE.md` Status block flip + session-log line | Slice 1 IN PR → slice 2 IN PR; append session-log entry. | `CLAUDE.md` Status block + session log | Step 10 |
| F15 | `docs/logs/SESSION_LOG.md` entry | New top entry per template. | `docs/logs/SESSION_LOG.md` line 5 (insert above current top entry) | Step 10 |
| F16 | `docs/logs/DECISION_LOG.md` entries | D1/D2/D3 from brief + whatever Decision Gate surfaces. | `docs/logs/DECISION_LOG.md` (top) | Step 10 |
| F17 | Plan artifacts | brief / plan / test-plan / decision-gate / manual-qa / triple-check / handoff | `docs/plans/2026-06-21-phase4-slice2-*.md` | Steps 1, 3, 4, 6, 11, 9, 12 |

**Files explicitly NOT in scope (executor must not touch):**
- Anything under `src/flying_probe_copilot/**`
- `.claude/**` (rules, hooks, agents, skills, settings)
- `.gitignore` / `.env.example`
- Any `migrations/` or `db/schema.py`
- Any prior `docs/plans/2026-06-2*-phase*.md`

---

## Ordered TDD steps

### Step 0 — Approval-gated dep add (BLOCKER on Decision Gate)
**Pre-condition:** Step 6 has ratified `playwright>=1.49` in dev group.
**Actions:**
1. `Edit pyproject.toml`: add `"playwright>=1.49"` to `[dependency-groups].dev` list (alphabetized).
2. Run `uv sync` to update `uv.lock`.
3. Run `uv run playwright install chromium` (one-time; not committed). Verify success.
**RED test:** `tests/test_scripts/test_capture_screenshots.py::test_playwright_importable` — `import playwright.sync_api; assert hasattr(playwright.sync_api, 'sync_playwright')`.
**GREEN:** passes after `uv sync`.
**REFACTOR:** none.

### Step 1 — Package markers
**RED test:** `test_scripts_package_importable` — `from scripts import capture_screenshots` does not raise (after file exists in later steps).
**GREEN:** Write `scripts/__init__.py` and `tests/test_scripts/__init__.py` (both empty).
**REFACTOR:** none.

### Step 2 — Pure helper: canned `Answer` builder
**RED test:** `test_canned_answer_returns_grounded_answer_with_citation` — `capture_screenshots.build_canned_answer("any q")` returns an `Answer` with `refused=False`, `len(citations) >= 1`, citation matches `r"failure-modes/[a-z-]+\.md#\d+"`, and `answer_text` is non-empty and ≥ 60 chars (so the rendered chat bubble has visual weight).
**GREEN:** Implement `build_canned_answer(question: str) -> Answer` returning a canned `Answer` over `failure-modes/tombstoning.md#0`. Mirror the `_grounded` stub in `tests/test_ui/test_chat_smoke.py:18-25` but expand `answer_text` to ~120 chars for screenshot weight.
**REFACTOR:** lift the citation string to a module constant `CANNED_CITATION_ID`.

### Step 3 — Streamlit shim app: `scripts/_capture_app.py`
**RED test:** `test_shim_app_monkeypatches_chat_module` — import `scripts._capture_app` in a subprocess (via `subprocess.run([sys.executable, "-c", "import scripts._capture_app"])`) under a sentinel env var that short-circuits `main()` (e.g., `FPC_CAPTURE_DRY_IMPORT=1`); assert the subprocess exits 0 and `flying_probe_copilot.ui.chat.answer_question.__qualname__` ends in `build_canned_answer` after import.

   The sentinel-env short-circuit is necessary because `app.main()` calls `st.set_page_config` etc., which raise outside a Streamlit runtime. The shim checks `os.environ.get("FPC_CAPTURE_DRY_IMPORT")` and returns before invoking `main()`.

**GREEN:** Write `scripts/_capture_app.py`:
```python
"""Streamlit shim: monkeypatches Co-Pilot backend then runs the real app.

Loaded by Playwright capture via `streamlit run scripts/_capture_app.py`.
"""
from __future__ import annotations

import os

from flying_probe_copilot.ui import chat as _chat
from scripts.capture_screenshots import build_canned_answer

_chat.answer_question = build_canned_answer

if not os.environ.get("FPC_CAPTURE_DRY_IMPORT"):
    from flying_probe_copilot.ui.app import main
    main()
```
**REFACTOR:** none.

### Step 4 — Pure helper: gif assembler
**RED test:** `test_assemble_gif_writes_valid_gif89a` — pass 3 small in-memory `PIL.Image.new("RGB", (100, 100), color="red")` (varied colors) to `capture_screenshots.assemble_gif(images, out_path, frame_duration_ms=200)`; assert `out_path.exists()`, first 6 bytes == `b"GIF89a"`, `Image.open(out_path).is_animated is True`, and frame count == 3.
**Additional RED:** `test_assemble_gif_empty_list_raises_value_error`.
**GREEN:** Implement `assemble_gif(frames: Sequence[PIL.Image.Image], out_path: Path, frame_duration_ms: int = 2000) -> None` using Pillow's `frames[0].save(out_path, save_all=True, append_images=list(frames[1:]), duration=frame_duration_ms, loop=0, optimize=True)`. Raise `ValueError` on empty input.
**REFACTOR:** none.

### Step 5 — Pure helper: filename map
**RED test:** `test_page_label_to_filename_covers_all_six_pages_in_correct_order` — `PAGE_CAPTURE_SPECS` is a tuple of 6 `(nav_label, filename_stem)` pairs in this exact order: `[("Overview","overview"), ("Yield","yield"), ("Failure Pareto","pareto"), ("SPC","spc"), ("Anomalies","anomalies"), ("Co-Pilot","copilot")]`. The map is the source of truth; everything that needs "which 6 pages" reads from it.
**GREEN:** Define the tuple at module top.
**REFACTOR:** none.

### Step 6 — Pure helper: free-port picker
**RED test:** `test_pick_free_port_returns_int_in_valid_range_and_actually_free` — `port = pick_free_port(); assert 1024 <= port <= 65535`; bind a `socket.socket(AF_INET, SOCK_STREAM)` to `("127.0.0.1", port)` and assert it doesn't raise.
**GREEN:** Implement `pick_free_port() -> int` using the standard `socket.socket(AF_INET, SOCK_STREAM); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()` pattern.
**REFACTOR:** none.

### Step 7 — Pure helper: missing-output detector
**RED test:** `test_check_outputs_complete_raises_on_missing_files` — given `tmp_path` with 5 of the 6 expected JPGs created (zero-byte), `check_outputs_complete(tmp_path, [...specs...])` raises `FileNotFoundError` whose message names the missing file. **Additional RED:** when all 6 exist and are non-empty, `check_outputs_complete` returns `None` silently. **Additional RED:** when a file exists but is 0 bytes, raises `ValueError` "empty screenshot".
**GREEN:** Implement `check_outputs_complete(out_dir: Path, specs: Sequence[PageSpec]) -> None`.
**REFACTOR:** none.

### Step 8 — CLI arg parsing
**RED test:** `test_cli_parse_args_all_subcommand_with_defaults` — `parse_args(["all"])` returns a namespace with `command="all"`, `db=Path("data/db/sample.duckdb")`, `out=Path("docs/img")`, `port=None` (None means "pick free").
**Additional RED:** `test_cli_parse_args_overrides` — `parse_args(["screenshots", "--db", "x.duckdb", "--out", "y/", "--port", "9000"])` reflects the overrides.
**Additional RED:** `test_cli_parse_args_unknown_command_exits_nonzero` — invalid subcommand → `SystemExit` with non-zero code.
**Additional RED:** `test_cli_parse_args_missing_db_raises` — when `args.db` doesn't exist on disk and `command != "gif"`, `main()` exits non-zero with diagnostic naming `--db`.
**GREEN:** Implement `argparse`-based `parse_args(argv)` + `main(argv=None)` skeleton that validates DB existence pre-launch.
**REFACTOR:** none.

### Step 9 — Capture-orchestration outline (no Playwright yet)
**Skipped — orchestration is the env-gated end-to-end (Step 10).** Pure helpers above carry the unit-test load.

### Step 10 — End-to-end env-gated test
**RED test:** `tests/test_scripts/test_capture_real.py::test_capture_real_screenshots_run_end_to_end` — gated on `CAPTURE_RUN_PLAYWRIGHT=1`. Build a temp DB via the existing `ui_db_path` fixture (lifted to a `tests/conftest.py`-level fixture or duplicated locally), invoke `main(["all", "--db", str(db_path), "--out", str(tmp_out)])`, assert exit 0, all 6 JPGs exist and are ≥ 50 KB, `demo.gif` exists and starts with `b"GIF89a"`.
**GREEN:** Implement the Playwright orchestration in `capture_screenshots.py::capture_screenshots(...)`:
1. `pick_free_port()` → `port`.
2. `subprocess.Popen(["uv", "run", "streamlit", "run", "scripts/_capture_app.py", "--server.port", str(port), "--server.headless", "true", "--browser.gatherUsageStats", "false", "--logger.level", "error"], env={**os.environ, "FPC_DB_PATH": str(args.db)})`.
3. Poll `http://localhost:{port}/_stcore/health` until 200 OK or 30 s timeout.
4. `from playwright.sync_api import sync_playwright`; `p.chromium.launch(headless=True)`, viewport 1440×900.
5. `page.goto(f"http://localhost:{port}")`, `page.wait_for_load_state("networkidle")`.
6. For each `(nav_label, stem)` in `PAGE_CAPTURE_SPECS`:
   - If not the first page, `page.get_by_role("link", name=nav_label).first.click()`.
   - `page.wait_for_load_state("networkidle")`, `page.wait_for_timeout(500)` (Plotly settle).
   - For the Co-Pilot page, `page.get_by_test_id("stChatInput").locator("textarea").fill("what causes tombstoning?")`, press Enter, `page.wait_for_load_state("networkidle")`, settle 800 ms.
   - `page.screenshot(path=str(out_dir / f"screenshot-{stem}.jpg"), full_page=False, quality=90, type="jpeg")`.
7. Tear down: `browser.close()`, `proc.terminate()`, wait 5 s, `proc.kill()` if needed.
8. `check_outputs_complete(out_dir, PAGE_CAPTURE_SPECS)`.
9. If `command in ("gif", "all")`: load each JPG via Pillow, `assemble_gif(...)` → `out_dir / "demo.gif"`.
**REFACTOR:** factor the Streamlit-launch + health-poll into `_launch_streamlit_subprocess(port, db_path) → Popen` (testable in isolation by mocking `Popen`).

### Step 11 — Capture invocation against the live sample DB
**Pre-condition:** `data/db/sample.duckdb` exists. If not, run `bash scripts/build-portfolio-data.sh` first (out-of-band, parent verifies).
**Action:** `python scripts/capture_screenshots.py all --db data/db/sample.duckdb`. Verify all 7 outputs (6 JPGs + 1 GIF). Spot-check each JPG opens cleanly and shows the expected page (parent-eyeball during Step 9 Triple Check).
**REFACTOR:** none.

### Step 12 — README embed (approval-gated, ratified at Step 6)
**Action:** `Edit README.md` to insert `![Demo walkthrough](docs/img/demo.gif)` at the location Decision Gate ratified (default: directly above the hero-strip table, after the intro paragraph).
**Verification:** local render via Markdown preview; final check is post-PR on GitHub.

### Step 13 — Case-study + roadmap edits
**Action:**
1. `Edit docs/case-study.md`: strike (or footnote-resolve) the "Slice 1.5 candidate" sentence at `:123`.
2. `Edit docs/ROADMAP.md`: append ` (+ demo gif 2026-06-21 — slice 2)` to line 157.
**Verification:** `grep -n "Slice 1.5 candidate" docs/case-study.md` returns nothing.

---

## Decision matrix (open decisions for Step 6 Decision Gate)

| # | Decision | Options | Parent recommendation | Rationale |
|---|---|---|---|---|
| D4 | Capture-script entry point | (a) `scripts/capture_screenshots.py` standalone; (b) `src/flying_probe_copilot/screenshots/cli.py` + `[project.scripts] screenshots=...` | **(a)** | Matches existing `scripts/build-portfolio-data.sh` convention; capture infra isn't a runtime feature of the package. Keeps `[project.scripts]` clean (only user-facing CLIs `generator`/`parser`). |
| D5 | Gif assembly lib | (a) Pillow (already locked); (b) imageio[ffmpeg] (new dep) | **(a)** | Zero new approval-gated dep. Pillow's gif writer is mature, supports `duration`, `loop`, `optimize`. Output size will be larger than imageio's; acceptable for a 12-s demo. |
| D6 | Sample-DB auto-build | (a) Abort with friendly message if missing; (b) auto-run `scripts/build-portfolio-data.sh`; (c) build a tiny in-memory DB inside the capture script | **(a)** | (b) couples capture to a 1-min batch generation that the owner may not want; (c) loses the realistic 6-month data visible in the README hero strip. Friendly error is cheap UX. |
| D7 | Co-Pilot page question shown in screenshot | (a) `"what causes tombstoning?"` (recently fixed by BUG-014); (b) `"why am I seeing a yield drop on board v2?"`; (c) something else owner picks | **(a)** | Story-rich choice: directly visualizes the BUG-014 fix; uses the canned `failure-modes/tombstoning.md#0` citation; matches the case-study's tombstoning engineering-story. |
| D8 | Where to insert gif in README | (a) above hero strip, after intro; (b) below hero strip; (c) as a new section between Quickstart and Architecture | **(a)** | Highest-impact placement for recruiter scan; gif is more attention-grabbing than static strip. Hero strip becomes the "stills" complement directly below. |
| D9 | Should slice 2 commit the 6 freshly-captured JPGs even though they're byte-different from slice-1's hand-captured ones? | (a) Yes — replace; (b) keep slice-1 JPGs, only commit the new gif | **(a)** | Whole point of the slice is "auto-recapture replaces manual"; keeping the hand-captured baseline would undermine the next change's diff. Slice-1 JPGs become "artifact of one moment in time"; slice-2 onward they are reproducible. |
| D10 | Frame duration in gif | (a) 2000 ms/frame (12 s total); (b) 1500 ms/frame (9 s total); (c) 3000 ms/frame (18 s total) | **(a)** | Slow enough to read each page's KPI numbers, fast enough that a recruiter's attention holds. CLI flag makes it overridable. |
| D11 | Whether to keep `tests/test_scripts/test_capture_real.py` in the suite (skipped by default) or omit it entirely until CI lands | (a) Keep gated; (b) omit | **(a)** | Cheap to keep skipped; gives a self-documenting recipe for "how do I prove the script works"; matches the slice-1 `RAG_RUN_LLM_EVAL` pattern. |
| D12 | Branch name | (a) `feature/phase4-slice2-screenshots`; (b) `feature/phase4-slice2-demo-capture` | **(a)** | More specific; "screenshots" is the user-facing artifact name; "capture" is the verb. |

---

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Playwright Chromium install fails on Windows behind corp proxy | M | H | `uv run playwright install chromium` is a one-time owner action; document in README + brief; if it fails, escalate before merging. |
| Streamlit's auto-generated URL slug for "Failure Pareto" or "Co-Pilot" isn't what we expect | M | M | Navigation by sidebar click on the visible label (`get_by_role("link", name=...)`) avoids URL-slug guesswork entirely. Plan step 10 specifies the click-based approach. |
| Plotly chart hasn't finished animating when screenshot fires → empty / mid-animation chart | M | M | `wait_for_load_state("networkidle")` + 500 ms settle + (for Co-Pilot) 800 ms post-submit. If still flaky, raise to 1500 ms — cheap, deterministic. |
| Streamlit subprocess doesn't terminate cleanly on Windows (zombie process holds port) | L | M | `proc.terminate()` then `proc.wait(timeout=5)` then `proc.kill()`. Use `try/finally` around the Playwright block so teardown always runs. |
| Pillow gif output > 2 MB → bloats repo / slow GitHub render | L | M | `optimize=True` + 1280×800 viewport keeps frames lean. If gif > 1.5 MB, Plan step 11 will resize frames to 1024×640 in the Pillow load step before assembling. |
| Co-Pilot page renders a chat bubble that overflows / wraps mid-screenshot | L | L | Canned answer text is ~120 chars (deliberately bounded). |
| `chat.answer_question` becomes a class method or is renamed → shim's `_chat.answer_question = ...` silently no-ops | L | H | Step 3 RED test confirms the monkeypatch survives a subprocess import. Step 10 end-to-end test inspects the Co-Pilot screenshot for the canned answer text via Playwright `page.get_by_text(...)`. |
| Slice silently regresses the existing 524-test suite via the new `scripts/__init__.py` triggering test-collection in a place pytest didn't reach before | L | M | `pyproject.toml`'s `[tool.pytest.ini_options] testpaths = ["tests"]` already scopes collection to `tests/`. Verify with `uv run pytest --collect-only -q | head -30` in Step 8. |
| README gif link breaks on `dev` PR preview (relative-vs-absolute path) | L | L | GitHub renders relative `docs/img/demo.gif` paths from the repo-root README correctly. Same pattern slice 1 already used for JPGs. |

---

## Verification checklist (parent at Step 9)

- [ ] `uv run pytest -q` → 528+ passed (524 baseline + ≥4 new) / 3 skipped (eval) / 1 xfailed / 97%+ coverage
- [ ] `python scripts/capture_screenshots.py all --db data/db/sample.duckdb` exits 0
- [ ] All 6 `docs/img/screenshot-*.jpg` exist and are ≥ 50 KB
- [ ] `docs/img/demo.gif` exists, starts with `GIF89a`, < 2 MB
- [ ] `grep -niE "IPC-A-610|J-STD-001|Keysight|i3070|HP3070"` over diff returns no verbatim quotes (titles/names are OK)
- [ ] `grep -rn "GOOGLE_API_KEY\|sk-\|AIza" docs/img/` returns nothing (no key leaked into image metadata)
- [ ] No edits under `src/flying_probe_copilot/**`
- [ ] No edits under `.claude/**`
- [ ] Plan-vs-Executed file list matches the F1-F17 table
- [ ] CLAUDE.md status block + session-log line both updated
- [ ] SESSION_LOG.md + DECISION_LOG.md entries both added
- [ ] Branch is `feature/phase4-slice2-screenshots` (renamed from worktree default)

---

## Loop-step skip notice

This is a **Medium-tier full 12-step loop**. No steps skipped. Step 4 (test-case plan) + Step 5 (verify plan) are non-skippable because this is the first new entry point in `scripts/` and the first Playwright integration in the repo.
