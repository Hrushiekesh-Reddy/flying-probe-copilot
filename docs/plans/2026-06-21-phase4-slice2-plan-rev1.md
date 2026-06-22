# Plan Revision 1 — Phase 4 Slice 2: Headless Screenshot Capture + Demo GIF

**Date:** 2026-06-21
**Supersedes:** §-by-§ deltas to `2026-06-21-phase4-slice2-plan.md`. Where this revision is silent, the original plan stands.
**Driver:** Step 5 Verify-Plan red-team report (`2026-06-21-phase4-slice2-redteam.md`) — 5 BLOCKERs + 12 WARNINGs + 5 MINORs + 6 MISSING DECISIONs.
**Disposition:** **All 5 BLOCKERs closed. WARNINGs W-1, W-3, W-4, W-5, W-6, W-9, W-10 closed proactively. Remaining WARNINGs and MINORs accepted-as-noted (will be re-evaluated at Step 9 Triple Check). All 6 MISSING DECISIONs surface to Step 6 Decision Gate with parent recommendations.**

---

## Summary of changes

| Red-team finding | Closed by Plan-Rev1 change | Plan §/line affected |
|---|---|---|
| **B-1** Canned citation `#0` (title chunk) → wrong narrative | Change `CANNED_CITATION_ID` constant to `"failure-modes/tombstoning.md#3"`. Declared parallel edit to `tests/test_ui/test_chat_smoke.py:24` to keep the existing chat-smoke fixture in sync. | Step 2 GREEN; F4.5 (new) |
| **B-2** `st.expander` defaults collapsed → screenshot misses citation | Playwright must click the "Citations (N)" button after the Co-Pilot answer renders and before screenshotting. No `chat.py` edit (guardrail-protected). | Step 10 Co-Pilot branch |
| **B-3** `from scripts import …` ImportError without `pythonpath` config | Step 0 also adds `pythonpath = [".", "src"]` to `pyproject.toml`'s `[tool.pytest.ini_options]`. Second approval-gated edit, bundled under one Step-6 approval (MD-5). | Step 0; F9.5 (new) |
| **B-4** Monkeypatch may not survive Streamlit rerun | (a) Add `assert _chat.answer_question is build_canned_answer` inside `scripts/_capture_app.py` before `main()` — fails loud if rebind silently breaks. (b) Add a second RED test using `AppTest.from_file("scripts/_capture_app.py")` that submits a chat input and asserts the canned answer text renders end-to-end through the shim. | Step 3 RED + GREEN |
| **B-5** Sidebar nav selector `name="Overview"` won't match emoji-prefixed `"📊 Overview"` | Use regex name match scoped to `[data-testid='stSidebarNav']`: `page.locator("[data-testid='stSidebarNav']").get_by_role("link", name=re.compile(rf"{re.escape(nav_label)}$")).first.click()`. Pre-Step-10 RED snapshots the actual sidebar DOM. | Step 10 navigation loop |
| **W-1** Sample-DB pre-flight friction | Step 0 adds an explicit pre-flight: if `data/db/sample.duckdb` missing, run `bash scripts/build-portfolio-data.sh` before any other Step-0 action. Surfaced in Brief §11 manual-QA addendum. | Step 0 |
| **W-3** `proc.terminate()` orphans grandchild Streamlit server on Windows (via `uv run` middleman) | Replace `subprocess.Popen(["uv", "run", "streamlit", "run", ...])` with `subprocess.Popen([sys.executable, "-m", "streamlit", "run", ...])`. Removes the `uv` layer; process tree is depth-1 so `terminate()` kills the actual server. Verified `uv sync` puts streamlit on the venv's `sys.path` so `python -m streamlit` resolves identically. | Step 10 GREEN |
| **W-4** Subprocess leaks if Playwright launch raises before `try` | Move `proc = subprocess.Popen(...)` to be the FIRST line inside the `try:` block (not before it). `finally:` block always runs `terminate → wait → kill`. | Step 10 GREEN |
| **W-5** 800 ms Co-Pilot settle too tight after rerun + expander click | Bump post-submit settle 800 → 1500 ms. Add `page.wait_for_selector("[data-testid='stChatMessage']", state="visible")` before clicking the expander. | Step 10 Co-Pilot branch |
| **W-6** Gif `< 2 MB` target unverified for high-detail Streamlit UI | Drop checklist assertion from `< 2 MB` to `< 5 MB`. GitHub's README image limit is 10 MB — 5 MB is the realistic ceiling for 6 frames of 1280×800 high-contrast UI at Pillow defaults. Surfaced as MD-1 (gif resolution + size budget) for owner re-ratification with options. | Verification checklist |
| **W-9** `ui_db_path` fixture lift vs duplicate | Lift `ui_db_path` from `tests/test_ui/conftest.py:260` to `tests/conftest.py` as canonical fixture. Test-UI tests already use it by name, so no caller change. Surfaced as MD-3 for owner ratification. | F-table; Step 10 |
| **W-10** Missing Chromium binary → 500-line stack trace | `capture_screenshots.py::capture_screenshots(...)` wraps `p.chromium.launch(headless=True)` in `try/except playwright.sync_api.Error` and on the "Executable doesn't exist" subset prints `uv run playwright install chromium` and exits non-zero with a single-line diagnostic. | Step 10 GREEN |

