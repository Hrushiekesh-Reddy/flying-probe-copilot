# Decision Gate — Phase 4 Slice 2: Headless Screenshot Capture + Demo GIF

**Date:** 2026-06-21
**Author:** parent (Step 6, not delegated)
**Inputs:** `brief.md`, `plan.md`, `plan-rev1.md`, `test-plan.md`, `redteam.md`
**Status:** awaiting owner sign-off

---

## 1. Decision Index (single-line list)

| # | Decision | Recommended | Owner ratifies? |
|---|---|---|---|
| **D1** | Scope = script + demo gif (no GH Actions) | ✓ ratified at brief time | (re-confirm) |
| **D2** | Co-Pilot capture = stub `answer_question` | ✓ ratified at brief time | (re-confirm) |
| **D3** | Headless tool = Playwright | ✓ ratified at brief time | (re-confirm) |
| **D4** | Capture script location = `scripts/capture_screenshots.py` (not in `src/`) | Recommended | needs sign-off |
| **D5** | Gif lib = Pillow (already locked) | Recommended | needs sign-off |
| **D6** | Sample-DB strategy = abort with friendly message if missing; pre-flight builds it in Step 0 | Recommended | needs sign-off |
| **D7** | Co-Pilot question shown = "what causes tombstoning?" | Recommended | needs sign-off |
| **D8** | Gif placement in README = above hero strip, after intro | Recommended | needs sign-off |
| **D9** | Replace slice-1 JPGs with auto-captured ones (yes) | Recommended | needs sign-off |
| **D10** | Gif frame duration = 2000 ms (12 s total) | Recommended | needs sign-off |
| **D11** | Keep env-gated end-to-end test (`CAPTURE_RUN_PLAYWRIGHT=1`) | Recommended | needs sign-off |
| **D12** | Branch name = `feature/phase4-slice2-screenshots` | Recommended | needs sign-off |
| **MD-1** | Gif resolution + size budget = 1280×800 Pillow defaults, < 5 MB | Recommended | needs sign-off |
| **MD-2** | Case-study line = **footnote-resolve** (not strike) | Recommended | needs sign-off |
| **MD-3** | `ui_db_path` fixture = **lift** to `tests/conftest.py` | Recommended | needs sign-off |
| **MD-4** | JPG capture quality = `quality=95` | Recommended | needs sign-off |
| **MD-5** | `pyproject.toml` edits (playwright dep + pytest.pythonpath) = **single bundled approval** | Recommended | needs sign-off |
| **MD-6** | Canned Co-Pilot answer text = parent-drafted (471 chars; see §4 MD-6 below) | Recommended | needs sign-off |
| **BLOCKER closures** | All 5 red-team BLOCKERs (B-1..B-5) closed per Plan-Rev1 deltas | Recommended | needs sign-off (any objection?) |
| **Approval-gated edits** | `pyproject.toml` (×2 lines), `README.md` (1 line), `tests/test_ui/test_chat_smoke.py` (declared parallel `#0`→`#3`) | Recommended | needs sign-off (per agent-conduct.md gated-files rule) |

---

## 2. Coverage check

Plan-Rev1 deltas have these guardrails verified:

| Guardrail | Status |
|---|---|
| `src/flying_probe_copilot/**` untouched | ✓ (B-2 fix uses Playwright click, not `chat.py` edit) |
| `.claude/**` untouched | ✓ |
| `.gitignore` / `.env.example` untouched | ✓ |
| `migrations/` untouched | ✓ |
| Real customer data zero-touch | ✓ (synthetic DB only) |
| Keysight / IPC verbatim zero-touch | ✓ (capture artifacts are dashboard UI only) |
| API keys zero-touch | ✓ (capture works with `GOOGLE_API_KEY` unset) |
| TDD discipline | ✓ (every Plan step has named RED test) |
| Out-of-scope chips tracked | ✓ (7 items in Brief §6 + 3 from red-team) |
| Decision Gate covers every approval-gated edit | ✓ (pyproject ×2, README ×1, test fixture parallel ×1) |

---

## 3. Per-decision detail

### D1–D3 — Re-confirmation only

Owner ratified at brief time. No new info changes the recommendation.

### D4 — Capture-script location

