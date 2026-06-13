# Flying-Probe / ICT Test-Log Co-Pilot — RESOURCES Requirements

**Project:** Flagship — Flying Probe / ICT Test-Log Intelligence Co-Pilot
**Owner:** Hrushiekesh Reddy Kanjula
**Purpose:** Everything the project needs to run — hardware, software, services, data, time, and money. Confirms viability against your real constraints.

---

## Confirmed constraints (from your answers)
- ✅ **Hardware:** Windows laptop, 16-32GB RAM, dedicated GTX/RTX GPU
- ✅ **Budget:** Paid Claude/OpenAI API access available
- ⚠️ **Data:** Real flying-probe logs exist but are confidential — **cannot leave work network**
- 🎯 **Log format:** HP3070 / Keysight i3070 (best public docs)
- 🎯 **Database:** DuckDB (file-based, analytics-optimized)

---

## 1. Hardware

| Component | Need | Your situation | Verdict |
|---|---|---|---|
| RAM | 16 GB minimum, 32 GB ideal | 16-32 GB | ✅ Sufficient |
| GPU | Optional; only for local embedding speed | GTX/RTX present | ✅ Bonus speed |
| Disk | ~20 GB for project, venvs, embeddings | Standard SSD assumed | ✅ Fine |
| CPU | Any modern x64 | Modern Windows laptop | ✅ Fine |
| Internet | For Claude/OpenAI API calls | Standard broadband | ✅ Fine |

**Critical conclusion:** **You do NOT need to run an LLM locally.** Your paid API access removes that requirement entirely. The GPU is only used for embedding model inference (sentence-transformers), which is fast on CPU too. **Hardware is a solved problem.**

---

## 2. Software (all free / open-source)

### Core stack
| Tool | Purpose | Cost |
|---|---|---|
| Python 3.11+ | Runtime | Free |
| `uv` package manager | Fast dependency install | Free |
| DuckDB | SQL spine / analytics DB | Free |
| Pandas | Data wrangling | Free |
| Streamlit | Dashboard UI | Free |
| Plotly | Interactive charts | Free |
| Git + GitHub | Version control | Free |
| VS Code or Cursor | IDE (you already use these) | Free / your existing license |

### RAG & LLM integration
| Tool | Purpose | Cost |
|---|---|---|
| `anthropic` Python SDK | Claude API client | Free (lib) |
| `openai` Python SDK | OpenAI API client (backup) | Free (lib) |
| `sentence-transformers` | Generate embeddings locally | Free, runs on your GPU |
| ChromaDB | Vector store (file-based, simple) | Free |
| `rank-bm25` | Lexical search for hybrid RAG | Free |
| `langchain` *(optional)* | RAG orchestration; you can skip and use plain Python | Free |

### Analytics & ML
| Tool | Purpose | Cost |
|---|---|---|
| scikit-learn | Isolation Forest, basic ML | Free |
| `pyspc` *(optional)* | SPC chart helpers | Free |
| pytest | Testing | Free |

### Polish / deployment (Phase 3+)
| Tool | Purpose | Cost |
|---|---|---|
| Docker Desktop | Containerization | Free (personal use) |
| GitHub Actions | CI/CD | Free for public repos |

**Total software cost: $0.**

---

## 3. Services & APIs (the only recurring cost)

| Service | Required? | Estimated monthly cost (dev) |
|---|---|---|
| Claude API (Anthropic) | Yes — primary | $10-30/month during active build; <$5/month after |
| OpenAI API | Optional backup | $0-10/month |
| GitHub | Yes (free tier fine) | $0 |
| Anthropic Console / Workbench | Yes (comes with API) | $0 |
| Hugging Face | Yes — model downloads only | $0 |

**Estimated total API spend across 2-month flagship build: $20-60.**

**Cost-control tactics:**
- Use Claude **Haiku** for cheap iteration during development; switch to **Sonnet** only for final demo prompts.
- Cache RAG queries during development so the same question doesn't bill twice.
- Mock the LLM layer entirely for unit tests.
- Anthropic typically gives $5 free credits to new console users — useful for first experiments.

---

## 4. Data — the critical strategy

This is where your confidentiality constraint shapes everything.

### Two-track data strategy (this becomes a portfolio talking point)

**Track A — Home development (synthetic data):**
- Build a **synthetic HP3070 log generator** (Python script) that produces realistic test reports based on the public BT-Basic / Keysight documentation.
- Configurable parameters: board ID, panel size, component count, fault injection rate, drift over time.
- Outputs: realistic `.log`, `.csv`, or `.txt` files mimicking real i3070 reports.
- **All development, testing, demos, and your GitHub repo use only synthetic data.**

**Track B — Work-network validation (real data, never copied):**
- On your work machine, point the parser at real anonymized logs.
- Verify field extraction, schema accuracy, edge-case handling.
- Capture **only structural metrics** to bring home: "parser handled 12,400 real records with 99.7% field-extraction accuracy."
- **No raw data, board IDs, customer names, or part numbers ever leave the work network.**