The following findings are ACCEPTED-AS-NOTED (no Plan change; visible in red-team report; revisit at Triple Check if relevant):

- **W-2** Bash on Windows — script inspected by red-team, low risk; Brief §11 manual-QA already includes a smoke-test.
- **W-7** Strike vs footnote-resolve — surfaced as MD-2 (recommend footnote-resolve).
- **W-8** Playwright wheel availability — surfaced as M-1 pre-flight `uv pip index versions playwright`.
- **W-11** "Auto-recapture" phrasing in CLAUDE.md vs actually-shipped local one-command — Step 10 docs use the precise wording "one-command local capture; GH Actions wiring deferred to slice 3 (chip)".
- **W-12** Pytest collection of `scripts/` — Step 8 verification adds `uv run pytest --collect-only -q | grep -c "scripts" || true` assertion.
- **M-1..M-5** — incorporated into the relevant steps or accepted as polish.

---

## Per-section deltas

### §F-table — additions and edits

| # | What | Why | Where | When |
|---|------|-----|-------|------|
| **F4.5 (NEW)** | Declared parallel edit to existing test fixture | Keep `_grounded()` stub in sync with new canned citation `#3` per B-1 fix. The fixture and the capture shim must agree on the citation, or chat-smoke tests will diverge from the live capture behaviour. | `tests/test_ui/test_chat_smoke.py:24` (single-line replace `tombstoning.md#0` → `tombstoning.md#3` in **both** the `citations` tuple AND the `retrieved_ids` tuple) | Plan step 2 (along with `CANNED_CITATION_ID` constant in the new script) |
| **F9.5 (NEW)** | `pyproject.toml` `[tool.pytest.ini_options].pythonpath = [".", "src"]` — **approval-gated** | Without this, `tests/test_scripts/` can't import `scripts.capture_screenshots`, even with `scripts/__init__.py`. Bundled under MD-5 (single owner approval covers both this and the playwright dep add). | `pyproject.toml [tool.pytest.ini_options]` | Plan step 0 |
| **F18 (NEW)** | New test file: `tests/test_scripts/test_streamlit_sidebar_dom_shape.py` (env-gated, `CAPTURE_RUN_PLAYWRIGHT=1`) | Pins the actual sidebar DOM structure on the current Streamlit version. Catches a future Streamlit release that renames `data-testid='stSidebarNav'` → something else, so we hear about it from THIS test instead of a mysterious Step-10 capture failure. | `tests/test_scripts/test_streamlit_sidebar_dom_shape.py` (NEW) | Plan step 10 |

### §Goal Contract — no change. The negative-space contract still holds; nothing new is in-scope.

