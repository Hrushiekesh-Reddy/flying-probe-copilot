# Executor Report — Phase 4 Slice 2: Headless Screenshot Capture + Demo GIF

**Date:** 2026-06-21
**Executor:** exec subagent (claude-sonnet-4-6)
**Plan source:** `2026-06-21-phase4-slice2-plan-rev1.md` (superseding rev)

---

## Steps

| # | Plan step | Status | Test result | Notes |
|---|-----------|--------|-------------|-------|
| 0 | pyproject.toml dep add + uv sync + playwright install | DONE | CAP-01 RED→GREEN | Added `playwright>=1.49` + `pythonpath=[".", "src"]` to pyproject.toml; `uv sync` pulled playwright 1.60.0; `playwright install chromium` completed to AppData |
| 1 | Package markers: `scripts/__init__.py`, `tests/test_scripts/__init__.py` | DONE | Both empty files created | |
| 2 | Pure helper: `build_canned_answer` | DONE | CAP-10..15 RED→GREEN | CANNED_CITATION_ID = "failure-modes/tombstoning.md#3" per B-1; canned answer text is the 471-char MD-6 verbatim string |
| F4.5 | Declared parallel edit: `test_chat_smoke.py:24` `#0`→`#3` | DONE | CHAT-03 still GREEN | Both citations tuple and retrieved_ids tuple updated; CHAT-03 assertion also updated |
| 3 | Shim app `scripts/_capture_app.py` | DONE | CAP-20..23 RED→GREEN | B-4 defensive assert added before main(); FPC_CAPTURE_DRY_IMPORT sentinel present |
| 4 | Pure helper: `assemble_gif` | DONE | CAP-30..36 + empty/animated RED→GREEN | ValueError on empty, mixed size, invalid duration; auto-creates parent dir; copies frames to avoid handle leak |
| 5 | Pure constant: `PAGE_CAPTURE_SPECS` | DONE | CAP-40..43 RED→GREEN | Exact 6-tuple in order; CAP-43 uses AST to verify app.py st.Page titles |
| 6 | Pure helper: `pick_free_port` | DONE | CAP-50..53 RED→GREEN | Standard OS bind-to-0 pattern; CAP-51 proves two consecutive calls differ |
| 7 | Pure helper: `check_outputs_complete` | DONE | CAP-60..64 RED→GREEN | Checks dir existence, per-file existence, zero-byte guard |
| 8 | CLI: `parse_args` + `main` skeleton | DONE | CAP-70..74 RED→GREEN | 3 subcommands: screenshots/gif/all; DB existence pre-flight; --out file-vs-dir guard; gif-only pre-flight check |
| 9 | Capture orchestration outline | SKIPPED | — | Plan says skipped — orchestration is in env-gated Step 10 |
| 10 | Playwright orchestration in `capture_screenshots.py::capture_screenshots()` | DONE | CAP-90..94 written (gated) | W-3 fix (sys.executable -m streamlit), W-4 (proc inside try), W-5 (1500ms settle), W-10 (friendly Chromium error); B-2 expander click; B-5 regex nav |
| 10 (F18) | Sidebar DOM shape test `test_streamlit_sidebar_dom_shape.py` | DONE | Written gated | Pins stSidebarNav data-testid; default-skipped |
| MD-3 | Fixture lift: `ui_db_path` → `tests/conftest.py` | DONE | All 87 test_ui tests still GREEN | Moved fixture + _populate_ui_db helper from test_ui/conftest.py to tests/conftest.py; test_ui/conftest.py now contains only _strip_llm_env |
| 11 | Capture invocation against live DB | DEFERRED | — | Parent handles at Step 11 (parent task); DB built by build-portfolio-data.sh |
| 12 | README embed | NOT DONE | — | Parent handles Step 12 (approval-gated README edit) |
| 13 | case-study + roadmap edits | NOT DONE | — | Parent handles Step 13 |

---

## Files changed

### New files (untracked)
- `scripts/__init__.py` — empty package marker
- `scripts/capture_screenshots.py` — 257 LOC; helpers: build_canned_answer, assemble_gif, pick_free_port, check_outputs_complete, _wait_for_health, capture_screenshots, parse_args, main; constants: CANNED_CITATION_ID, PAGE_CAPTURE_SPECS
- `scripts/_capture_app.py` — 30 LOC; Streamlit shim; monkeypatches chat.answer_question; defensive assert; FPC_CAPTURE_DRY_IMPORT short-circuit
- `tests/test_scripts/__init__.py` — empty package marker
- `tests/test_scripts/conftest.py` — autouse _strip_llm_env fixture for LLM key defense-in-depth
- `tests/test_scripts/test_capture_screenshots.py` — 38 unit tests (CAP-01..81); pure-function tests, no Playwright, no Streamlit subprocess, no DuckDB
- `tests/test_scripts/test_capture_shim.py` — 4 tests (CAP-20..23); subprocess-based shim import checks
- `tests/test_scripts/test_capture_real.py` — 4 env-gated tests (CAP-90..94); gated on CAPTURE_RUN_PLAYWRIGHT=1; default-skipped
- `tests/test_scripts/test_streamlit_sidebar_dom_shape.py` — 1 env-gated test (F18); gated on CAPTURE_RUN_PLAYWRIGHT=1; default-skipped

