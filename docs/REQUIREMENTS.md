# REQUIREMENTS.md

This document is an index. The full content lives in two companion files (provided separately, drop them into this `docs/` folder):

- **`SKILLS.md`** — Personal skill gaps and ramp-up plan for the owner. Tiered by domain / engineering / data / RAG / UI / deployment.
- **`RESOURCES.md`** — Hardware, software, services, data strategy, time, and money budget.

## Quick summary (the headline numbers)

### Skills
- ✅ All Tier-1 domain skills (flying probe, IPC, SMT, SPC) already present — your moat.
- 🟡 ~3-4 days of brush-up across regex, pandas, anomaly stats, Plotly, Docker.
- 🔴 ~1.5 weeks of new learning across pytest, DuckDB API, structured LLM output, embeddings, ChromaDB, BM25, Streamlit.
- **Total skill ramp: ~2 weeks, interleaved with the 8-week build.**

### Resources
- Hardware: ✅ Sufficient (16-32 GB RAM, GTX/RTX) — no local LLM needed.
- Software: $0 (entire stack open-source).
- LLM API: Google Gemini (already paid via portfolio account, free tier generous).
- Backup LLM: Anthropic API (~$20-60 across whole build if needed).
- Data: Synthetic-first; real-data validation only on work network.
- Time: ~70-90 hours total over 8-10 calendar weeks.
- **Total out-of-pocket cost: ~$0-30.**

## Confirmed decisions

| Question | Answer |
|---|---|
| Hardware sufficient? | ✅ Yes |
| Run LLM locally? | ❌ No — use Gemini API |
| API budget | Gemini free tier first; Claude API as backup |
| Real data accessible? | Only on work network; never copied home |
| Log format target | HP3070 / Keysight i3070 |
| Database | DuckDB |

## Verification checklist (Phase 0 exit)

- [ ] Owner has read both SKILLS.md and RESOURCES.md and signed off on the plan
- [ ] Google AI Studio key obtained and stored in `.env`
- [ ] Python 3.11+, `uv`, Git installed
- [ ] Repo created on GitHub (private until Phase 4)
- [ ] Keysight i3070 BT-Basic and Test Methods manual PDFs downloaded (kept locally; never committed)
- [ ] Bookmarks saved for the 3 reference RAG repos
- [ ] Workspace path on E:\ confirmed (`E:\flying-probe-copilot\`)

Once all boxes are checked, Phase 1a (synthetic log generator) is unblocked.