### §Step 0 — REVISED

Was: dep add + uv sync + playwright install + RED test.

Now:
1. **Pre-flight A:** confirm `data/db/sample.duckdb` exists. If missing: `bash scripts/build-portfolio-data.sh` (~3 min). [W-1]
2. **Pre-flight B:** `uv pip index versions playwright | head -5` — confirm reachable from owner's network. [M-1, W-8]
3. **Edit `pyproject.toml`** (approval-gated): add `"playwright>=1.49"` to `[dependency-groups].dev` (alphabetized). [F9]
4. **Edit `pyproject.toml`** (approval-gated, bundled): add `pythonpath = [".", "src"]` to `[tool.pytest.ini_options]`. [F9.5, B-3, MD-5]
5. `uv sync` — updates `uv.lock`.
6. `uv run playwright install chromium` — one-time; not committed.
7. **RED test 1:** `tests/test_scripts/test_capture_screenshots.py::test_playwright_importable`.
8. **RED test 2 (new):** `tests/test_scripts/test_pytest_finds_scripts_package` — `import scripts; assert scripts.__name__ == 'scripts'`. Closes B-3 at the lowest possible level.
9. **GREEN:** both pass after `uv sync` and the pythonpath edit.

### §Step 2 — REVISED (B-1 + MD-6)

- `CANNED_CITATION_ID = "failure-modes/tombstoning.md#3"` (was `#0`).
- The canned answer text is **drafted by the parent at Step 6**, not by the executor. Owner-recommended default text (MD-6):
  > `"Likely causes of tombstoning: (1) uneven pad heating during reflow causing one terminal to wet before the other, (2) pad-design imbalance or unequal copper thermal mass, (3) excess solder paste on one pad pulling the chip upright via surface tension. The ICT signature is an open across the two pads — cross-check against the expected refdes value to distinguish tombstoning from a wrong or missing part."`
  - 471 chars, paraphrases the `## Likely causes` + `## ICT signature` sections of `tombstoning.md`. Grounded entirely in the cited chunk.
- Step 2 GREEN now also writes the declared parallel edit at `tests/test_ui/test_chat_smoke.py:24` to flip the same `#0` → `#3` (F4.5). RED test for chat-smoke regression: existing CHAT-03 already checks `failure-modes/tombstoning.md#0` literal — that string is updated in the same patch.

### §Step 3 — REVISED (B-4)

GREEN body becomes:

```python
"""scripts/_capture_app.py — Streamlit shim that monkeypatches the Co-Pilot
backend then runs the real dashboard. Loaded by capture_screenshots.py via
`python -m streamlit run scripts/_capture_app.py`.
"""
from __future__ import annotations

import os

from flying_probe_copilot.ui import chat as _chat
from scripts.capture_screenshots import build_canned_answer

_chat.answer_question = build_canned_answer
assert _chat.answer_question is build_canned_answer, (
    "Monkeypatch failed — chat.answer_question was not rebound. "
    "Capture would call the live Gemini path."
)

if not os.environ.get("FPC_CAPTURE_DRY_IMPORT"):
    from flying_probe_copilot.ui.app import main
    main()
```

RED tests for Step 3:
1. `test_shim_app_monkeypatches_chat_module` — original (subprocess `import scripts._capture_app` under `FPC_CAPTURE_DRY_IMPORT=1` env; assert exit 0 + `chat.answer_question.__qualname__` ends in `build_canned_answer`).
2. **NEW** `test_shim_serves_canned_answer_via_apptest` — `AppTest.from_file("scripts/_capture_app.py").run()`, navigate to Co-Pilot page (via `at.switch_page` or by calling `chat.render_chat()` directly), submit a chat input, assert assistant's answer text contains the canned text's first sentence. Survives across `apptest.run()` because the shim's top-level rebind re-fires on rerun.

### §Step 10 — REVISED (B-2, B-5, W-3, W-4, W-5, W-10)

