# Agent Conduct — Flying-Probe Co-Pilot

> Applies to Claude Code, Cursor, and any AI agent in this repo.
> Read this file at the start of every session before any other action.

---

## Before any work

1. **Read context first — in this order:**
   - `CLAUDE.md` (project identity, current phase, hard guardrails)
   - `docs/ROADMAP.md` (current phase deliverables and exit criteria)
   - `docs/logs/SESSION_LOG.md` (last session: what was done, what's next)
   - `docs/logs/DECISION_LOG.md` (decisions in force that affect your work)

2. **Confirm your phase.** Never work on deliverables from a future phase. Park ideas in `docs/DECISIONS.md`.

3. **Confirm your branch.** Never commit directly to `main` or `dev`. Always use a feature branch (`feature/short-task-name`).

---

## TDD is mandatory

**Write tests before writing implementation. Every time. No exceptions.**

- Red → Green → Refactor. In that order.
- No implementation function is committed without a corresponding test.
- If you find yourself writing a module without a test file, STOP and write the test first.
- Test stubs are acceptable — placeholder assertions that fail are better than no tests.

---

## Critical files — explicit owner sign-off required before editing

| File | Why |
|------|-----|
| `pyproject.toml` | Dependency changes affect the entire environment |
| `src/flying_probe_copilot/db/schema.py` | Schema changes require a migration |
| Any file in `migrations/` | Irreversible once applied |
| `.claude/settings.json` | Changes agent behavior globally |
| `.env.example` | Documents the secret surface — sensitive |

Ask explicitly: "This file is approval-gated. Do I have owner sign-off to edit it?"

---

## Code changes

- Match the style of surrounding code.
- No commented-out code committed.
- No TODO comments without a corresponding `BUG_LOG.md` entry.
- Read every generated file line-by-line before committing.
- One coherent change per commit (don't bundle unrelated changes).

---

## Docs must stay in sync

After any code change, before committing:

- Add an entry to `docs/logs/SESSION_LOG.md`
- Add decisions to `docs/logs/DECISION_LOG.md`
- Add bugs (>5 min to resolve) to `docs/logs/BUG_LOG.md`
- Tick off any completed deliverables in `docs/ROADMAP.md`
- Update `CLAUDE.md` session log line

**Code changes without matching doc updates = incomplete work.**

---

## Git & commit policy

- **Never commit directly to `main` or `dev`.** Feature branches only.
- **Feature PRs target `dev`, never `main` directly.** Promotion to `main` happens via a separate `dev → main` PR at phase boundaries. (The one-time exception during the 2026-06-13 Phase 0 cleanup is logged in `DECISION_LOG.md` and is not the default.)
- **Never force-push** (`--force`, `--force-with-lease`, `-f`).
- **Never `git reset --hard`** without explicit owner approval.
- **Never `git clean -f`** without explicit owner approval.
- **Never delete permanent branches** (`main`, `dev`).
- Auto-commit at session end only — not mid-session checkpoints.
- Pushing is always owner-initiated — never push automatically.

---

## Scope discipline

- Work on one phase per session.
- If you find something out-of-scope worth fixing, surface it via a `spawn_task` chip. Do not fix it silently.
- Out-of-scope changes bloat the blast radius and make review impossible.

---

## Prohibited without explicit owner approval (this session)

- `uv add` / `pip install` of new packages not in `pyproject.toml`
- Adding files outside the current phase's module directory
- Modifying `.gitignore`, `.env.example`, `pyproject.toml`
- Creating or deleting git branches
- Any migration file edit
- Pushing to remote
