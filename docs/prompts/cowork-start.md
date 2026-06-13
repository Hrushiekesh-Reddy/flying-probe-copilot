# Cowork — Project Startup Prompt

> Paste this when starting a Cowork session for this project. Cowork is best used for: planning conversations, doc generation, design review, brainstorming. Heavier code work belongs in Claude Code / Cursor.

---

You are working with me on **flying-probe-copilot** — my flagship AI portfolio project: a PCBA flying-probe / ICT test-log analytics + RAG co-pilot.

**Project context:**
- I'm Hrushiekesh, a Manufacturing Engineer with 4 yrs PCBA experience, based in Dallas
- Target outcome: a hireable portfolio piece that lands a Manufacturing/Process Engineer with AI role
- The repo lives at `E:\flying-probe-copilot\` and on GitHub (private until Phase 4)
- Project status, phase plan, scope, and guardrails are all in the repo's `docs/` folder

**What Cowork is best for here:**
- Conversational design review ("does this schema make sense?")
- Drafting docs (case-study writeups, README polish, blog posts)
- Generating prompts and config files
- Sanity-checking architectural decisions before I cement them
- Job-search / resume / portfolio-presentation work that touches this project

**What Cowork is NOT for here:**
- Long coding sessions (use Cursor or Claude Code instead)
- Multi-file refactors (use Claude Code with subagents)
- Anything requiring direct repo file access for code execution

**Rules that always apply:**
1. No real customer log data in any form — synthetic only
2. No verbatim IPC-A-610 / J-STD-001 / Keysight standards text
3. API keys are never in code; `.env` only
4. One phase at a time; out-of-scope ideas go to the parking lot in `docs/DECISIONS.md`

**For this session:**
Tell me what you'd like help with. If I'm vague, ask one clarifying question before diving in.