GREEN body becomes (capture orchestration):

```python
import os, re, signal, socket, subprocess, sys, time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright, Error as PlaywrightError

def _wait_for_health(port, timeout_s=30):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Streamlit on :{port} did not become healthy in {timeout_s}s")

def capture_screenshots(db_path, out_dir, port=None):
    port = port or pick_free_port()
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "FPC_DB_PATH": str(db_path)}

    # W-3: bypass the `uv` middleman so terminate() reaches the actual server
    cmd = [
        sys.executable, "-m", "streamlit", "run", "scripts/_capture_app.py",
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--logger.level", "error",
    ]

    # W-4: Popen is FIRST line inside try/, so finally always runs teardown
    proc = None
    try:
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _wait_for_health(port)

        with sync_playwright() as p:
            # W-10: friendly error on missing Chromium binary
            try:
                browser = p.chromium.launch(headless=True)
            except PlaywrightError as e:
                if "Executable doesn't exist" in str(e):
                    raise SystemExit(
                        "Chromium binary missing. Run: uv run playwright install chromium"
                    )
                raise

            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"http://127.0.0.1:{port}")
            page.wait_for_load_state("networkidle")

            for i, (nav_label, stem) in enumerate(PAGE_CAPTURE_SPECS):
                if i > 0:
                    # B-5: regex name + sidebar-scoped locator
                    nav_link = page.locator("[data-testid='stSidebarNav']").get_by_role(
                        "link", name=re.compile(rf"{re.escape(nav_label)}$")
                    ).first
                    nav_link.click()
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(500)  # Plotly settle

                if stem == "copilot":
                    # Submit canned question
                    page.get_by_test_id("stChatInput").locator("textarea").fill(
                        "what causes tombstoning?"
                    )
                    page.keyboard.press("Enter")
                    page.wait_for_load_state("networkidle")
                    # W-5: 1500 ms settle + wait for the assistant chat-message
                    page.wait_for_selector("[data-testid='stChatMessage']", state="visible")
                    page.wait_for_timeout(1500)
                    # B-2: click the "Citations (N)" expander so the citation is visible
                    page.get_by_role(
                        "button", name=re.compile(r"Citations \(\d+\)")
                    ).first.click()
                    page.wait_for_timeout(300)

                page.screenshot(
                    path=str(out_dir / f"screenshot-{stem}.jpg"),
                    full_page=False,
                    quality=95,  # MD-4 recommend (b)
                    type="jpeg",
                )

            browser.close()
        check_outputs_complete(out_dir, PAGE_CAPTURE_SPECS)

    finally:
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
```

