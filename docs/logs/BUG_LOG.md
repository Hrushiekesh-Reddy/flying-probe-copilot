# Bug Log — Flying-Probe Co-Pilot

Bugs that took >5 minutes to diagnose or resolve are logged here.
Add an entry here AND reference it from `SESSION_LOG.md` on the day it was found.

Severity:
- **P0** — Blocks all work. Must fix before anything else.
- **P1** — Important. Workaround exists. Fix this sprint.
- **P2** — Minor. Log and defer.

---

## Active / Open

<!-- Add new bugs below this line -->

## [BUG-002] Generator hardcodes 4 test records per board regardless of profile (P0) — RESOLVED 2026-06-13

**Discovered:** 2026-06-13
**Phase:** Phase 1a — Step 9 (Manual QA)
**File(s):** `src/flying_probe_copilot/generator/cli.py:94-142` (`_build_blocks`)
**Symptom:** Generated `.log` files for small/medium/large board profiles are all ~410 bytes. Each panel has exactly 4 test records: `shorts`, `R12` (A-RES), `D1` (A-DIO), `U7` (D-T) — the same 4 every time, regardless of `--board-profile`. CSV inspection (Test 8 of manual QA) confirmed: 4 rows per panel × N panels, identical component identifiers. Spec lines 100-104 require small=~120 tests, medium=~450 tests, large=~1600 tests per board.
**Root Cause:** `_build_blocks` docstring says "Build the representative four-block test set for one board." The function hardcodes the 4-block list as a representative sample, never expanding to use `profile.component_count` or `profile.component_mix`. Manual QA caught this; automated tests did NOT because (a) `test_profiles` validates profile DEFINITIONS only, not output scale; (b) `test_lexical_compliance` only checks lexical validity; (c) CLI tests only assert file presence and YAML round-trip, not realistic content scale.
**Fix:** Replace `_build_blocks(outcome)` with `generate_blocks(profile, outcome, seed)` that (a) uses `profile.component_count` to size the block count, (b) apportions blocks across component types per `profile.component_mix`, (c) generates realistic refdes (R1..R80, C1..C40, U1..U12, etc.), (d) maps component-type prefixes to record types (R→A-RES, C→A-CAP, L→A-IND, D→A-DIO, Q→A-NPN, U→D-T), (e) randomizes the component that fails (not always R12), and (f) keeps one shorts test as the first block per panel. Add tests asserting per-panel block count matches profile within ±10%, type mix matches `component_mix` within ±10%, refdes diversity, and failure can occur on any component family.
**Verification:** Manual QA Test 5 reruns produce small/medium/large with file sizes scaling ~5KB / 20KB / 80KB. Automated `test_panel_block_count_scales_with_profile` and `test_panel_block_mix_matches_profile_component_mix` pass.
**Time to resolve:** in progress (estimated 45-60 min, this session).

## [BUG-003] `available_profiles()` returns sorted-set order ('large, medium, small') not size order (P3) — RESOLVED 2026-06-13

**Discovered:** 2026-06-13
**Phase:** Phase 1a — Step 9 (Manual QA)
**File(s):** `src/flying_probe_copilot/generator/profiles.py`
**Symptom:** CLI error for unknown profile reads "valid: large, medium, small" — alphabetical, not the size-ascending order the spec implies and the docs everywhere quote ("small | medium | large").
**Root Cause:** Likely `set(...)` or `sorted(...)` returns alphabetical.
**Fix:** Return the list in size-ascending order explicitly.
**Verification:** `test_available_profiles_returns_size_ascending_order` passes; manual QA Test 6 shows ordered list.
**Time to resolve:** in progress (estimated 5 min, this session).

## [BUG-001] Web-research subagent cached proprietary Keysight PDF + Virinco LGPL source in `.cache_research/` (P1) — RESOLVED 2026-06-13

