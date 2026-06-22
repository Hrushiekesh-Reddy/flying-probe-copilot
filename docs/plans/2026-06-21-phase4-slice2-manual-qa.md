# Manual QA — Phase 4 Slice 2

**Date:** 2026-06-21
**Tier:** Medium
**Branch:** `feature/phase4-slice2-screenshots` (committed as `b7ca25c`, not pushed)

Parent has verified end-to-end in-session: live capture script produced all 6 portfolio-grade JPGs + valid GIF89a, suite 566/5/1 at 97%, and the Co-Pilot screenshot shows the canned tombstoning answer with the Citations expander opened showing `failure-modes/tombstoning.md#3`. Owner QA is therefore a light eyeball pass.

## 5-minute checklist for owner

1. **Local: re-run the capture script.** Should complete in ~30 s with no output (silent success).
   ```bash
   uv run python scripts/capture_screenshots.py all --db data/db/sample.duckdb --out docs/img
   ```
   - Expect: 6 JPGs + `demo.gif` in `docs/img/`, file timestamps updated, no traceback.
   - Note: the captures are byte-different each run (timestamps render into the dashboard) — `git diff docs/img/` will always show modifications. That's fine; do NOT commit the re-captures unless the dashboard's visual design actually changed.

2. **Local: re-run the test suite.** Should be 566 passing / 5 skipped / 1 xfailed.
   ```bash
   uv run pytest -q
   ```

3. **Local: open `docs/img/demo.gif` directly.** A 12-second loop cycling Overview → Yield → Pareto → SPC → Anomalies → Co-Pilot. The Co-Pilot frame should show:
   - User bubble: "what causes tombstoning?"
   - Assistant bubble: "Likely causes of tombstoning: (1) uneven pad heating during reflow ..."
   - **Open** "Citations (1)" expander showing `failure-modes/tombstoning.md#3`.

4. **Local: open `README.md` in any markdown previewer.** The "Dashboard at a glance" section should show:
   - The animated `demo.gif` first
   - Then the 2×3 hero strip of static screenshots below it
   - All screenshot labels (Overview / Yield / Pareto / SPC / Anomalies / Co-Pilot) still match the images

5. **Local: spot-check `docs/case-study.md` line 123.** The "Capture screenshots from CI, not by hand" retrospective sentence should now end with an italic `*[Resolved 2026-06-21 — slice 2 shipped automated capture; see scripts/capture_screenshots.py and the slice-2 brief.]*` footnote-resolve.

6. **After push to GitHub: confirm the gif animates inline on the rendered README.** GitHub auto-plays GIFs; if static, the file got corrupted in transit (unlikely — GIF89a is what we wrote).

## What to escalate (don't fix in-session — surface as a follow-up chip)

- Any of the 6 hero-strip JPGs render blank, mis-cropped, or clearly different aspect from slice 1.
- The `demo.gif` is > 5 MB (GitHub still renders up to 10 MB but README load slows).
- A test from the existing 524-baseline is suddenly failing (capture script shouldn't have touched any production code).
- The Co-Pilot screenshot shows a refusal or the Live Gemini path instead of the canned answer (means the shim monkeypatch broke — debug with `FPC_CAPTURE_DRY_IMPORT=1 python -c "import scripts._capture_app"` and check `chat.answer_question.__qualname__`).

## What's deliberately not covered

- **Visual-diff regression.** No perceptual-hash assertion across runs. Adding one would couple us to Chromium font rendering.
- **Live Gemini integration via the capture path.** The Phase 3 live eval (`RAG_RUN_LLM_EVAL=1`) covers that separately.
- **Repeated-capture race conditions.** Single-user dev workflow, not a server.
- **GitHub Actions wiring.** Explicitly slice 3 scope.
