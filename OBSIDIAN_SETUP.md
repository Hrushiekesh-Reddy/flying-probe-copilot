# Obsidian Knowledge Base Setup

## Quick Start

### Two ways to open this project in Obsidian

- **Project-as-vault (recommended, 2026-06-28):** File → "Open folder as vault" → select the **project root** `~/Projects/flying-probe-copilot`. Everything in the repo — CLAUDE.md, README.md, the existing `docs/flying-probe-copilot-obsidian/` taxonomy as a substructure, `docs/plans/`, `docs/logs/`, `docs/knowledge-base/`, `docs/case-study.md`, the standalone `docs/{SCOPE,DECISIONS,ROADMAP,GUARDRAILS,REQUIREMENTS,SKILLS}.md` — appears in one graph. A pre-seeded `.obsidian/app.json` excludes noise (`.venv/`, `__pycache__/`, `.git/`, `.cursor/`, `.claude/`, `.github/`, `data/`, `uv.lock`).
- **Vault-only:** File → "Open folder as vault" → select `docs/flying-probe-copilot-obsidian`. Just the curated 7-folder knowledge zone. Use when you want a focused reading view.

### Why project-as-vault

Plans, logs, the case study, the standalone docs at `docs/*.md`, and the project's CLAUDE.md / README all live outside the per-project vault — but they're real project knowledge you'll want to read and edit in Obsidian with backlinks and graph visibility. Opening the project root as the vault brings everything into one graph without moving any files. The `.claude/` scaffolding keeps reading from the canonical paths. Cross-project convention: see `~/Projects/Personal-Assistant/vault/02-Decisions/2026-06-28-hrk-agent-starter-plans-logs-in-vault.md` for why we didn't formalize this at the starter level (yet).

### Other quick-start steps

1. **Install Obsidian**: Download from https://obsidian.md
2. **Trust Vault**: Click "Trust author" when prompted
3. **Read Home**: Open `docs/flying-probe-copilot-obsidian/00-Home/Home.md` to navigate

## What's Inside

This vault provides **4 layers of knowledge**:

### 🏗️ Architecture
- System design & technical decisions
- Decision records (ADRs)
- Technology stack

### ✨ Features
- Feature specifications
- Implementation plans
- Status tracking

### 🔬 Domain Knowledge  
- Probe technology fundamentals
- Testing methodologies
- Hardware & integration knowledge

### 📋 Project Planning + 📚 Learning
- Roadmap & sprints
- Lessons learned
- Best practices & gotchas

## Key Features to Use

### Search (`Ctrl+P`)
Find any note by name or content

### Wikilinks (`[[Link]]`)
Click to jump between related notes

### Graph View
Visualize connections between topics

### Tags
Search by `#feature`, `#architecture`, `#domain-knowledge`

## Maintenance Tips

- **Weekly**: Update sprint status in Project Planning
- **Monthly**: Review and update metrics
- **As you learn**: Add to Learning Log
- **Before commits**: Link new docs to existing notes

## Next Steps

1. ✅ Vault is set up - start reading!
2. Open [[00-Home/Home.md]] for navigation
3. Fill in `[TODO]` items as you document the system
4. Link related features, architecture, and domain knowledge

---

**Need help?** Check `docs/flying-probe-copilot-obsidian/README.md` for detailed documentation.
