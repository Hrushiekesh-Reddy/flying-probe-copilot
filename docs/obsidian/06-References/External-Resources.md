# External Resources & References

## Repository & Project

- **GitHub Repo**: Private (goes public after Phase 4 guardrails checklist)
- **Portfolio Site**: hrushiekeshreddykanjula.com
- **Owner**: Hrushiekesh Reddy Kanjula — Manufacturing Engineer, ~4 yrs PCBA, Dallas TX

## Hardware Documentation

- **Keysight Log Record Format**: Authoritative format reference found via Virinco public mirror (used for Phase 1a generator design)
- **HP3070 / Keysight i3070 Manuals**: Reference by manual section name only — do not reproduce wholesale (see `docs/GUARDRAILS.md`)
- **Keysight i3070 Test System**: Primary target hardware platform

## Standards (Reference Only — No Verbatim Text)

- **IPC-A-610**: Acceptability of Electronic Assemblies — defines PCBA pass/fail criteria
- **J-STD-001**: Requirements for Soldering Electrical and Electronic Assemblies
- ⚠️ These are copyrighted — summaries and citations only, never verbatim reproduction

## Technology Documentation

### Core Stack
- **DuckDB**: duckdb.org — File-based columnar SQL
- **Pydantic v2**: docs.pydantic.dev — Data models and validation
- **sentence-transformers**: sbert.net — Free local embeddings
- **ChromaDB**: docs.trychroma.com — Local vector store
- **rank-bm25**: PyPI — Lexical search
- **Streamlit**: docs.streamlit.io — Dashboard UI
- **Plotly**: plotly.com/python — Interactive charts

### LLM APIs
- **Google Gemini**: ai.google.dev/docs — Primary LLM (Phase 3)
- **Anthropic Claude**: docs.anthropic.com — Backup LLM + IDE AI (Claude Code)

### Dev Tools
- **uv**: docs.astral.sh/uv — Package manager
- **pytest**: docs.pytest.org — Test framework

## SPC Reference Material

- **Donald Wheeler** — Understanding Statistical Process Control (authoritative XmR source)
- Wheeler doctrine: `sigma = MR̄ / 1.128`, rule_1 (3σ) + rule_4 (run of 8) default
- Why not Western Electric/Nelson rules: designed for X-bar charts, not individuals — excessive false positives on raw measurements

## Target Employers (Portfolio Context)

Dallas-area EMS firms this project targets:
- Celestica
- Jabil
- Sanmina
- Lockheed Martin

## Related Personal Projects

- `E:\my-assembly-hub\` — Full-stack SMT assembly management system
- `E:\Portfolio\` — Personal portfolio website
- `E:\hrk-agent-starter\` — Portable Claude Code agent starter kit

**Tags:** #references #resources #external #tools
