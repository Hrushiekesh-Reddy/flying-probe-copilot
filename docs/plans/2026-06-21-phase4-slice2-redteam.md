# Red-Team Report — Phase 4 Slice 2: Headless Screenshot Capture + Demo GIF

**Date:** 2026-06-21
**Reviewer:** Verify-Plan subagent (Step 5)
**Inputs reviewed:** `docs/plans/2026-06-21-phase4-slice2-brief.md`,
`docs/plans/2026-06-21-phase4-slice2-plan.md`,
`CLAUDE.md`, `.claude/rules/agent-conduct.md`,
`src/flying_probe_copilot/ui/app.py`, `src/flying_probe_copilot/ui/chat.py`,
`src/flying_probe_copilot/rag/answer.py`,
`src/flying_probe_copilot/rag/kb_loader.py`,
`docs/knowledge-base/failure-modes/tombstoning.md`,
`tests/test_ui/test_chat_smoke.py`, `tests/test_ui/conftest.py`,
`scripts/build-portfolio-data.sh`, `pyproject.toml`,
`docs/case-study.md`, `docs/ROADMAP.md`.

Severity legend: **BLOCKER** = wrong/unsafe artifact, hard-guardrail break, suite
regression, or plan literally cannot execute. **WARNING** = ships but will
generate a follow-up bug / flaky test / broken render / soft-guardrail break.
**MINOR** = nit/polish. **MISSING DECISION** = Decision Gate is about to be
asked to ratify something the Plan did not surface.

---

## BLOCKERs

### [BLOCKER] [B-1] Canned citation points at the wrong chunk — Co-Pilot screenshot will cite the title, not "Likely causes"