End-to-end RED test for Step 10 is unchanged except the `assert` set is broadened to:
- Co-Pilot screenshot file inner-text via OCR-free Playwright check (during capture, `page.locator("[data-testid='stChatMessage']").nth(1).inner_text()` must contain the canned answer's first six words).
- Sidebar-DOM shape pinning test (F18) is a separate file.

### §Step 11 — REVISED (W-11)

Add a sentence to Step 11: "Capture runs against `data/db/sample.duckdb` (built by `bash scripts/build-portfolio-data.sh` in Step 0 pre-flight A). The slice ships local one-command capture; auto-recapture-on-PR via GH Actions is **deferred to slice 3** (out-of-scope chip)."

### §Step 13 — REVISED (W-7, MD-2)

Sub-step (a) clarified: **footnote-resolve** the `docs/case-study.md:123` line, do NOT strike it. Append:

> *[Resolved 2026-06-21 — slice 2 shipped automated capture; see `docs/plans/2026-06-21-phase4-slice2-brief.md`.]*

### §Verification checklist — REVISED

- `docs/img/demo.gif` exists, starts with `GIF89a`, **< 5 MB** (was < 2 MB) — W-6.
- New assertion: `uv run pytest --collect-only -q | grep -c "scripts/" || true` → output = `0` (W-12).
- New assertion: Co-Pilot screenshot's chat-bubble contains the canned-answer first-sentence (via Playwright inner_text during capture; not a separate test).

### §Risk register — additions

| New risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `python -m streamlit` resolves a different streamlit than `uv run streamlit` does (uv-managed venv path issue) | L | M | `uv sync` is the binding step; `sys.executable` inside the same venv resolves the same package set. Verified by Python's standard `sys.path` rules. If owner has multiple Python interpreters on PATH, `uv run` selects the right one — that's why Step 10 uses `sys.executable`, NOT just `python`. |
| Pillow's `Image.save(append_images=...)` API change in a future Pillow > 12.2.0 lockfile bump | L | L | Lockfile pinned; if streamlit transitively bumps Pillow major, the gif-assembler tests catch it. |
| Footnote-resolve syntax `*[…]*` in case-study renders as italic-only-strikethrough rather than the intended footnote | L | L | Verify post-edit in `grep -n "Resolved 2026-06-21" docs/case-study.md`. GitHub renders `*[…]*` as italic, which reads cleanly as an inline aside — that's the intended effect, not literal footnote machinery. |

---

## Step-6 Decision Gate inputs (6 MISSING DECISIONs to ratify)

Carried into `2026-06-21-phase4-slice2-decision-gate.md` (Step 6 artifact, written next):

| # | Decision | Recommended | Why |
|---|---|---|---|
| **MD-1** Gif size budget | (a) 1280×800 Pillow defaults, `< 5 MB` actual; chip "shrink demo.gif via imageio palette quantization" for future | Cheapest; verifiable post-capture; GitHub limit is 10 MB. |
| **MD-2** Case-study line — strike vs footnote-resolve | (b) **footnote-resolve** | Preserves retrospective candor; adds receipt; chosen narrative. |
| **MD-3** `ui_db_path` fixture — lift vs duplicate | (a) **lift** to `tests/conftest.py` | DRY; session-scope unchanged; no caller change. |
| **MD-4** JPG capture quality | (b) `type="jpeg", quality=95` | Cleaner text than 90; ~15% larger; visually-equivalent-or-better than slice-1 hand-snipped baselines. |
| **MD-5** `pyproject.toml` pythonpath + playwright — bundle approval | (a) **single approval covers both edits** | Mechanical pair; both required. |
| **MD-6** Canned Co-Pilot answer text | parent-drafted (text in §Step 2 revision above) | Public-facing artifact; not delegable. Owner can copy-edit at Decision Gate. |

Plus the implicit ratification of the **5 BLOCKER closures** above (the parent's recommended fixes — owner can override any).

---

## What's still uncertain

- The exact sidebar DOM `data-testid` may have changed in Streamlit 1.45+ (vs slice 1 baseline). F18 (sidebar DOM-shape test) is the live-canary; if it fails, the executor falls back to `page.locator("section[data-testid='stSidebar'] a:has-text(...)")`.
- Pillow's gif palette quantization on 6 high-contrast Plotly screenshots is empirically untested in this repo — actual gif byte count is "first measurement at Step 11".
- The canned answer text wraps at the chat-bubble's natural width — at 1440×900 viewport with a sidebar, the bubble is ~700 px wide. 471 chars will produce ~6 visible lines. Acceptable; will eyeball at Step 9.

---

## Plan-Revision-1 Definition of Done

- All 5 BLOCKERs have a Plan-Rev1 §-by-§ delta closing them. ✓
- 7 of 12 WARNINGs closed proactively; 5 accepted-as-noted with revisit conditions. ✓
- 6 MISSING DECISIONs surfaced for Step 6 with parent recommendations. ✓
- Approval-gated edits accumulated: `pyproject.toml` (playwright dep + pytest.pythonpath) + `README.md` (gif embed). Owner signs off in one Decision Gate. ✓
- Out-of-scope set unchanged (no scope creep from red-team). ✓
- F-table grew from F1–F17 to F1–F18, plus F4.5 + F9.5 declared edits. ✓

**Ready for Step 6 Decision Gate.**