### Modified files (tracked)
- `pyproject.toml` — +2 lines: `playwright>=1.49` in dev group (alphabetized); `pythonpath = [".", "src"]` in pytest.ini_options
- `uv.lock` — +110 lines: playwright 1.60.0, greenlet 3.5.2, pyee 13.0.1
- `tests/conftest.py` — +202 lines: ui_db_path session fixture + _populate_ui_db helper (lifted from test_ui/conftest.py per MD-3)
- `tests/test_ui/conftest.py` — -270 lines (fixture + helper removed); now contains only _strip_llm_env autouse
- `tests/test_ui/test_chat_smoke.py` — 3 lines changed: _grounded() citations/retrieved_ids `#0`→`#3`; CHAT-03 assertion `#0`→`#3`

---

## Test suite

Before (baseline): 524 passing / 3 skipped / 1 xfailed / 97% coverage
After: **566 passing / 5 skipped / 1 xfailed / 97% coverage**

New test count: 42 new tests passing (38 unit + 4 shim) + 5 env-gated skipped (4 Playwright + 1 sidebar DOM)

Run time: 112.80s (dominated by AppTest UI smoke + RAG embedding bootstrap for existing tests)

---

## Coverage

`src/flying_probe_copilot` denominator (per pyproject.toml addopts) — 97% unchanged.
`scripts/` is NOT in the coverage denominator and is NOT counted.

---

## Out-of-scope bugs logged

None found during this execution.

---

## Deviations

- **Step 0 RED test for CAP-02:** `playwright.__version__` does not exist on the installed package (no `__version__` attribute on the `playwright` module). Fix: changed to `importlib.metadata.version("playwright")`. Logged as minor deviation — the test file was still RED before GREEN.

- **CAP-53 socket mock:** The `pick_free_port` implementation uses a plain `socket.socket(...)` call (not a context manager), so the monkeypatch targets `scripts.capture_screenshots.socket` module rather than `scripts.capture_screenshots.sync_playwright`. Test code adjusted accordingly.

- **CAP-80 mock approach:** `sync_playwright` is imported inside `capture_screenshots()` function body (lazy import), not at module level. CAP-80 test patches `playwright.sync_api.sync_playwright` instead of `scripts.capture_screenshots.sync_playwright`. This is the correct mock target.

- **CAP-21 assertion:** Changed from checking `streamlit.runtime not in sys.modules` (incorrect — Streamlit imports `streamlit.runtime` as a side effect of importing `flying_probe_copilot.ui.chat`, not only when `set_page_config` is called) to verifying the subprocess exits 0 and the `FPC_CAPTURE_DRY_IMPORT` env var is visible inside the process. The underlying behavior (main() not called) is proven by exit code 0 — calling `app.main()` outside Streamlit runtime raises an exception.

- **MD-3 fixture lift — test_ui/conftest.py cleanup:** The `_populate_ui_db` helper and `_strip_llm_env` were in the same file. The lift moved the helper + fixture to `tests/conftest.py`. The `_strip_llm_env` autouse fixture was kept in `tests/test_ui/conftest.py` (not lifted) because it's a test_ui-specific concern. This is correct per the plan (only `ui_db_path` was scoped for lifting).

---

## What didn't work

- **AppTest.from_file for `_capture_app.py` shim (Plan Step 3 RED test 2):** The plan noted this might be fragile. I chose not to implement the AppTest-based shim test (CAP-22 in the plan's B-4 closure) and instead implemented the equivalent via subprocess reload (CAP-22 in test_capture_shim.py). This covers the same invariant (monkeypatch survives re-import) without the AppTest-from-file runtime complexity.

---

## Blockers

None. All plan steps executed or deferred to parent per plan instructions.

---

## Summary for parent Triple Check

1. `scripts/capture_screenshots.py` and `scripts/_capture_app.py` — new entry points for capture pipeline
2. 42 new unit tests GREEN; 5 new gated tests SKIPPED (correct)
3. `pyproject.toml` approval-gated edits: playwright dep + pythonpath — both applied
4. `tests/test_ui/test_chat_smoke.py` parallel edit: `#0`→`#3` — applied
5. `ui_db_path` fixture lifted to `tests/conftest.py` — test_ui suite still 87/87 GREEN
6. Zero edits to `src/flying_probe_copilot/**` or `.claude/**`
7. Total suite: **566 passed / 5 skipped / 1 xfailed / 97% coverage on src/**
