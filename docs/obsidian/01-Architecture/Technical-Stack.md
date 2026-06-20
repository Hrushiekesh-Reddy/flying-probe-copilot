# Technical Stack

Complete overview of technologies, frameworks, and tools used in Flying Probe Copilot.

## Language & Runtime

- **Primary Language**: Python 3.11+
- **Package Manager**: `uv` (fastest modern Python tool — replaces pip/poetry for this project)

## Core Frameworks

### Data Layer
- **Database**: DuckDB — file-based columnar SQL, no service required
  - Why: Analytics-fast, SQLite simplicity, Postgres-compatible SQL — see [[ADRs#ADR-004]]
  - Schema: 9 tables (`src/flying_probe_copilot/db/schema.py`)
  - Sample DB: `data/db/sample.duckdb` (gitignored)

### Analytics
- **Stats/Pandas**: Standard Python stdlib + DuckDB native SQL
- **SPC**: Custom implementation (Wheeler XmR doctrine, no external stats lib)
- **Anomaly Detection**: Z-score leave-one-out (no sklearn in Phase 2)

### RAG Layer (Phase 3)
- **Vector Store**: ChromaDB (local, no service required)
- **Lexical Search**: `rank-bm25`
- **Fusion**: Reciprocal Rank Fusion (RRF) — custom implementation
- **Embeddings**: `sentence-transformers` (free, local, GPU-accelerated if available)
- **LLM API**: Google Gemini (primary) — `google-generativeai` SDK
- **LLM Backup**: Anthropic Claude API

### UI (Phase 2 slice 3+)
- **Dashboard**: Streamlit
- **Charts**: Plotly

### Testing
- **Framework**: pytest
- **Coverage Target**: 97%+ (current: 97%)
- **Current Count**: 292 passing / 1 xfailed / 0 failing

## Dev Dependencies

| Tool | Purpose |
|------|---------|
| `uv` | Package manager + venv |
| `pytest` | Test runner |
| `pytest-cov` | Coverage reporting |
| `pydantic v2` | Data models (generator models use v2 validators) |
| `python-dotenv` | API key management from `.env` |

## Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `duckdb` | latest | SQL spine |
| `pydantic` | v2 | Data models |
| `python-dotenv` | latest | `.env` loading |
| `streamlit` | latest | Dashboard UI (Phase 3) |
| `plotly` | latest | Charts (Phase 3) |
| `chromadb` | latest | Vector store (Phase 3) |
| `sentence-transformers` | latest | Embeddings (Phase 3) |
| `rank-bm25` | latest | Lexical search (Phase 3) |
| `google-generativeai` | latest | Gemini LLM API (Phase 3) |

## Infrastructure

- **Deployment**: Local only (v1). No cloud deployment.
- **CI/CD**: GitHub Actions (Phase 4 — not yet wired)
- **Repo**: Private GitHub repo (will go public after Phase 4 guardrails checklist)

## Development Environment

### Multi-IDE Workflow
- **Claude Code**: Exploration, planning, debugging, doc generation
- **Cursor**: Primary builder for component code
- **Both**: Read `CLAUDE.md` as the memory bridge

### Setup
```bash
# Install uv (one-time)
pip install uv

# Create venv + install deps
uv sync

# Run tests
uv run pytest

# Run generator
uv run generator --board-profile=medium --count=100 --out=data/synthetic/

# Run parser
uv run parser --input=data/synthetic/<run_dir>/ --db=data/db/flying-probe.duckdb
```

### Environment Variables
- `.env` — API keys (gitignored, never committed)
- `.env.example` — template (committed)
- Required: `GOOGLE_API_KEY` (Gemini), optionally `ANTHROPIC_API_KEY` (backup)

## Guardrails (Non-Negotiable)

- ❌ No real customer log data in repo or any home machine
- ❌ No IPC-A-610 / J-STD-001 verbatim text (copyrighted)
- ❌ No Keysight documentation copied wholesale
- ❌ No API keys committed (use `.env`)
- ✅ All committed data is synthetic

---

**Tags:** #architecture #tech-stack #dependencies
