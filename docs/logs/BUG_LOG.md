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

## [BUG-001] Web-research subagent cached proprietary Keysight PDF + Virinco LGPL source in `.cache_research/` (P1) — OPEN

**Discovered:** 2026-06-13
**Phase:** Phase 1a — Step 2 (Explore)
**File(s):** `.cache_research/LogRecordFormat.pdf`, `.cache_research/LogRecordFormat.txt`, `.cache_research/Importer.cs`, `.cache_research/UnitMapper.cs`, `.cache_research/README.md`
**Symptom:** Step 2's external-research subagent (general-purpose, web-enabled) downloaded the Keysight "i3070 Log Record Format" PDF and its extracted text, plus three files from the Virinco WATS-Client-Converter repo (LGPL-3.0), into a working `.cache_research/` directory at the repo root. None of these files were in `.gitignore` at the time; a `git add .` could have committed proprietary Keysight content into the repo, violating CLAUDE.md hard guardrail #3 ("No proprietary Keysight documentation copied wholesale").
**Root Cause:** The subagent was instructed to do public-sources research with citations. It correctly fetched material to read it, but persisted the raw downloads at the repo root instead of in `~/.cache/` or `%TEMP%`. The guardrail was not part of its charter.
**Fix (in-session, immediate):** (a) Added `.cache_research/` to `.gitignore` so it cannot enter the repo accidentally; (b) entire directory will be deleted after Step 3 (Plan) consumes the information; (c) future Explore-style external-research charters must include "do not persist downloaded source material at the repo root — use `%TEMP%` and write a citation-only report."
**Verification:** `git check-ignore .cache_research/LogRecordFormat.pdf` returns the file as ignored; `.cache_research/` deleted at end of session and absence verified before commit at Step 8.
**Time to resolve:** ~5 min (gitignore + BUG_LOG entry); cleanup deferred to Step 8.

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
