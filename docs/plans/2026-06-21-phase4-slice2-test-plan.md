# Test-Case Plan — Phase 4 Slice 2: Headless Screenshot Capture + Demo GIF

**Date:** 2026-06-21
**Author:** test-generator subagent (Step 4)
**Inputs:** `2026-06-21-phase4-slice2-brief.md`, `2026-06-21-phase4-slice2-plan.md`
**Audience:** Step 5 red-team, Step 6 Decision Gate, Step 7 exec
**Scope:** behavior-level test cases only — what to assert, not how to implement

> Conventions
> - `CAP-NN` IDs are stable and grep-able; reuse them as `test_capNN_*` in code.
> - "Helper" = pure function in `scripts/capture_screenshots.py` (no Playwright).
> - "Smoke" = `tests/test_scripts/test_capture_real.py` (env-gated `CAPTURE_RUN_PLAYWRIGHT=1`).
> - Where the Plan's TDD step already names a RED test, this doc adds the **adversarial siblings** the Plan missed.

---

## 1. Coverage matrix

| Helper / Behavior | Plan RED test | New IDs (this doc) | Total |
|---|---|---|---|
| `playwright` importable (Plan Step 0) | implicit | CAP-01, CAP-02 | 2 |
| Package markers (Plan Step 1) | implicit | CAP-03 | 1 |
| `build_canned_answer` (Plan Step 2) | 1 happy-path | CAP-10, CAP-11, CAP-12, CAP-13, CAP-14, CAP-15 | 6 |
| `_capture_app.py` shim (Plan Step 3) | 1 monkeypatch check | CAP-20, CAP-21, CAP-22, CAP-23 | 4 |
| `assemble_gif` (Plan Step 4) | 1 happy-path + 1 empty | CAP-30, CAP-31, CAP-32, CAP-33, CAP-34, CAP-35, CAP-36 | 7 |
| `PAGE_CAPTURE_SPECS` (Plan Step 5) | 1 shape check | CAP-40, CAP-41, CAP-42, CAP-43 | 4 |
| `pick_free_port` (Plan Step 6) | 1 happy-path | CAP-50, CAP-51, CAP-52, CAP-53 | 4 |
| `check_outputs_complete` (Plan Step 7) | 3 cases | CAP-60, CAP-61, CAP-62, CAP-63 | 4 |
| `parse_args` / `main` CLI (Plan Step 8) | 4 cases | CAP-70, CAP-71, CAP-72, CAP-73, CAP-74 | 5 |
| Approval-gated dep behavior | none | CAP-80, CAP-81 | 2 |
| End-to-end Playwright smoke (Plan Step 10) | 1 happy-path | CAP-90, CAP-91, CAP-92, CAP-93, CAP-94, CAP-95 | 6 |
| **Total new tests** | | | **45** |

Of the 45, **~10 are env-gated** (`CAPTURE_RUN_PLAYWRIGHT=1`); the remaining ~35 run in the default `uv run pytest` flow, satisfying brief G1 (≥4 new unit tests).

---

## 2. New test cases (numbered by ID)

### Helper group A — Playwright dep (CAP-01..02)