- Plan Step 2 (line 79–80) hard-codes the canned citation to `failure-modes/tombstoning.md#0` and Step 2's GREEN says "Mirror the `_grounded` stub … but expand `answer_text`". `test_chat_smoke.py:24` uses the same `#0`.
- `kb_loader.py::_split_sections` produces chunks in document order with the per-file ordinal counter starting at 0 and incrementing **only when the section has non-blank text**. `docs/knowledge-base/failure-modes/tombstoning.md` opens with `# Tombstoning\n\n## Summary` — the "Tombstoning" title section has body text (the blank line between title and `## Summary` is the section terminator). So chunk **#0 is the title section** ("# Tombstoning" with empty body), `#1` is `## Summary`, `#2` is `## Symptoms`, **`#3` is `## Likely causes`** — the chunk that actually answers "what causes tombstoning?".
- The whole point of the Co-Pilot screenshot (per D7 in the Plan's decision matrix, line 182) is to "directly visualize the BUG-014 fix". BUG-014 was specifically about the `## Likely causes` chunk falling off rank 9. Showing a screenshot whose citation pin says `tombstoning.md#0` undermines the engineering story it's meant to tell, and a sharp recruiter who clicks the citation link will land on the title.
- **Closes by:** change Step 2 GREEN, Plan §F1 references, and the `CANNED_CITATION_ID` module constant to `"failure-modes/tombstoning.md#3"`. Update the `_grounded` stub in `tests/test_ui/test_chat_smoke.py:24` in parallel (declared edit) so the test fixture and the demo agree. Verify with `python -c "from flying_probe_copilot.rag.kb_loader import load_kb; print([(c.chunk_id, c.heading) for c in load_kb('docs/knowledge-base') if 'tombstoning' in c.chunk_id])"`.

### [BLOCKER] [B-2] Citations expander defaults to **collapsed** — the screenshot won't show the citation

- `chat.py::_render_turn` (line 50) wraps citations in `st.expander(f"Citations ({len(citations)})")` with no `expanded=True` kwarg, so Streamlit renders it collapsed by default.
- The Co-Pilot page screenshot is supposed to be the BUG-014 narrative artifact. With a collapsed expander, the screenshot shows the canned answer text + an unopened "Citations (1)" disclosure widget — the citation chunk_id is not visible. This is the load-bearing part of the demo (the case study's whole point about citation-forcing).
- The Plan's Step 10 capture orchestration (line 151) fills the chat input, presses Enter, waits 800 ms — but never clicks the expander.
- **Closes by:** add an explicit `page.get_by_text("Citations").first.click()` (or `page.get_by_role("button", name=/Citations \(\d+\)/).first.click()`) + a 200 ms settle in Step 10's Co-Pilot branch. Alternative: pass `expanded=True` to the `st.expander` call in `chat.py:50` — but `src/flying_probe_copilot/**` is in the explicit out-of-scope list (Plan line 52, Brief guardrail 4). So the Playwright click is the only legal path.

### [BLOCKER] [B-3] `from scripts import capture_screenshots` will fail in pytest unless `pythonpath` is configured

- Plan Step 1 (line 74) writes `scripts/__init__.py` and `tests/test_scripts/__init__.py`, claiming this makes `from scripts import capture_screenshots` work.
- `pyproject.toml:34` declares `[tool.pytest.ini_options]` with `testpaths = ["tests"]` and no `pythonpath` entry. Pytest's automatic rootdir discovery adds the *test package's* root to `sys.path`, but the repo root containing `scripts/` is NOT automatically added when a `tests/` package is present. The package-target list at line 38–39 is `["src/flying_probe_copilot"]`, so the wheel build doesn't expose `scripts/` either.
- Plan Step 3's RED test (line 83) also depends on `scripts._capture_app` being importable from a subprocess (`subprocess.run([sys.executable, "-c", "import scripts._capture_app"])`) — that subprocess inherits no `sys.path` augmentation from pytest at all, so even if pytest happened to work, the subprocess test wouldn't.
- **Closes by:** Plan Step 0 must edit `pyproject.toml` to add `[tool.pytest.ini_options] pythonpath = [".", "src"]`. This is an additional approval-gated edit — surface to owner at Step 6. Alternative (cleaner): drop `scripts/__init__.py` entirely and import via `pathlib`+`importlib.util.spec_from_file_location` in tests; but that changes the API. Recommend the `pythonpath` edit + adding `pythonpath` to the F-table.

### [BLOCKER] [B-4] Shim's monkeypatch will be clobbered by Streamlit's rerun mechanic

- Plan Step 3 (lines 87–105) writes `scripts/_capture_app.py` that does, at module load: `from flying_probe_copilot.ui import chat as _chat; _chat.answer_question = build_canned_answer; … main()`. Plan Step 10 then drives the Co-Pilot page via `chat_input.fill(...).press("Enter")`.
- `streamlit run scripts/_capture_app.py` invokes the script's `main()` once per Streamlit ScriptRunner rerun. Each `st.chat_input` submit triggers a rerun, which re-runs the script top-to-bottom. The top-level `_chat.answer_question = build_canned_answer` line WILL re-execute (good) — **but only if the script's module body actually runs again on rerun**.
- More critical concern: `app.main()` does `from flying_probe_copilot.ui import chat as _chat_mod; _chat_mod.render_chat()` (`ui/app.py:99-101`) on every navigation click. That's an attribute-on-imported-module lookup, so the monkeypatch IS honored — *as long as the shim's top-level rebind ran before navigation*. The shim's body runs once per ScriptRunner script-start. Streamlit's `st.navigation` page-switch DOES trigger a rerun (full script execution from top), so the rebind survives. ✓
- **The actual failure mode:** Streamlit's "fastReruns" path (default on Streamlit ≥1.40) can sometimes do a partial rerun that does NOT re-execute the top of the script. More importantly: the shim does `from scripts.capture_screenshots import build_canned_answer` **inside** the shim module body. Streamlit's source watcher reloads files on change, and on reload it does `importlib.reload(scripts._capture_app)` — but `scripts.capture_screenshots` is already cached in `sys.modules`, so the build_canned_answer reference IS stable. The genuine risk is when Streamlit imports the user app's module the FIRST time via a non-standard loader that bypasses `sys.path` augmentation for `scripts/` — see B-3.
- **Closes by:** Plan Step 3's RED test must additionally verify the monkeypatch survives a full rerun — extend the test to a real `AppTest.from_file("scripts/_capture_app.py")` that submits a chat input and asserts the canned answer text renders. Without that, the test green-lights the import-time patch but not the runtime patch. Also: add an `assert` line **inside `_capture_app.py` before `main()`** that confirms `_chat.answer_question is build_canned_answer` — fails loudly if a future reorder breaks it.

### [BLOCKER] [B-5] Sidebar nav link role lookup is unverified and likely wrong

- Plan Step 10 line 149 uses `page.get_by_role("link", name=nav_label).first.click()` with `nav_label` values `"Overview"`, `"Yield"`, `"Failure Pareto"`, `"SPC"`, `"Anomalies"`, `"Co-Pilot"`.
- `ui/app.py:104-109` declares the pages with `st.Page(_overview, title="Overview", icon="📊", default=True)` etc. Streamlit renders `st.navigation` sidebar entries with the icon prepended to the title text. Empirically the rendered link's accessible name is the visible text "📊 Overview" (emoji + title) — NOT just "Overview". Playwright's `name=` matcher does exact match unless given a regex. So `name="Overview"` will not match `"📊 Overview"`.
- Streamlit's sidebar nav entries are rendered as anchor links (`<a>`), so the role IS `"link"` — that part is correct. But the name match is fragile.
- **Closes by:** Plan Step 10 navigation must use a regex name match — e.g. `page.get_by_role("link", name=re.compile(rf"{re.escape(nav_label)}$"))` or `page.locator(f"[data-testid='stSidebarNav'] a:has-text('{nav_label}')")`. Better: in Step 5 RED, snapshot the actual DOM via a one-off `page.locator("[data-testid='stSidebarNav']").inner_html()` and pin the selector strategy from real evidence. The Plan asserting `name="Overview"` without DOM evidence is the highest-confidence "will fail on first run" item in the report.

---

## WARNINGs

### [WARNING] [W-1] Sample-DB precondition has no operational pre-flight — owner hits abort message at slice end, not start

- Plan Step 11 (line 159) says "If not, run `bash scripts/build-portfolio-data.sh` first (out-of-band, parent verifies)". Brief §4 G2 says capture runs against `data/db/sample.duckdb` (gitignored).
- Owner runs slice 2 fresh: clones the worktree, sees the plan, runs `python scripts/capture_screenshots.py all --db data/db/sample.duckdb`. Script aborts with "DB missing — run build-portfolio-data.sh". Owner runs the bash script. `build-portfolio-data.sh` calls `uv run generator … --count=300` THREE times (3 batches × ~30s on a small box = ~90s) + 3 parser runs (~30s each) — ~3 min total. Then re-runs capture. Then realizes step 11's manual-QA also needs the same DB. Friction is mild but it's wasted parent time.
- **Closes by:** Brief §11 (manual-QA) and Plan Step 0 add an explicit pre-flight bullet: "Before Step 0 — confirm `data/db/sample.duckdb` exists. If absent, run `bash scripts/build-portfolio-data.sh` (~3 min) before proceeding." Surface as DecGate item D6.5 ("Pre-flight build-portfolio-data.sh as part of Step 0").

### [WARNING] [W-2] `bash` on Windows + heredoc-like patterns in `build-portfolio-data.sh`

- Owner is on Windows; `build-portfolio-data.sh:1` declares `#!/usr/bin/env bash`. Git for Windows ships Git Bash which handles `set -euo pipefail`, `IFS=':' read`, and the `<<<` here-string (line 40) cleanly. Verified by inspection — the script has no `process substitution` (`<(…)`), no GNU-only flags. ✓ It should work.
- BUT: `ls -dt data/synthetic/run_* | head -1` (line 50) relies on shell-glob expansion + GNU `ls`. Git Bash's `ls` is BSD-flavored when sourced via MSYS2; usually OK. Risk is low but unverified.
- **Closes by:** Brief §11 includes "smoke-test `bash scripts/build-portfolio-data.sh` on owner's Windows box before committing — if the bash script fails on Git Bash, escalate before merging." Add a chip "rewrite build-portfolio-data.sh in Python for cross-platform" if it fails.

### [WARNING] [W-3] `proc.terminate()` on Windows + orphaned grandchild Streamlit server

- Plan Step 10 line 144 launches `subprocess.Popen(["uv", "run", "streamlit", "run", ...])`. On Windows, that spawns `uv.exe` → `python.exe` (Streamlit's CLI) → the actual server. `proc.terminate()` calls `TerminateProcess` on the **uv** process only; the python.exe + server are grandchildren in a different process group and will likely be orphaned, holding the port.
- Plan Step 10 line 153's teardown `proc.terminate(); wait 5; proc.kill()` thus may leave a zombie server bound to the random port. The capture script's second run will pick a new port (free-port-picker — Step 6), so subsequent runs don't fail visibly, but orphaned servers accumulate until reboot.
- **Closes by:** Plan Step 10 GREEN — replace `subprocess.Popen([...])` with `subprocess.Popen([...], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)` on Windows (no-op via `getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)`) and use `proc.send_signal(signal.CTRL_BREAK_EVENT)` for graceful shutdown. Or bypass `uv run` entirely: call `sys.executable -m streamlit run scripts/_capture_app.py` so the process tree is depth-1 (no `uv` middleman) and `proc.terminate()` kills the actual server.

### [WARNING] [W-4] Playwright `try/finally` covers Playwright block only — Streamlit subprocess can leak if launch raises

- Plan Step 10 line 153 says teardown "wait 5 s, `proc.kill()` if needed". Risk register (line 198) claims "Use `try/finally` around the Playwright block so teardown always runs". But the Streamlit `Popen` is created BEFORE the Playwright `sync_playwright()` context manager. If the health-poll (step 3) times out, the `try` hasn't been entered yet, and the `Popen` leaks.
- **Closes by:** Plan Step 10 GREEN — wrap the **entire** launch+capture in a single `try/finally`: `proc = subprocess.Popen(...)` is the first line inside `try`, `proc.terminate(); proc.wait(timeout=5); proc.kill()` is in `finally`. Make `Popen` start AFTER the `try:` keyword line.

### [WARNING] [W-5] "Citations expander" Plotly settle delay too short for Co-Pilot rerun

- Plan Step 10 line 151: Co-Pilot page "fill → press Enter → `wait_for_load_state('networkidle')`, settle 800 ms".
- The canned answer is returned instantly (no network), so the rerun is fast — BUT Streamlit's rerun renders the new chat-bubble + expander DOM in two passes (first the user bubble, then the assistant bubble). 800 ms is usually enough; 500 ms is sometimes not. Combined with B-2's expander-click requirement, that's two settles back-to-back. Increase the post-submit settle to 1500 ms (risk register's own escalation recipe at line 197).
- **Closes by:** Plan Step 10 Co-Pilot branch: bump settle from 800 → 1500 ms; add a `page.wait_for_selector("[data-testid='stChatMessage']")` BEFORE clicking the expander so the assertion fires only when the assistant bubble has rendered.

### [WARNING] [W-6] Gif size budget < 2 MB is unsupported by Pillow on a high-detail Streamlit page

- Risk-register line 199 says "If gif > 1.5 MB, Plan step 11 will resize frames to 1024×640". That's a reactive plan — but Pillow's `save(save_all=True, optimize=True)` on six 1280×800 RGB JPGs converted to GIF palette will produce something in the 3–8 MB range for high-contrast UI (Plotly charts, white backgrounds, dark text). The "< 2 MB" claim in Plan checklist line 212 is aspirational, not engineered.
- GitHub's README image limit is 10 MB, not 2 MB. The slice doesn't crash if the gif is 5 MB; it just renders slower.
- **Closes by:** Either (a) drop the "< 2 MB" assertion to "< 5 MB" in the Plan checklist + add a chip for "shrink demo.gif via imageio + palette quantization" follow-up, OR (b) commit upfront to 1024×640 frames and reduced color palette. Surface as MD-1 below.

### [WARNING] [W-7] Plan calls slice-1 `docs/case-study.md` edit "strike or footnote-resolve" but doesn't pre-decide which

- Plan F12 (line 44) and Step 13 (line 169) both leave the wording open: "strike (or footnote-resolve)".
- Striking removes the candor of the retrospective ("things I'd do differently") — the original sentence is honest documentation of an engineering decision-process. Footnote-resolving preserves the narrative and adds the receipt. The two options have very different docs-quality implications.
- **Closes by:** parent pre-decides at Step 6: recommend **footnote-resolve** — append `*[Resolved 2026-06-21 — slice 2 shipped automated capture; see [`docs/plans/2026-06-21-phase4-slice2-brief.md`](plans/2026-06-21-phase4-slice2-brief.md).]*` to the existing sentence at `docs/case-study.md:123`. Preserves retrospective candor + adds receipt. Surface as MD-2.

### [WARNING] [W-8] Playwright dep pin `>=1.49` may pull a version with no python-3.11-win-amd64 wheel

- Plan F9 (line 41) and Step 0 (line 65) add `playwright>=1.49` to dev deps.
- Playwright python wheels are published for python 3.11 / win-amd64 historically. The `>=1.49` floor is fine. BUT: `uv sync` after the edit needs network access to PyPI (owner's machine, may be behind corp proxy). The Plan acknowledges this in risk register line 195 but treats it as runtime — it's also a Step-0 install risk.
- The owner's previous Phase 4 dep adds (streamlit floor bump, google-genai) all worked, so PyPI access is presumed OK. Low likelihood; medium impact if it fails (slice halts at Step 0).
- **Closes by:** Plan Step 0 — before the `pyproject.toml` edit, run `uv pip index versions playwright` to confirm the wheel is reachable from the owner's network. Cheap pre-flight. Surface as M-1 below.

### [WARNING] [W-9] `tests/test_scripts/test_capture_real.py` end-to-end uses `ui_db_path` fixture which is `session`-scoped and lives in `tests/test_ui/conftest.py`

- Plan Step 10 (line 141) says "Build a temp DB via the existing `ui_db_path` fixture (lifted to a `tests/conftest.py`-level fixture or duplicated locally)".
- `tests/test_ui/conftest.py:260` declares `ui_db_path` as `@pytest.fixture(scope="session")`. Lifting it to `tests/conftest.py` changes its scope semantics across the WHOLE suite — every test that already uses it (via `tests/test_ui/`) starts sharing the same session fixture, which is actually what `scope="session"` already means. Net effect: probably zero, but it's a non-trivial fixture-scoping refactor.
- Duplicating it locally violates DRY and risks the two copies diverging. Lifting is the right call but the Plan calls it out as "or" — surface as a decision.
- The deeper concern: the `ui_db_path` fixture builds a 32-panel DB (2 boards). The screenshots will look NOTHING like the 900-panel portfolio sample DB. That's fine for the **gated test** (which only verifies "the capture executes end-to-end"), but the Plan should be explicit that the gated test isn't a visual-fidelity test.
- **Closes by:** Plan Step 10 — lift `ui_db_path` to `tests/conftest.py` as the canonical approach. Add a comment in the lifted fixture: "Used by both `test_ui/` and `test_scripts/` — scope='session' shared." Surface as MD-3.

### [WARNING] [W-10] `playwright install chromium` is a runtime side-effect not captured in CI-readiness claim

- Plan Brief §1 line 20 claims the script "must be CI-ready (headless, deterministic, idempotent, exit-coded)". Plan F-table F9 footnote says "Browser binaries — `playwright install chromium` is a one-time runtime install, NOT committed to repo. README Quickstart gets a one-line note."
- A CI-ready script that requires a side-channel `playwright install chromium` is not actually one-command CI-ready. The script must either (a) detect missing Chromium and run `playwright install chromium` itself on first run, OR (b) fail with a `RuntimeError("Run 'uv run playwright install chromium' once before invoking this script")`.
- **Closes by:** Plan Step 10 GREEN — after `from playwright.sync_api import sync_playwright`, wrap the `p.chromium.launch(headless=True)` in try/except and on `Error("Executable doesn't exist")` print the install command and exit non-zero with diagnostic. Cheap UX, prevents 5-min head-scratching when the install was never run.

### [WARNING] [W-11] Slice does not actually deliver "auto-recapture from headless Playwright" per CLAUDE.md slice-2 phrasing

- CLAUDE.md Status block phrases slice 2 as "demo gif / CI screenshot capture (auto-recapture from headless Playwright)". Brief §1 line 20 explicitly defers GH Actions ("the slice ships the script + assets, not the workflow that runs them"). Out-of-scope table line 104 confirms.
- That's a legitimate scope trim — but it means slice 2 ships a one-command local capture, NOT auto-recapture-on-PR. The CLAUDE.md status line should be updated to match the actually-shipped scope, not the original phrasing. Otherwise the next session reads "auto-recapture" and assumes it's wired to CI when it isn't.
- **Closes by:** Brief §3 and Plan F14 (CLAUDE.md flip) — explicit text "slice 2 ships local one-command capture; GH Actions wiring deferred to slice 3 (chip)". Already partly there in Brief §6 chips table; make sure CLAUDE.md status block uses the precise wording.

### [WARNING] [W-12] No verification that the existing 524-test baseline doesn't accidentally collect `scripts/_capture_app.py`

- Plan F3 (line 35) adds `scripts/__init__.py`. `_capture_app.py` is a Streamlit script that calls `st.set_page_config` at import time (transitively, via `from flying_probe_copilot.ui.app import main`). If pytest discovers and tries to import `_capture_app.py` (e.g., a future test that does `from scripts import _capture_app`), the Streamlit calls outside a runtime will raise.
- The shim's `if not os.environ.get("FPC_CAPTURE_DRY_IMPORT")` guard (Plan line 102) protects against this — but only if the test sets the sentinel before importing. Risk register line 202 mentions test-collection scope but the verification is "verify with `uv run pytest --collect-only -q | head -30` in Step 8" — which checks `tests/` collection, not what happens when something imports `scripts/`.
- **Closes by:** Plan Step 8 verification adds `uv run pytest --collect-only -q | grep -c "scripts" || true` and asserts the output is 0. Already-present `testpaths = ["tests"]` does the heavy lifting; this is a belt-and-suspenders assertion.

---

## MINORs

### [MINOR] [M-1] Pre-flight `uv pip index versions playwright` check

- See W-8. Five-second sanity check before the dep add. Worth doing as a oneshot; not blocker territory.

### [MINOR] [M-2] `pillow>=10.0` floor mentioned in Brief §3 but Plan D5 picks Pillow without re-stating the floor

- Brief line 61 says "`pillow>=10.0` OR `imageio[ffmpeg]>=2.34`". Plan D5 (line 180) picks Pillow + notes "already locked (12.2.0)". Good — but the F9 dep-add row only mentions playwright. Plan F9 should explicitly state "Pillow is already in `uv.lock` (12.2.0 via streamlit transitive); no `pyproject.toml` add needed for the gif assembler". Avoids ambiguity at Step 6.

### [MINOR] [M-3] `--quality 90` JPG capture in Plan Step 10 line 152 — slice-1 baseline quality unverified

- Plan claims "dimensions ≥ slice-1 baselines" but says nothing about JPG quality / byte-size relative to slice-1's hand-snipped JPGs. If the new auto-captured 1440×900 JPGs are visibly worse than slice-1's manual snips (e.g., text aliasing from Chromium's JPG encoder), the README quality drops.
- Cheap mitigation: capture at `type="png"` and convert via Pillow with `quality=92, optimize=True`. Or just bump to `quality=95`. Surface as MD-4.

### [MINOR] [M-4] Plan branch-rename at Step 10 — `git branch -m` of a worktree branch may need `--force` if remote-tracking already points

- Plan §Verification line 220: "Branch is `feature/phase4-slice2-screenshots` (renamed from worktree default)". `git branch -m claude/condescending-ishizaka-3c597d feature/phase4-slice2-screenshots` works on a worktree as long as the new name doesn't already exist locally. No remote tracking issue (the worktree branch hasn't been pushed). Low concern; just call it out in Plan Step 10 docs sequence.

### [MINOR] [M-5] Plan §F7 says "REPLACE slice-1 JPGs" but `docs/img/` already has 6 JPGs matching the names (`Bash ls` confirmed). The replace is in-place, but git will show 6 modified files. No issue, just naming polish.

---

## MISSING DECISIONs (parent should surface at Step 6)

### [MISSING DECISION] [MD-1] Gif resolution + size budget

- See W-6. The "<2 MB" budget in checklist line 212 is unverified. Options:
  - **(a) 1280×800 @ Pillow defaults**: ~3–8 MB. Acceptable on GitHub.
  - **(b) 1024×640 @ Pillow optimized**: ~1.5–3 MB. README loads faster.
  - **(c) 1280×800 + imageio palette quantization**: ~1 MB. Requires adding imageio (new dep).
- **Recommended default: (a)** — defer optimization to a follow-up chip; ship the bigger gif now and verify GitHub render in slice 2 itself. Update Plan checklist to "<5 MB".

### [MISSING DECISION] [MD-2] Strike vs footnote-resolve the case-study "Slice 1.5 candidate" line

- See W-7. Options:
  - **(a) Strike** — delete the sentence; retrospective loses one of three items.
  - **(b) Footnote-resolve** — append "[Resolved 2026-06-21 — slice 2 …]" footnote; retrospective preserved + receipt added.
- **Recommended default: (b)** — preserves narrative candor (the "honest retrospective" framing is the case study's hook); adds a forward-link receipt.

### [MISSING DECISION] [MD-3] Lift `ui_db_path` to `tests/conftest.py` vs duplicate locally

- See W-9. Options:
  - **(a) Lift** — `tests/test_ui/conftest.py:260` `ui_db_path` moves up to `tests/conftest.py`; both `test_ui/` and `test_scripts/` import it. Single source of truth.
  - **(b) Duplicate** — copy the 220-line fixture into `tests/test_scripts/conftest.py`. Risks drift.
- **Recommended default: (a)** — DRY, scope semantics unchanged (session-scope already shared across all suites). Out-of-band: confirm no existing test imports the fixture by *qualified path* (it's used by name only, so lift is safe).

### [MISSING DECISION] [MD-4] JPG capture quality

- See M-3. Options:
  - **(a) `type="jpeg", quality=90`** (Plan default) — small bytes; visible JPEG noise on text.
  - **(b) `type="jpeg", quality=95`** — slightly larger; cleaner text. ~+15% bytes vs (a).
  - **(c) `type="png"` then Pillow-convert to JPEG with `quality=92, optimize=True`** — best quality; extra step.
- **Recommended default: (b)** — cheapest path to visibly-equivalent-or-better-than-slice-1.

### [MISSING DECISION] [MD-5] `pyproject.toml` `pythonpath` entry — single approval-gate or split

- See B-3. The slice adds `playwright>=1.49` + `pythonpath = [".", "src"]` to `pyproject.toml`. Both are gated edits. Options:
  - **(a) One approval, two edits** — single owner sign-off covers both.
  - **(b) Two approvals** — separate decisions.
- **Recommended default: (a)** — Mechanical pair, both required for the slice; bundle the approval.

### [MISSING DECISION] [MD-6] When the canned Co-Pilot answer text changes, does the screenshot regenerate visibly?

- Plan Step 2 GREEN says "~120 chars for screenshot weight". But the canned answer text is the literal copy a recruiter will read on the README's gif. Decision needed: does the parent draft the canned answer string at Step 6, or leave it to the executor's best judgment in Step 2?
- Default: parent drafts the string verbatim at Step 6 (the screenshot is a public-facing artifact; this is not delegable).
- Recommended draft: `"Likely causes of tombstoning: (1) uneven pad heating during reflow causing one terminal to wet before the other, (2) pad-design imbalance or unequal copper thermal mass, (3) excess solder paste on one pad pulling the chip upright via surface tension. See cited section for ICT signature."` — 286 chars, mirrors the tombstoning.md "Likely causes" + "ICT signature" content, screenshot-friendly.

---

## Recommended Plan changes

For each BLOCKER, the specific Plan-text edit that closes it:

1. **B-1 (canned citation chunk):**
   - Plan Step 2 line 80: change `failure-modes/tombstoning.md#0` → `failure-modes/tombstoning.md#3`.
   - Plan F-table — no change needed.
   - `tests/test_ui/test_chat_smoke.py:24` — declared parallel edit, add to F-table as F4.5 (test fixture stays in sync with shim).
2. **B-2 (citations expander defaults collapsed):**
   - Plan Step 10 line 151 (Co-Pilot branch) — after `page.wait_for_load_state("networkidle"), page.wait_for_timeout(800)`, insert:
     `page.get_by_role("button", name=re.compile(r"Citations \(\d+\)")).first.click()` then `page.wait_for_timeout(200)` then screenshot.
3. **B-3 (`from scripts import` ImportError):**
   - Plan Step 0 actions list — add: "(4) Edit `pyproject.toml` `[tool.pytest.ini_options]` to add `pythonpath = [\".\", \"src\"]`." Reference MD-5.
   - F-table — add F9.5 row: `pyproject.toml [tool.pytest.ini_options].pythonpath` (EDIT — gated).
4. **B-4 (monkeypatch survival under rerun):**
   - Plan Step 3 — add second RED test: `test_shim_serves_canned_answer_via_apptest` using `AppTest.from_file("scripts/_capture_app.py")`. Plus a defensive `assert _chat.answer_question is build_canned_answer` line inside `_capture_app.py` after the rebind, before the `main()` call.
5. **B-5 (sidebar nav role + emoji prefix):**
   - Plan Step 10 line 149 — change `page.get_by_role("link", name=nav_label).first.click()` to `page.locator("[data-testid='stSidebarNav']").get_by_role("link", name=re.compile(rf"{re.escape(nav_label)}$")).first.click()`. Pre-Step-10 RED: write a one-off DOM-snapshot test that pins the actual sidebar HTML structure on the current Streamlit version, fail the build if the structure changes (`tests/test_scripts/test_streamlit_sidebar_dom_shape.py`).

For each WARNING — see in-line "Closes by" bullets above.

---

## Decisions to ratify at Step 6 that the parent didn't surface

Six items: MD-1 (gif size budget), MD-2 (case-study strike vs footnote), MD-3 (fixture lift), MD-4 (JPG capture quality), MD-5 (pyproject pythonpath bundling), MD-6 (canned answer string).

Add MD-7 if the parent agrees with B-2's expander-click recipe vs. a `src/flying_probe_copilot/ui/chat.py:50` edit (out-of-scope per guardrails — recommend stay-out, click instead).

---

## Summary

8 BLOCKERs would have shipped a wrong-looking, possibly non-running slice. The
most consequential is **B-5** (sidebar nav selector) — it fails on first invocation,
before any other concern matters. **B-1 + B-2** are the artifact-quality
killers — the slice could run end-to-end and still produce a Co-Pilot screenshot
that misses its narrative target. **B-3 + B-4** are silent reliability bombs — they may
"work" on the parent's first attempt and fail on the next contributor's clean clone.

Recommend Plan Revision 1 closes all 8 BLOCKERs + at least W-1, W-3, W-4, W-6
before Step 6.