- **(a) `scripts/capture_screenshots.py` standalone** — matches existing `scripts/build-portfolio-data.sh` convention. NOT exposed as a `[project.scripts]` entry-point. Invoked via `python scripts/capture_screenshots.py ...` (or `uv run python scripts/capture_screenshots.py ...`).
- **(b) `src/flying_probe_copilot/screenshots/cli.py:main` + new `[project.scripts] screenshots = ...` entry** — capture becomes an installed CLI alongside `generator`/`parser`. Bigger surface; couples a dev-tool to the runtime package.
- **Recommend (a)** — capture infra isn't a runtime feature of the package. Keeps `[project.scripts]` user-facing only.

### D5 — Gif library

- **(a) Pillow** — already locked at 12.2.0 via streamlit's transitive deps. Zero new approval-gated dep. `Image.save(save_all=True, append_images=[...], duration=2000, loop=0, optimize=True)`. Output may be 2–5 MB.
- **(b) imageio[ffmpeg]** — new dep. Smaller gif via palette quantization. ~5 MB ffmpeg binary install.
- **Recommend (a)** — slice-2 already has 1 approval-gated dep (playwright). Adding a second for marginally-smaller gif is poor cost/value. Future chip can swap if README load becomes slow.

### D6 — Sample-DB strategy

- **(a) Abort if missing** with `bash scripts/build-portfolio-data.sh` recipe in the diagnostic message; Step 0 pre-flight runs the bash script if needed.
- **(b) Auto-run** the bash script from capture_screenshots.py on missing DB.
- **(c) Build a tiny in-memory DB** inside the capture script.
- **Recommend (a)** — (b) couples capture to a 3-min batch generation the owner may not want; (c) loses the realistic 6-month data visible in the README hero strip.

### D7 — Co-Pilot question shown in screenshot

- **(a) "what causes tombstoning?"** — recently fixed by BUG-014; directly visualizes the engineering story; uses the canned `failure-modes/tombstoning.md#3` citation.
- **(b) "why am I seeing a yield drop on board v2?"** — broader question; would require a different canned answer; no existing case-study tie.
- **(c) Something else owner picks** — open.
- **Recommend (a)** — story-rich choice; matches case-study's tombstoning engineering-story.

### D8 — Gif placement in README

- **(a) Above hero strip, after intro paragraph** — recruiters see motion first, stills below for detail. Insert at `README.md:14` (between the intro and the hero-strip markdown table at line 16).
- **(b) Below hero strip** — stills first, then animation.
- **(c) New section between Quickstart and Architecture** — gif as a "demo" subsection.
- **Recommend (a)** — highest-impact placement for recruiter scan; gif is more attention-grabbing than static strip.

### D9 — Replace slice-1 JPGs with auto-captured ones

- **(a) Yes — replace all 6** — slice-2's whole point is "auto-recapture replaces manual". Hand-captured JPGs become a one-moment artifact; auto-captured ones are reproducible.
- **(b) Keep slice-1 JPGs, only commit the new gif** — saves the slice-1 dimension baselines.
- **Recommend (a)** — keeping slice-1 baselines undermines the next change's diff.

### D10 — Gif frame duration

- **(a) 2000 ms/frame, 12 s total** — slow enough to read each page's KPI numbers; fast enough that attention holds.
- **(b) 1500 ms/frame, 9 s total** — snappier; KPI numbers harder to read.
- **(c) 3000 ms/frame, 18 s total** — generous reading time; risks attention drop-off.
- **Recommend (a)** — CLI flag makes it overridable for future tweaks.

### D11 — Keep env-gated end-to-end test

- **(a) Keep gated** (`CAPTURE_RUN_PLAYWRIGHT=1`, default-skipped). Cheap; self-documenting recipe for "how do I prove the script works"; matches slice-1 `RAG_RUN_LLM_EVAL` pattern.
- **(b) Omit until CI lands** — fewer files; loses the recipe.
- **Recommend (a)**.

### D12 — Branch name

- **(a) `feature/phase4-slice2-screenshots`** — specific; "screenshots" is the user-facing artifact.
- **(b) `feature/phase4-slice2-demo-capture`** — emphasizes the verb.
- **Recommend (a)**.

### MD-1 — Gif resolution + size budget

- **(a) 1280×800 Pillow defaults, < 5 MB actual** (recommended) — verifiable post-capture; GitHub README image limit is 10 MB.
- **(b) 1024×640 Pillow optimized, ~1.5–3 MB** — smaller; README loads faster; chart-text harder to read.
- **(c) 1280×800 + imageio palette quantization, ~1 MB** — requires new dep (overrides D5).
- **Recommend (a)** — ship the bigger gif now; verify GitHub render in slice 2 itself; future chip can swap.