**CAP-01 — playwright SDK exposes `sync_playwright`**
- **Subject:** import-time availability of `playwright.sync_api`.
- **Setup:** none (post-`uv sync`).
- **Trigger:** `from playwright.sync_api import sync_playwright`.
- **Assert:** import does not raise; `sync_playwright` is a callable; calling `sync_playwright()` returns a context-manager object (does *not* require entering it — don't launch Chromium).
- **Rationale:** the Plan's Step-0 RED test only checks `hasattr`. A future `uv sync` that resolves to a broken wheel could give a `hasattr`-OK but call-time `ImportError`. This pins the actual public entry point.

**CAP-02 — playwright Python wrapper version floor**
- **Subject:** `playwright.__version__`.
- **Setup:** none.
- **Trigger:** `import playwright; from packaging.version import Version; v = Version(playwright.__version__)`.
- **Assert:** `v >= Version("1.49")`.
- **Rationale:** if someone later relaxes the `pyproject.toml` floor (`>=1.49`) or pins an older version, the capture script's `get_by_role(... name=...)` API may regress (only stable since 1.27 but `get_by_test_id` semantics changed in 1.42). Catches dep-floor drift.

---

### Helper group B — Package markers (CAP-03)

**CAP-03 — `scripts` package importable and does not run anything**
- **Subject:** `scripts/__init__.py` is empty (no side effects).
- **Setup:** none.
- **Trigger:** `import scripts; import scripts.capture_screenshots`.
- **Assert:** import succeeds; `scripts.__file__` ends with `__init__.py`; the imported module exposes `build_canned_answer`, `assemble_gif`, `PAGE_CAPTURE_SPECS`, `pick_free_port`, `check_outputs_complete`, `parse_args`, `main` as module attributes.
- **Rationale:** Plan asserts the test_scripts test sub-package is importable, but doesn't pin the public API surface of `capture_screenshots`. If a refactor renames `assemble_gif` → `build_gif`, every downstream call site changes silently — this test forces the rename to be deliberate.

---

### Helper group C — `build_canned_answer` (CAP-10..15)

**CAP-10 — citation chunk-id matches `failure-modes/<slug>.md#<int>` shape**
- **Subject:** `build_canned_answer("anything").citations[0]`.
- **Setup:** none.
- **Trigger:** call once.
- **Assert:** regex match `^failure-modes/[a-z][a-z-]*\.md#\d+$` (matches Plan but tightens: slug starts with a lowercase letter, no leading hyphen, integer index).
- **Rationale:** Plan's regex `r"failure-modes/[a-z-]+\.md#\d+"` allows a citation like `failure-modes/-.md#0` which would crash chat rendering. Tightening avoids silent-corruption.

**CAP-11 — citation points at a knowledge-base file that actually exists**
- **Subject:** referential integrity of `CANNED_CITATION_ID`.
- **Setup:** repo root resolvable from the test file.
- **Trigger:** parse `build_canned_answer("q").citations[0]`, split on `#`, resolve `docs/knowledge-base/<that path>`.
- **Assert:** `(repo_root / "docs/knowledge-base" / cite_path).exists()` is `True`.
- **Rationale:** **High-value.** A hard-coded `"failure-modes/tombstoning.md#0"` will silently drift if `tombstoning.md` is ever renamed or split. The Plan's stub mirrors `test_chat_smoke.py:18-25`, which has the same drift risk — locking citation to disk reality catches both at once.

**CAP-12 — citation chunk index is within the chunk count of the target file**
- **Subject:** `CANNED_CITATION_ID`'s `#<int>` is < the number of chunks `kb_loader.chunk_document` would produce for that file.
- **Setup:** `from flying_probe_copilot.rag import kb_loader` (already shipped Phase 3 slice 1).
- **Trigger:** load and chunk the target md file; count chunks.
- **Assert:** `int(chunk_idx) < len(chunks)`.
- **Rationale:** uncertain — recommend Decision Gate item: do we want to couple the test to `kb_loader`'s internal chunking, or is "file exists" enough (CAP-11)? Stronger version catches refactors that re-chunk; weaker version is faster. Recommend **strong (CAP-12 in)** because the screenshot will literally render a citation index a user can click on.

**CAP-13 — `Answer.refused` is `False`**
- **Subject:** `build_canned_answer(...).refused`.
- **Setup:** none.
- **Trigger:** call.
- **Assert:** `result.refused is False` (identity, not truthiness — `Answer.refused` is a frozen `bool`).
- **Rationale:** if `refused=True`, `render_chat` shows `REFUSAL_TEXT` and **no citation expander**, defeating the entire purpose of the Co-Pilot screenshot. Plan asserts citations exist but never that `refused` is the right value.

**CAP-14 — `answer_text` is free of markdown-hazard characters**
- **Subject:** `build_canned_answer(...).answer_text`.
- **Setup:** none.
- **Trigger:** call.
- **Assert:**
  - no triple backticks (` ``` `) → would open a code fence that breaks the citations `st.expander` below
  - no unmatched single backticks (count of `` ` `` is even)
  - no leading `#` (would render as h1, conflicting with the page header)
  - no leading `>` (would render as blockquote, visual noise)
  - length between 60 and 240 chars (Plan says ≥60; cap at 240 so the chat bubble fits the screenshot viewport)
- **Rationale:** **High-value.** The Plan says "expand answer_text to ~120 chars for screenshot weight" but never specifies what *content* is forbidden. A future helpful refactor that adds a code-block example would silently break the screenshot — and the failure mode (broken page render) would only show up at Step 11 capture time, not in unit tests.

**CAP-15 — deterministic output across calls**
- **Subject:** `build_canned_answer` is a pure function.
- **Setup:** none.
- **Trigger:** call twice with different `question` strings, then twice with the same string.
- **Assert:** all four `answer_text` / `citations` / `retrieved_ids` are identical (the question is only echoed into `Answer.question`, not into the body); `result_q1.question == "q1"` and `result_q2.question == "q2"` distinct.
- **Rationale:** if the function ever takes a `random.choice(...)` over a list of canned answers (a tempting "variety" refactor), the screenshot becomes non-reproducible across runs. Pin determinism.

---

### Helper group D — Streamlit shim (`scripts/_capture_app.py`) (CAP-20..23)

**CAP-20 — monkeypatch visible to a *different* import of `flying_probe_copilot.ui.chat`**
- **Subject:** the shim's `_chat.answer_question = build_canned_answer` rebinds the module attribute, not just a local alias.
- **Setup:** in a subprocess so module state is clean; set `FPC_CAPTURE_DRY_IMPORT=1`.
- **Trigger:** `python -c "import scripts._capture_app; from flying_probe_copilot.ui import chat as fresh; print(fresh.answer_question.__qualname__)"`.
- **Assert:** subprocess stdout contains `build_canned_answer` (not the original `answer_question` qualname).
- **Rationale:** **High-value, exactly the failure mode the user flagged.** If Streamlit reimports `chat` under a different `sys.modules` key (unlikely but possible with `streamlit run`'s script-runner machinery), `_chat.answer_question = ...` is invisible. This test simulates a second importer and proves the rebind is module-global.

**CAP-21 — shim does not call `app.main()` when sentinel env var set**
- **Subject:** `FPC_CAPTURE_DRY_IMPORT=1` short-circuit.
- **Setup:** subprocess with the env var.
- **Trigger:** `import scripts._capture_app`.
- **Assert:** subprocess exit code 0; `streamlit.runtime` is *not* in `sys.modules` (proves `st.set_page_config` was never called).
- **Rationale:** the Plan describes the short-circuit but never asserts it. If a later refactor moves `from ...app import main` to module-top, the dry-import will crash at `st.set_page_config` outside a Streamlit runtime — silently breaking CAP-20 and downstream tests.

**CAP-22 — shim reloaded twice in the same process is idempotent**
- **Subject:** repeated import of `scripts._capture_app` (simulates Streamlit hot-reload).
- **Setup:** single Python process, sentinel env var set.
- **Trigger:** `import scripts._capture_app; importlib.reload(scripts._capture_app); importlib.reload(scripts._capture_app)`.
- **Assert:** no exception raised; `flying_probe_copilot.ui.chat.answer_question is scripts.capture_screenshots.build_canned_answer` after each reload.
- **Rationale:** Streamlit's `streamlit run` hot-reload triggers module re-execution. Reload-unsafe shims (e.g., one that captures the original `answer_question` once and restores it on second-run) would unwire the monkeypatch on save. Catches the Plan's blind spot.

**CAP-23 — shim degrades cleanly if `scripts.capture_screenshots` import fails**
- **Subject:** import-error handling.
- **Setup:** subprocess with sentinel env var set, plus `PYTHONPATH` manipulated so `scripts.capture_screenshots` raises (e.g., by injecting a sitecustomize that pre-poisons `sys.modules["scripts.capture_screenshots"] = None`).
- **Trigger:** `import scripts._capture_app`.
- **Assert:** exit code is non-zero; stderr contains the string `capture_screenshots` (so the operator knows the failing import); does **not** silently fall back to live `answer_question` (which would then hit the real API in a capture run with no key).
- **Rationale:** the user explicitly flagged this. The worst failure mode would be a silent fallback where `_chat.answer_question` keeps its original value, and the capture pipeline then calls the real Gemini API in the Co-Pilot screenshot step — leaking the key, hanging on no-key, or producing a non-canned answer.

---

### Helper group E — `assemble_gif` (CAP-30..36)

**CAP-30 — frame-size mismatch is rejected or normalized**
- **Subject:** frames with mixed dimensions.
- **Setup:** build 3 in-memory `PIL.Image.new("RGB", (100,100))` plus 1 of `(200,150)`.
- **Trigger:** `assemble_gif([img100, img100, img200, img100], out_path, 200)`.
- **Assert (option A — recommended):** raises `ValueError` whose message names "frame size mismatch" and lists the offending index.
- **Assert (option B — fallback):** if normalization is chosen, all output frames are the same size as `frames[0]`; verify by reading the output gif's frame dimensions.
- **Rationale:** **High-value (Pillow gotcha).** Pillow's `save(append_images=...)` silently accepts mixed dims and writes a corrupt gif (only first frame renders correctly on most viewers). Plan never tests this. Recommend option A — uncertain → Decision Gate item.

**CAP-31 — `frame_duration_ms <= 0` raises**
- **Subject:** invalid duration.
- **Setup:** 2 valid frames.
- **Trigger:** `assemble_gif(frames, out_path, frame_duration_ms=0)` and `..., -100)`.
- **Assert:** raises `ValueError` whose message names `frame_duration_ms`.
- **Rationale:** Pillow accepts `duration=0` and produces an invalid (instantaneously-cycling) gif that crashes some viewers. Cheap guard.

**CAP-32 — one-frame input produces a valid single-frame GIF (not animated)**
- **Subject:** edge case `len(frames) == 1`.
- **Setup:** 1 in-memory `PIL.Image`.
- **Trigger:** `assemble_gif([img], out_path, 2000)`.
- **Assert:** uncertain — recommend Decision Gate item. Two valid options:
  - (a) Output is a valid 1-frame GIF, `Image.open(out).is_animated == False`; or
  - (b) Raises `ValueError("need >=2 frames for animation")`.
  Recommend (a) — it's defensive and matches Pillow's natural behavior.
- **Rationale:** Plan's `assemble_gif_empty_list_raises_value_error` covers `len==0` but not `len==1`. Without this, a future bug in `capture_screenshots` that captures only the first page would produce a non-failing gif assembly step followed by a confusing "1-frame demo".

**CAP-33 — output path's parent dir does not exist**
- **Subject:** filesystem prerequisite.
- **Setup:** `out_path = tmp_path / "nonexistent" / "demo.gif"`.
- **Trigger:** `assemble_gif(frames, out_path, 200)`.
- **Assert:** either auto-creates the parent (`out_path.parent.exists()` after call, file written) OR raises `FileNotFoundError` whose message names the missing parent dir. **Recommend auto-create** (UX: capture script's `--out` may point at a fresh dir).
- **Rationale:** Plan never specifies. Pillow's `save()` raises `FileNotFoundError` with a low-signal message. Define the contract.

**CAP-34 — very large frame completes within memory budget**
- **Subject:** scalability.
- **Setup:** 3 frames of `PIL.Image.new("RGB", (4096, 4096), color="red")`.
- **Trigger:** `assemble_gif(frames, out_path, 500)`.
- **Assert:** exits within 30 s (pytest `@pytest.mark.timeout(30)`); output file < 50 MB; first 6 bytes == `b"GIF89a"`.
- **Rationale:** Pillow's gif optimizer is memory-hungry on large palettes. Documents the upper bound. If this test is too slow for CI, mark `@pytest.mark.slow` — uncertain → Decision Gate item.

**CAP-35 — assembler does not leak open file handles (Windows-critical)**
- **Subject:** Pillow `Image.open(...)` returns a lazy file handle.
- **Setup:** write 6 JPGs to `tmp_path`; load each via `Image.open(path)` (no `.copy()` / `.close()`); pass to `assemble_gif`.
- **Trigger:** call; immediately try `tmp_path.unlink()` on each source JPG.
- **Assert:** all 6 unlinks succeed (on Windows, an open handle would raise `PermissionError [WinError 32]`).
- **Rationale:** **High-value, Windows-specific.** Per BUG-011 (resolved), the repo has prior pain with file-handle leaks on Windows. The assembler must `.close()` or `.copy()` source frames so they don't pin the JPG files — otherwise `--out docs/img/` would fail on the *second* capture run because the first run's JPGs are still open.

**CAP-36 — gif file size budget (proxy for `optimize=True` working)**
- **Subject:** Plan asserts gif < 2 MB (G3 brief gate). Pin in unit-land.
- **Setup:** 6 `PIL.Image.new("RGB", (1280, 800), color=(i*40, 0, 255-i*40))` frames (smooth gradient stand-in).
- **Trigger:** `assemble_gif(frames, out_path, 2000)`.
- **Assert:** `out_path.stat().st_size < 500_000` (synthetic frames; the real-world budget of 2 MB has headroom).
- **Rationale:** if `optimize=True` is dropped from the Pillow call, file size jumps 3-5×. Catches the regression in CI without needing a real capture run.

---

### Helper group F — `PAGE_CAPTURE_SPECS` (CAP-40..43)

**CAP-40 — tuple shape, length, order**
- **Subject:** the literal value.
- **Setup:** none.
- **Trigger:** `from scripts.capture_screenshots import PAGE_CAPTURE_SPECS`.
- **Assert:** `len(PAGE_CAPTURE_SPECS) == 6`; `PAGE_CAPTURE_SPECS == (("Overview","overview"), ("Yield","yield"), ("Failure Pareto","pareto"), ("SPC","spc"), ("Anomalies","anomalies"), ("Co-Pilot","copilot"))` (exact equality, tuple form).
- **Rationale:** Plan's Step 5 RED already covers this — listed for completeness in the matrix.

**CAP-41 — order matches README hero-strip image-link order**
- **Subject:** cross-file consistency: `PAGE_CAPTURE_SPECS` order must equal the order screenshots appear in `README.md`'s 2×3 hero strip table.
- **Setup:** read `README.md` from repo root; regex out the `screenshot-<stem>.jpg` references in order.
- **Trigger:** zip `PAGE_CAPTURE_SPECS` stems with the README-order list.
- **Assert:** `[stem for _,stem in PAGE_CAPTURE_SPECS] == readme_order` (`["overview","yield","pareto","spc","anomalies","copilot"]`).
- **Rationale:** **High-value cross-file invariant.** If someone reorders the hero strip in README (e.g., moves Co-Pilot to top) without updating the capture script, the gif and the README still look "fine" but the page ordering drifts. Catches narrative-vs-asset desync.

**CAP-42 — all 6 stems are valid POSIX path components**
- **Subject:** filename hygiene.
- **Setup:** none.
- **Trigger:** iterate the stems.
- **Assert:** each stem is lowercase, contains only `[a-z0-9-]`, no spaces, no slashes, length 1..32.
- **Rationale:** the Co-Pilot label has a hyphen (`Co-Pilot`) but the stem maps to `copilot` — protects against a future contributor copying the label verbatim and breaking the README's `docs/img/screenshot-Co-Pilot.jpg` (case-insensitive on Windows, case-sensitive on Linux CI).

**CAP-43 — each nav label exists as an `st.Page(title=...)` in `ui/app.py`**
- **Subject:** cross-module invariant: capture nav labels must match a real Streamlit page title.
- **Setup:** `import flying_probe_copilot.ui.app`; collect page titles by either (a) introspecting the module's source for `st.Page(..., title="...")` literals via `ast.parse` (preferred, no Streamlit runtime needed) or (b) running `app.main()` under AppTest and reading the navigation widget. Recommend (a).
- **Trigger:** extract the set of titles from the AST; compare to `{label for label,_ in PAGE_CAPTURE_SPECS}`.
- **Assert:** the capture set is a subset of (or equal to) the app set.
- **Rationale:** **High-value, the user explicitly flagged this.** If someone renames `st.Page(..., title="Co-Pilot")` to `"Copilot"` or `"AI Assistant"` and updates the screenshot stem but forgets to update the *click target* (`page.get_by_role("link", name="Co-Pilot")`), the Playwright run fails silently on the wrong page. This AST-level test catches the rename before the env-gated smoke runs.

---

### Helper group G — `pick_free_port` (CAP-50..53)

**CAP-50 — returns int in valid range and port is actually free**
- **Subject:** Plan Step 6 RED — listed for completeness.
- **Assert:** as plan.

**CAP-51 — two consecutive calls return different ports**
- **Subject:** no caching / no constant return.
- **Setup:** none.
- **Trigger:** `p1 = pick_free_port(); p2 = pick_free_port()`.
- **Assert:** `p1 != p2` (parallel-capture safety).
- **Rationale:** if the impl is ever optimized to `@lru_cache`, two captures running in parallel (or in a `pytest -n auto` future) collide on the same port. Cheap guard.

**CAP-52 — does not return privileged port `< 1024`**
- **Subject:** OS-assigned port is in the ephemeral range.
- **Setup:** repeat 50 times to reduce flakiness (Linux ephemeral range is 32768-60999; macOS/Windows differ).
- **Trigger:** collect 50 calls.
- **Assert:** `all(p >= 1024 for p in ports)`.
- **Rationale:** Plan asserts `1024 <= port <= 65535` once. A flaky single-shot test could pass while a real low-port assignment slips through in production. 50× is cheap.

**CAP-53 — socket error propagates with a clear message**
- **Subject:** behavior when `socket.bind` raises.
- **Setup:** monkeypatch `socket.socket` to a fake that raises `OSError("network unreachable")`.
- **Trigger:** `pick_free_port()`.
- **Assert:** the original `OSError` propagates (do not swallow); message intact.
- **Rationale:** silent fallback to `8501` here would mask a real network-stack problem at capture time. Pins the contract.

---

### Helper group H — `check_outputs_complete` (CAP-60..63)

**CAP-60 — all 6 present and non-empty → returns `None`**
- **Subject:** Plan Step 7 happy-path — listed for completeness.
- **Assert:** as plan.

**CAP-61 — missing file → `FileNotFoundError` naming the file**
- **Subject:** Plan Step 7 — listed.

**CAP-62 — zero-byte file → `ValueError` naming "empty screenshot"**
- **Subject:** Plan Step 7 — listed.

**CAP-63 — wrong extension (`.png` instead of `.jpg`) → raises**
- **Subject:** strict extension check.
- **Setup:** create `screenshot-overview.png` instead of `.jpg` in `tmp_path` for one of the 6.
- **Trigger:** `check_outputs_complete(tmp_path, PAGE_CAPTURE_SPECS)`.
- **Assert:** raises `FileNotFoundError` for `screenshot-overview.jpg` (not silently picks up the `.png`).
- **Rationale:** Playwright's `page.screenshot(type="jpeg", path=...)` will write whatever extension you give it. A typo `out_dir / f"screenshot-{stem}.png"` would produce a PNG file with `.png` extension, breaking the README's `.jpg` links — but `check_outputs_complete` should fail loudly first.

**CAP-64 — output dir does not exist → raises with clear message**
- **Subject:** missing dir vs missing file.
- **Setup:** `nonexistent = tmp_path / "no-such-dir"`.
- **Trigger:** `check_outputs_complete(nonexistent, PAGE_CAPTURE_SPECS)`.
- **Assert:** raises `FileNotFoundError` whose message names the *directory* (not one of the 6 files); the user-facing message reads like "output directory does not exist: <path>", **not** a stack-trace-style `[Errno 2] No such file or directory: '.../screenshot-overview.jpg'`.
- **Rationale:** the user flagged this exact UX. Without the explicit branch, the user sees 6 confusing per-file errors instead of "you pointed `--out` at nothing".

---

### Helper group I — CLI (`parse_args` / `main`) (CAP-70..74)

**CAP-70 — `--help` exits 0 and mentions all 3 subcommands**
- **Subject:** `main(["--help"])` or `parse_args(["--help"])`.
- **Setup:** capture stdout/stderr.
- **Trigger:** call.
- **Assert:** raises `SystemExit(0)`; captured stdout contains `screenshots`, `gif`, and `all` as subcommand keywords.
- **Rationale:** Plan's CLI tests cover happy/unknown but never `--help`. Documentation-level invariant; cheap.

**CAP-71 — bad `--port` (non-int, negative, >65535) exits non-zero with clear message**
- **Subject:** `parse_args(["screenshots", "--port", "abc"])`, `..., "-1"`, `..., "70000"`.
- **Setup:** capture stderr.
- **Trigger:** call.
- **Assert:** raises `SystemExit` with non-zero code; stderr contains the literal `--port`; for `-1` and `70000` cases the message names "port range" or similar (uncertain — Decision Gate item: do we want range validation in `parse_args` or only inside `main`? Recommend `parse_args` via `type=` callable for fail-fast).
- **Rationale:** Plan tests "unknown command" but not invalid port values, which are the more common typo.

**CAP-72 — `--out` pointing at a file (not a dir) raises with clear message**
- **Subject:** target type validation.
- **Setup:** create a file at `tmp_path / "demo.gif"`; call `main(["screenshots", "--db", str(valid_db), "--out", str(tmp_path / "demo.gif")])`.
- **Trigger:** call.
- **Assert:** exits non-zero before launching Streamlit (no subprocess spawn); stderr contains `--out` and the word "directory" (or similar guidance).
- **Rationale:** common operator typo. Without this check, Playwright would write `<out_dir>/screenshot-overview.jpg` where `<out_dir>` is a file → confusing `NotADirectoryError` deep in the stack.

**CAP-73 — `gif` subcommand without pre-existing screenshots raises with clear message**
- **Subject:** `main(["gif", "--out", str(empty_tmp_path)])`.
- **Setup:** `empty_tmp_path` exists but contains no `screenshot-*.jpg`.
- **Trigger:** call.
- **Assert:** exits non-zero; stderr names at least one of the missing `screenshot-<stem>.jpg` files; does NOT launch Streamlit or Chromium (verifiable via spy on `subprocess.Popen` or `playwright.sync_api.sync_playwright`).
- **Rationale:** the user flagged this. `gif` is the "stitch from existing files" mode; running it cold should fail with a recipe ("run `screenshots` first or use `all`"), not crash inside Pillow.

**CAP-74 — `main()` exits non-zero with diagnostic when `--db` does not exist (Plan Step 8)**
- **Subject:** Plan-listed. Add: assert the diagnostic mentions both the literal path and the `parser` CLI as the fix.
- **Setup:** `main(["all", "--db", "/no/such/file.duckdb"])`.
- **Trigger:** call.
- **Assert:** exits non-zero; stderr contains `/no/such/file.duckdb` AND one of `parser` / `build-portfolio-data.sh` / `generator`.
- **Rationale:** Plan asserts "diagnostic naming `--db`" but UX is better if it points at the fix. Cheap upgrade.

---

### Helper group J — Approval-gated dep behavior (CAP-80..81)

**CAP-80 — `playwright install chromium` recipe surfaced if browser binary missing**
- **Subject:** capture script behavior when `playwright` is installed but Chromium browser is not.
- **Setup:** monkeypatch `playwright.sync_api.sync_playwright().__enter__().chromium.launch` to raise `playwright._impl._api_types.Error("Executable doesn't exist at /.../chrome ...")`. (Real error shape from Playwright source.)
- **Trigger:** `main(["all", "--db", str(valid_db), "--out", str(tmp_out)])`.
- **Assert:** exits non-zero; stderr contains the literal `playwright install chromium` (the fix recipe), not the 500-line raw Playwright stack.
- **Rationale:** **High-value UX.** The user flagged this. First-time setup pain. Without the catch, a fresh clone gives a wall of red — with it, the operator copies one command and moves on.

**CAP-81 — `pyproject.toml` declares `playwright>=1.49` in dev group**
- **Subject:** file-level invariant.
- **Setup:** parse `pyproject.toml` (already in tree).
- **Trigger:** read `[dependency-groups].dev` list.
- **Assert:** at least one entry matches regex `^playwright(\[.*\])?>=1\.49`; lockfile has playwright pinned (check `uv.lock` for `name = "playwright"`).
- **Rationale:** prevents a contributor from removing the dep from `pyproject.toml` while the test suite still runs because their local `.venv` has it cached. Catches "works on my machine".

---

### Helper group K — End-to-end (env-gated) (CAP-90..95)

> All gated on `CAPTURE_RUN_PLAYWRIGHT=1`. Skip marker on import-time env check, same pattern as `tests/test_rag/test_eval.py`.

**CAP-90 — all 6 JPGs produced, each ≥ 50 KB**
- **Subject:** Plan Step 10 happy path.
- **Setup:** `ui_db_path` fixture (see §4); `tmp_out = tmp_path / "out"`.
- **Trigger:** `main(["all", "--db", db_path, "--out", str(tmp_out), "--port", str(pick_free_port())])`.
- **Assert:** exit code 0; for each `(_, stem)` in `PAGE_CAPTURE_SPECS`, `(tmp_out / f"screenshot-{stem}.jpg").stat().st_size >= 50_000`.
- **Rationale:** Plan-listed; restated with concrete numbers.

**CAP-91 — `demo.gif` valid GIF89a and < 2 MB**
- **Subject:** brief G3.
- **Trigger:** same run as CAP-90.
- **Assert:** `(tmp_out / "demo.gif").exists()`; first 6 bytes == `b"GIF89a"`; `stat().st_size < 2_000_000`; `Image.open(out).is_animated == True`; frame count == 6.
- **Rationale:** explicit numeric guard; Plan only says "valid GIF89a".

**CAP-92 — no orphan Streamlit / Chromium processes after teardown**
- **Subject:** subprocess cleanup.
- **Setup:** record `psutil.process_iter()` names before the run; run; record names again 2 s after `main()` returns.
- **Trigger:** same run.
- **Assert:** no new processes whose `name()` matches `streamlit`, `chromium`, `headless_shell`, `chrome` survive past the wait.
- **Rationale:** **High-value, Windows-critical.** The Plan's risk register flags this (Risk row "Streamlit subprocess doesn't terminate cleanly on Windows") but doesn't pin a test. Without this, a flaky teardown silently bleeds capacity across runs. Note: adds `psutil` as a test-only import; check it's already available (it's commonly pulled in transitively, but uncertain — Decision Gate item if needed).

**CAP-93 — missing DB exits non-zero *before* launching Streamlit**
- **Subject:** fast-fail.
- **Setup:** spy on `subprocess.Popen` via `unittest.mock.patch`.
- **Trigger:** `main(["all", "--db", "/no/such.duckdb", "--out", str(tmp_out)])`.
- **Assert:** exit code != 0; `Popen` was never called.
- **Rationale:** sanity-checks Plan Step 8's missing-DB validation actually runs before subprocess launch. Catches a future refactor that moves validation into the orchestration body.

**CAP-94 — `--port None` picks a free port automatically**
- **Subject:** default-port flow.
- **Setup:** patch `pick_free_port` to return a known free port; run capture.
- **Trigger:** `main(["all", "--db", db_path, "--out", str(tmp_out)])` (no `--port` flag).
- **Assert:** the patched `pick_free_port` was called exactly once; the Streamlit subprocess's argv contains `--server.port <that_port>`.
- **Rationale:** Plan claims this in the Goal Contract but never asserts it. Catches a refactor that hard-codes `8501`.

**CAP-95 — Co-Pilot screenshot actually contains the canned answer text**
- **Subject:** visual-level invariant, the only one that proves the monkeypatch reached the running Streamlit.
- **Setup:** after capture, drive a *second* Playwright session against the *same* live Streamlit (or capture page text mid-run via `page.text_content("body")`) for the Co-Pilot page. Alternatively use Pillow + Tesseract to OCR the screenshot — uncertain → Decision Gate item.
- **Trigger:** assert the rendered page (or its screenshot via OCR) contains a substring of `build_canned_answer("q").answer_text` (e.g., the word "tombstoning").
- **Assert:** the substring is present.
- **Rationale:** **Highest-value end-to-end test.** Without it, every prior test could be green and the actual Co-Pilot screenshot could still show a refusal, a stale state, or a blank chat — because the monkeypatch didn't survive subprocess launch. Recommend the Playwright-text approach (no OCR dep): use `page.locator("[data-testid='stChatMessage']").inner_text()` instead of screenshot-byte introspection.

---

## 3. Coverage gaps (deliberately NOT testing)

| Behavior | Rationale |
|---|---|
| Visual-diff regression (perceptual-hash JPG-to-JPG across runs) | Couples to font rendering, OS-level subpixel AA, Chromium version. Flaky in CI; high-noise low-signal. Brief G6 explicitly accepts byte-different equivalents. |
| Co-Pilot integration with live Gemini | Phase 3 `RAG_RUN_LLM_EVAL=1` eval already covers it (`tests/test_rag/test_eval.py`). |
| GitHub Actions workflow integration | Out of scope per brief §6 (separate Phase 4 deliverable). |
| Repeated-capture race conditions (two `main()` calls concurrently) | Single-user dev workflow; CAP-51 covers the port-collision angle. Full concurrency hardening is over-spec. |
| Cross-platform screenshot byte-identity (Linux vs Windows vs macOS) | Chromium renders differently per OS font-hinting. Brief gates on dimensions + size + valid header, which is OS-portable. |
| Streamlit version drift (1.45 → 1.58 → next) | Out of scope; the existing UI test suite catches Streamlit API breaks. |
| Cookie / localStorage state across captures | Each capture launches a fresh headless browser; no persistence. |
| Capture-script HTML/CSS regression of the Streamlit dashboard | The dashboard's own visual smoke is covered by `tests/test_ui/`. Capture script is downstream of that. |
| README markdown render correctness | GitHub renders relative paths reliably; brief G5 makes this a manual post-PR check, not a unit test. |

---

## 4. Test fixture additions needed

| Fixture | Status | Plan |
|---|---|---|
| `ui_db_path` — populated tmp DuckDB | **Already exists** at `tests/test_ui/conftest.py:260`. Session-scoped. | **Lift to `tests/conftest.py`** so `tests/test_scripts/test_capture_real.py` can depend on it without cross-package import. (No code change to current callers — pytest discovers root-`conftest.py` fixtures everywhere.) Uncertain → Decision Gate item: lift vs. duplicate vs. parametrize. Recommend **lift**. |
| `_strip_llm_env` autouse | Already in `tests/test_ui/conftest.py:31`. | **Mirror in `tests/test_scripts/conftest.py`** as autouse, so no capture-script test ever sees a real `GOOGLE_API_KEY`. Important for CAP-90..95: even though the shim monkeypatches `answer_question`, defense-in-depth. |
| `playwright_browser` | New | Optional: a session-scoped `sync_playwright()` context that yields a `Browser` for tests that drive Playwright directly (not the capture script). For slice 2 only CAP-95 might use this. Recommend **defer** — instantiate inline in the one test that needs it; saves the fixture-import cost on every `tests/` collection. |
| `psutil_baseline` | New (CAP-92 only) | Captures pre-run process names. Tiny; define inline in CAP-92. |
| `fake_playwright_chromium_missing` | New (CAP-80) | Monkeypatch helper that makes `chromium.launch` raise the "Executable doesn't exist" error. Define inline; don't promote to fixture. |

---

## 5. Anti-redundancy check (vs existing tests)

| New test | Closest existing | Why not duplicate |
|---|---|---|
| CAP-10..15 (`build_canned_answer`) | `tests/test_ui/test_chat_smoke.py::test_chat03..09` (use `_grounded` stub) | Existing tests use a *test-local* stub inline; CAP-10..15 test the **production-shipped** helper in `scripts/capture_screenshots.py` that the *capture script* monkeypatches in. Different file, different lifetime, different drift surface. |
| CAP-20..23 (shim) | None | Shim is new in slice 2. |
| CAP-30..36 (gif assembler) | None | First gif assembler in the repo. |
| CAP-40..43 (page specs) | None | First nav-label/filename mapping in the repo. CAP-43 (AST-of-`app.py`) is novel — no existing test introspects `st.Page` titles. |
| CAP-50..53 (port picker) | None | First port-picker in the repo. |
| CAP-60..64 (output detector) | None | First post-capture validator in the repo. |
| CAP-70..74 (CLI) | `tests/test_parser/test_cli.py`, `tests/test_generator/test_cli.py` | Each is scoped to its own CLI's arg shape. CAP-7x exercises the slice-2 CLI surface; zero overlap. |
| CAP-80..81 (dep) | None | First dep-floor pin in tests. |
| CAP-90..95 (env-gated end-to-end) | `tests/test_rag/test_eval.py::test_eval_live_llm_8_of_10` (`RAG_RUN_LLM_EVAL=1`) | Same gating pattern, different subject (capture pipeline vs LLM eval). No overlap. |

No proposed test duplicates an existing assertion.

---

## 6. Summary table for parent (Step 6 Decision Gate inputs)

| Uncertainty surfaced here | Plan section it touches | Recommended resolution |
|---|---|---|
| CAP-12 strong vs weak citation-existence test | Plan Step 2 | Strong (test chunk index against `kb_loader` output) |
| CAP-30 frame-size mismatch: raise or normalize | Plan Step 4 | Raise (option A) |
| CAP-32 one-frame input: valid 1-frame gif or raise | Plan Step 4 | Valid 1-frame gif |
| CAP-33 missing parent dir: auto-create or raise | Plan Step 4 | Auto-create |
| CAP-34 (4K frame) marked `@slow` or always-run | Plan Step 4 | Always-run with `@pytest.mark.timeout(30)`; bail to `@slow` only if CI exceeds 5 s |
| CAP-71 `--port` range validation: in `parse_args` or in `main` | Plan Step 8 | `parse_args` via `type=` callable (fail-fast) |
| CAP-92 add `psutil` dev dep or skip CAP-92 if unavailable | Plan Step 10 | Skip-if-unavailable (no new dep ask in slice 2) |
| CAP-95 OCR vs Playwright-text for canned-answer verification | Plan Step 10 | Playwright `inner_text()` (no OCR dep) |
| Fixture: lift `ui_db_path` to root conftest, duplicate, or parametrize | Plan §F-table | Lift to `tests/conftest.py` |

Eight decisions for Step 6 owner sync; all are recommend-and-confirm, none are show-stoppers.