**Discovered:** 2026-06-13
**Phase:** Phase 1a — Step 2 (Explore)
**File(s):** `.cache_research/LogRecordFormat.pdf`, `.cache_research/LogRecordFormat.txt`, `.cache_research/Importer.cs`, `.cache_research/UnitMapper.cs`, `.cache_research/README.md`, plus stray `flying-probe-copilot.cache_researchImporter.cs` (malformed path concatenation)
**Symptom:** Step 2's external-research subagent (general-purpose, web-enabled) downloaded the Keysight "i3070 Log Record Format" PDF and its extracted text, plus three files from the Virinco WATS-Client-Converter repo (LGPL-3.0), into a working `.cache_research/` directory at the repo root. A separate `flying-probe-copilot.cache_researchImporter.cs` artifact also appeared, evidence of a path-concatenation bug in the subagent's file-saving code. None of these files were in `.gitignore` at the time; a `git add .` could have committed proprietary Keysight content into the repo, violating CLAUDE.md hard guardrail #3 ("No proprietary Keysight documentation copied wholesale").
**Root Cause:** The subagent was instructed to do public-sources research with citations. It correctly fetched material to read it, but persisted the raw downloads at the repo root instead of in `~/.cache/` or `%TEMP%`. The guardrail was not part of its charter. The stray artifact additionally indicates the subagent built file paths by string-concatenating "<project-name>" + ".cache_research" + "<filename>" instead of a platform-correct path join.
**Fix:**
  In-session (2026-06-13):
    (a) Added `.cache_research/` to `.gitignore`;
    (b) deleted `.cache_research/` and the stray `flying-probe-copilot.cache_researchImporter.cs` artifact;
    (c) noted the issue in DECISION_LOG.
  Process improvement (2026-06-13, this entry's resolution):
    (d) Added an "External Research / Web Download Policy" block to the Explorer charter in `.claude/skills/session-workflow/SKILL.md` (Step 2) requiring `%TEMP%\agent-research\<session>\` (Win) or `~/.cache/agent-research/<session>/` (Unix) for any caching, citation-only reports, no copying of LGPL/GPL/proprietary source, mandatory cleanup with a `Cleanup:` line in the report, and an explicit STOP-on-bad-path rule that catches the path-concatenation bug pattern.
    (e) Added a matching charter block to `.claude/skills/deep-research/SKILL.md` Step 2 ("Charter for every fan-out search agent") and reinforced in the Research quality rules.
    (f) Added a one-line summary to `.claude/rules/session-workflow.md` Hard rules.
    (g) Added matching rows to the Subagent charter summary table.
    (h) Source of truth for these edits is `E:\hrk-agent-starter\` (the portable kit) — all three files updated there and propagated here, so future stamps of new projects inherit the policy automatically.
**Verification:**
  - `.cache_research/` and stray artifact removed from working tree (in-session, 2026-06-13).
  - `.cache_research/` present in `.gitignore`: verified.
  - Charter updated in both `E:\hrk-agent-starter\` (source of truth) and `E:\flying-probe-copilot\` (this project), files:
    `.claude\skills\session-workflow\SKILL.md` (Step 2 + summary table),
    `.claude\skills\deep-research\SKILL.md` (Step 2 + quality rules),
    `.claude\rules\session-workflow.md` (Hard rules).
  - Behavioural verification deferred to next external-research session: confirm the spawned subagent (i) writes only to `%TEMP%\agent-research\<session>\`, (ii) returns a `Cleanup:` line, (iii) the post-session `git status` shows no new files under the repo root and no path-mangled artifacts.
**Time to resolve:** ~5 min (in-session mitigation, 2026-06-13) + ~30 min (process improvement: charter language drafted, applied to starter + project, 2026-06-13).

---

## Resolved

<!-- Move bugs here when fixed. Include resolution date and verification note. -->

---

## Template

```
## [BUG-XXX] Short title (P0 / P1 / P2) — OPEN | RESOLVED YYYY-MM-DD

**Discovered:** YYYY-MM-DD
**Phase:** Phase X — name
**File(s):** `src/flying_probe_copilot/...`
**Symptom:** What you saw or what failed.
**Root Cause:** Why it happened.
**Fix:** What was changed to resolve it.
**Verification:** How you confirmed the fix (test name, manual check, etc.)
**Time to resolve:** X min / X hr
```