### MD-2 — Case-study "Slice 1.5 candidate" line — strike vs footnote-resolve

- **(a) Strike** — delete the sentence; retrospective loses one of three items.
- **(b) Footnote-resolve** (recommended) — append `*[Resolved 2026-06-21 — slice 2 shipped automated capture; see [`docs/plans/2026-06-21-phase4-slice2-brief.md`](plans/2026-06-21-phase4-slice2-brief.md).]*` to the sentence at `docs/case-study.md:123`. Preserves retrospective candor + adds receipt.
- **Recommend (b)**.

### MD-3 — `ui_db_path` fixture lift vs duplicate

- **(a) Lift** to `tests/conftest.py` (recommended) — single source of truth; test-UI tests already use it by name, so no caller change. Session-scope semantics unchanged.
- **(b) Duplicate** into `tests/test_scripts/conftest.py` — copies 220 lines; risks drift.
- **Recommend (a)**.

### MD-4 — JPG capture quality

- **(a) `type="jpeg", quality=90`** — Plan default; small bytes; visible JPEG noise on text.
- **(b) `type="jpeg", quality=95`** (recommended) — ~15% larger; cleaner text; visually-equivalent-or-better than slice-1.
- **(c) `type="png"` then Pillow-convert** — best quality; extra step.
- **Recommend (b)**.

### MD-5 — `pyproject.toml` edits bundling

- **(a) Single bundled approval** (recommended) — both edits (playwright dep + `[tool.pytest.ini_options].pythonpath`) are mechanically paired; both required for the slice; one owner sign-off covers both.
- **(b) Two separate approvals** — overhead with no benefit.
- **Recommend (a)**.

### MD-6 — Canned Co-Pilot answer text (parent-drafted, owner can copy-edit)

Recommended verbatim string (471 chars, grounded entirely in `tombstoning.md` §Likely causes + §ICT signature):

```
Likely causes of tombstoning: (1) uneven pad heating during reflow causing
one terminal to wet before the other, (2) pad-design imbalance or unequal
copper thermal mass, (3) excess solder paste on one pad pulling the chip
upright via surface tension. The ICT signature is an open across the two
pads — cross-check against the expected refdes value to distinguish
tombstoning from a wrong or missing part.
```

This is the literal text a recruiter reads in the README's demo gif and Co-Pilot screenshot. Public-facing; owner has veto / copy-edit prerogative.

### BLOCKER closures — re-confirm

Plan-Rev1 §Summary closes B-1..B-5. Owner objection welcome on any.

### Approval-gated edits — re-confirm

Per `.claude/rules/agent-conduct.md`, the gated files are: `pyproject.toml`, `db/schema.py`, `migrations/`, `.claude/settings.json`, `.env.example`. This slice touches:
- **`pyproject.toml`** (×2 edits, bundled per MD-5): `playwright>=1.49` in dev group + `pythonpath = [".", "src"]` in `[tool.pytest.ini_options]`
- **No other gated files**

Approval-gated by `agent-conduct.md` "Code changes" section but worth re-confirming:
- **`README.md`** (1 line insert): `![Demo walkthrough](docs/img/demo.gif)` at line 15 (after intro, before hero-strip table)

And a declared **parallel test-fixture edit** (not separately gated; called out for transparency):
- **`tests/test_ui/test_chat_smoke.py:24`** — flip both `failure-modes/tombstoning.md#0` literals → `#3` to match the new canned citation.

---

## 4. What I will NOT do without explicit owner approval

- Push to remote.
- Force-push or reset --hard.
- Edit any `src/flying_probe_copilot/**` file.
- Add a GitHub Actions workflow.
- Vendor Chromium binaries into the repo.
- Auto-run `playwright install chromium` from the capture script's normal path (it surfaces an instructional error instead).
- Touch any file not in the Plan-Rev1 F-table.

---

## 5. Single owner question

The owner is asked **one** approval-shaped question with the recommended answer pre-loaded. If owner says "Yes — proceed with Recommended on all", I move directly to Step 7 Execute. If owner overrides any item, I revise the relevant section of Plan-Rev1 before Execute.

Question: "Phase-4 slice-2 Decision Gate — ratify Recommended on all 18 items above + the 5 BLOCKER closures + the 2 approval-gated pyproject edits + the 1 approval-gated README edit + the declared parallel test-fixture edit? If yes, I proceed to Step 7 Execute on branch `feature/phase4-slice2-screenshots`. If no, name the item you want to change."