### Why this is a feature, not a limitation
EMS hiring managers care deeply about IP protection. A project that demonstrates synthetic-data-first architecture + on-premise validation is *more* hireable than one that requires data exfiltration. Document this dual-track design in your README.

### Public documentation sources for synthetic data realism
| Source | Use |
|---|---|
| Keysight i3070 BT-Basic Programming Manual | Log format reference (free PDF on Keysight site) |
| Keysight i3070 Test Methods Manual | Test types, measurement conventions |
| Industry papers on ICT/flying-probe data analytics | Realistic failure distributions, yield norms |
| Nick's Software NS-HPDCA product docs | Field names commercial tools expose (feature checklist) |

### Other useful synthetic-data ingredients
- A small open BOM/CPL (centroid) sample to anchor component IDs (use any KiCad demo project)
- IPC-A-610 acceptance criteria summaries (your own notes, kept local)

---

## 5. Knowledge resources (free, all online)

| Resource | Use |
|---|---|
| DuckDB official tutorials (duckdb.org) | SQL spine |
| Streamlit official "30 Days of Streamlit" | Dashboard UI |
| Anthropic Claude API docs (docs.claude.com) | LLM integration |
| ChromaDB documentation | Vector store |
| `rag-document-assistant` (GitHub) — code study | Hybrid RAG pattern |
| `Industrial-Docs-RAG-Chatbot` (GitHub) — code study | FastAPI/industrial framing |
| sentence-transformers documentation | Embedding model selection |
| Keysight i3070 manuals | Log format ground truth |

---

## 6. Time budget

| Phase | Duration | Effort/week |
|---|---|---|
| Pre-build skill warm-up | 1 week (optional) | 5-8 hours |
| Phase 1 — Parser + DuckDB spine | 2 weeks | 8-10 hours/week |
| Phase 2 — Analytics + anomaly detection | 3 weeks | 8-10 hours/week |
| Phase 3 — RAG/LLM co-pilot layer | 2-3 weeks | 8-10 hours/week |
| Polish, docs, portfolio writeup | 1 week | 5-8 hours |
| **Total** | **~8-10 calendar weeks** | **~70-90 hours total** |

This assumes evenings + weekends, not full-time. Fully compatible with a 9-5 job.

---

## 7. Money budget — total honest estimate

| Item | One-time | Recurring |
|---|---|---|
| Hardware | $0 (you have it) | — |
| Software | $0 | — |
| Claude API (dev phase) | — | $20-60 across build |
| Claude API (post-build, occasional demos) | — | <$5/month |
| Domain / hosting | $0 (use your existing portfolio site) | — |
| **Total to ship v1** | **~$0-30 out of pocket** | **~$5/month ongoing** |

---

## 8. What you DON'T need (and would be wasteful to acquire)

- ❌ A bigger laptop or workstation — your current one is fine for everything except training large models, which you won't do.
- ❌ A local LLM setup (Ollama, LM Studio, etc.) — API access is faster, smarter, and cheaper than buying hardware to run a worse local model.
- ❌ A cloud GPU (AWS, RunPod, etc.) — no model training in this project.
- ❌ Paid vector DB (Pinecone, Weaviate Cloud) — ChromaDB is local and free.
- ❌ A paid Streamlit Cloud plan — free tier or local-only is fine for portfolio.
- ❌ Real customer flying-probe data exported off your work network — illegal/risky and architecturally unnecessary.

---

## 9. Viability scorecard

| Dimension | Score | Notes |
|---|---|---|
| Hardware adequacy | ✅ 10/10 | Paid API removes the local-LLM constraint entirely |
| Software availability | ✅ 10/10 | Entire stack is free and open-source |
| API budget | ✅ 9/10 | $20-60 total across build is very manageable |
| Data access | ✅ 8/10 | Synthetic-first design turns the constraint into a feature |
| Documentation availability | ✅ 9/10 | HP3070/i3070 is the best-documented log format publicly |
| Time required | ✅ 8/10 | Fits evening/weekend cadence over ~2 months |
| Skill ramp-up feasibility | ✅ 9/10 | ~2 weeks of new learning, all glue code |
| **Overall viability** | **✅ GREEN LIGHT** | Build it. |

---

## 10. Pre-build checklist (do this week)

- [ ] Sign up for Anthropic API account at console.anthropic.com (grab the $5 free credit)
- [ ] Install Python 3.11+, `uv`, Git, VS Code/Cursor on your dev laptop
- [ ] Create a private GitHub repo: `flying-probe-copilot`
- [ ] Download the Keysight i3070 BT-Basic and Test Methods manuals (free from keysight.com)
- [ ] Bookmark the 3 starter repos: `rag-document-assistant`, `Industrial-Docs-RAG-Chatbot`, `RAG-Anything`
- [ ] Decide a workspace path on `E:\` (suggest `E:\flying-probe-copilot\`)
- [ ] Optional: do the 1-week pre-build warm-up exercises from the SKILLS file

Once these are done, Phase 1 begins.
