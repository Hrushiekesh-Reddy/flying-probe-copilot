# Flying Probe Copilot - Obsidian Vault

A comprehensive knowledge management system for the Flying Probe Copilot project, combining architecture documentation, project planning, domain knowledge, and continuous learning.

## 📁 Vault Structure

```
docs/flying-probe-copilot-obsidian/
├── 00-Home/              # Navigation hub & project overview
├── 01-Architecture/      # System design & technical decisions
├── 02-Features/          # Feature documentation & specifications
├── 03-Domain-Knowledge/  # Engineering expertise & domain insights
├── 04-Project-Planning/  # Roadmap, sprints, tasks & timelines
├── 05-Learning/          # Lessons learned & how-to guides
├── 06-References/        # External resources & links
└── .obsidian/           # Obsidian configuration (do not edit manually)
```

## 🚀 Getting Started

1. **Open in Obsidian**
   - Download [Obsidian](https://obsidian.md)
   - Open folder: `docs/flying-probe-copilot-obsidian`
   - Trust the vault when prompted

2. **Start with Home**
   - Open `00-Home/Home.md`
   - Use navigation links to explore sections

3. **Quick Commands**
   - `Ctrl+P` (Cmd+P on Mac) - Quick search
   - `Ctrl+O` - Quick file open
   - Graph view - See connections between notes

## 📖 Each Section Explained

### 🏗️ Architecture (01-Architecture/)
**Purpose**: Technical documentation and design decisions
- System diagrams and component overviews
- Architecture Decision Records (ADRs)
- Technical stack details
- Integration points and APIs

**When to use**: Understanding system design, making technical decisions, onboarding new developers

### ✨ Features (02-Features/)
**Purpose**: Feature specifications and tracking
- Feature descriptions and acceptance criteria
- Implementation plans
- Testing strategies
- Status and ownership tracking

**When to use**: Planning features, understanding requirements, tracking progress

### 🔬 Domain Knowledge (03-Domain-Knowledge/)
**Purpose**: Engineering expertise and subject matter
- Probe technology fundamentals
- Testing methodologies
- Hardware knowledge
- Domain-specific math and algorithms

**When to use**: Learning how the system works, solving technical problems, onboarding

### 📋 Project Planning (04-Project-Planning/)
**Purpose**: Roadmap, timelines, and task management
- Product roadmap and strategic goals
- Current sprint tracking
- Feature backlog
- Metrics and progress

**When to use**: Project status, sprint planning, priority setting

### 📚 Learning & Lessons (05-Learning/)
**Purpose**: Capture insights and growth
- Lessons learned from development
- Architecture evolution
- Common gotchas and solutions
- Team best practices

**When to use**: Preventing repeated mistakes, onboarding, decision-making

### 🔗 References (06-References/)
**Purpose**: External resources and links
- Official documentation
- Tool and service links
- Related projects
- Learning materials

**When to use**: Finding external resources, tool documentation

## ✍️ How to Contribute

### Adding Knowledge

1. **Choose the right section** based on the 6 categories above
2. **Use existing templates** (Feature, ADR, etc.)
3. **Link to related notes** using `[[Link Syntax]]`
4. **Add tags** like `#feature`, `#architecture`, `#domain-knowledge`
5. **Keep it updated** - outdated docs are worse than no docs

### Creating a New Note

```markdown
# Title

> Brief one-line summary

## Overview
What is this about?

## Key Points
- Point 1
- Point 2

## Related Notes
- [[Link to related note]]

**Tags:** #relevant-tags
```

### Linking Notes

Use wikilinks to connect notes:
```markdown
[[01-Architecture/ADRs|Read the ADRs]]
[[02-Features/Feature-Template|Feature Template]]
```

## 🔍 Discovery Tools

### Search
- Use `Ctrl+P` to search all notes
- Filter by `#tag` in search

### Graph View
- Visualize connections between notes
- Find knowledge clusters
- Identify missing documentation

### Backlinks
- See what links to current note
- Find related content
- Understand context

## 🚫 What NOT to Put Here

- **Code** - Keep in source files with comments
- **Logs** - Track in logging systems
- **Temporary notes** - Use daily notes instead
- **Sensitive data** - Never include credentials or API keys

## 💡 Best Practices

1. **Keep it DRY** - Link to other notes instead of duplicating
2. **Use Headers** - Make scanning easy
3. **Add context** - Not just "what" but "why"
4. **Date decisions** - When was this decided/learned?
5. **Maintain tags** - Makes filtering and searching better
6. **Link aggressively** - Cross-reference everything
7. **Review regularly** - Mark outdated notes for update

## 🔄 Maintenance

### Weekly
- Update [[04-Project-Planning/Current-Sprint|Current Sprint]] status
- Add new [[05-Learning/Learning-Log|learnings to log]]

### Monthly
- Review [[01-Architecture/ADRs|ADRs]] for relevance
- Update [[04-Project-Planning/Project-Dashboard|metrics]]
- Check for broken links

### Quarterly
- Review [[01-Architecture/Architecture-Overview|architecture]] for accuracy
- Update [[04-Project-Planning/Roadmap|roadmap]]
- Consolidate [[05-Learning/Learning-Log|lessons learned]]

## 📚 Git Integration

This vault is version-controlled:
- Commit changes along with code
- `.obsidian/` config is tracked
- `.obsidian/workspace.json` can be ignored (local UI state)
- Resolve merge conflicts in markdown as normal text

**Suggestion**: Commit vault changes with related code changes to keep history aligned.

## 🆘 Troubleshooting

### Links not working?
- Use `[[Exact Note Name]]` format
- Check that the note file exists
- Use forward slashes for folders: `[[01-Architecture/ADRs]]`

### Can't see backlinks?
- Enable the Backlinks pane in Obsidian settings
- Add more wikilinks to create connections

### Want to customize?
- Obsidian settings are in `.obsidian/app.json`
- Plugin recommendations: Dataview, Calendar, Tag Wrangler
- Daily notes template can be configured in settings

---

**Last Updated**: 2026-06-20  
**Vault Version**: 1.0  
**Maintained By**: [Team]

For questions or suggestions about this vault structure, open an issue or discuss with the team.
