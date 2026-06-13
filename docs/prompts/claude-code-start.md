# Claude Code — Project Startup Prompt

> Paste this at the start of any new Claude Code session for this project.

---

You are working on **flying-probe-copilot**, my flagship AI portfolio project.

**First action:** Read `CLAUDE.md` at the project root in full. Then read whichever phase doc is current (see the Phase table in CLAUDE.md). Confirm you've absorbed both before any other work.

**Project identity** (mirror in your responses if context is unclear):
- Owner: Hrushiekesh, Manufacturing Engineer, 4 yrs PCBA
- Goal: Build a flying-probe / ICT test-log RAG co-pilot as a hireable portfolio piece
- Status: see `CLAUDE.md` → Phase table

**Non-negotiable rules** (also in `docs/GUARDRAILS.md`):
1. No real customer data ever enters this repo or machine
2. No verbatim IPC-A-610 / J-STD-001 / Keysight text
3. No hardcoded API keys; `.env` only
4. One phase at a time
5. Every AI-generated module read line-by-line before commit

**Workflow conventions:**
- Use Context7 MCP for live docs on DuckDB, Streamlit, ChromaDB, sentence-transformers, Gemini SDK
- For exploration spanning >3 queries → spawn an Explore subagent
- For non-trivial implementation → spawn a Plan subagent first
- Default to pipeline subagent execution, not parallel
- Adversarial verification: before acting on a finding, spawn 2-3 skeptic subagents to refute it
- Cross-project findings (from `my-assembly-hub`, `Portfolio`) → surface as `spawn_task` chips, don't silently scope-creep

**For this session:**
1. Tell me the current phase per `CLAUDE.md`
2. List the open items in that phase's deliverables (from `docs/ROADMAP.md`)
3. Ask me which item to tackle, or recommend the next one with reasoning
4. Do not start writing code until I confirm

At end of session:
- Add a session-log line to `CLAUDE.md` ("YYYY-MM-DD — <phase> — <what was done>")
- If you made any architectural call, add an ADR to `docs/DECISIONS.md`
- Summarize remaining work in 3-5 bullets
