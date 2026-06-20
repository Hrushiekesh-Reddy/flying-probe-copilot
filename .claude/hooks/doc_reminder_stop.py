#!/usr/bin/env python3
"""
Stop hook — nudges agent to update docs when source files have changed.
Advisory only. Always exits 0.
"""
import subprocess
import sys


REMINDER = """
╔══════════════════════════════════════════════════════════════════════╗
║  SESSION-END REMINDER — Flying-Probe Co-Pilot                       ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Source files changed but no doc updates detected.                  ║
║  Before committing, work through this checklist:                    ║
║                                                                      ║
║  [ ] docs/logs/SESSION_LOG.md    — add today's entry               ║
║  [ ] docs/logs/DECISION_LOG.md   — any decisions made?             ║
║  [ ] docs/logs/BUG_LOG.md        — any bugs that took >5 min?      ║
║  [ ] docs/ROADMAP.md             — any deliverables completed?      ║
║  [ ] CLAUDE.md                   — update session log line          ║
║  [ ] uv run pytest               — all tests green?                 ║
║                                                                      ║
║  Code changes without doc updates = incomplete work.                 ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# Maps changed path prefixes to Obsidian vault notes that need syncing
OBSIDIAN_MAP = [
    ("src/flying_probe_copilot/analytics/", ["02-Features/Features-Index.md", "04-Project-Planning/Project-Dashboard.md"]),
    ("src/flying_probe_copilot/ui/",        ["02-Features/Features-Index.md", "04-Project-Planning/Project-Dashboard.md"]),
    ("src/flying_probe_copilot/rag/",       ["02-Features/Features-Index.md", "04-Project-Planning/Project-Dashboard.md"]),
    ("src/flying_probe_copilot/parser/",    ["01-Architecture/Architecture-Overview.md"]),
    ("src/flying_probe_copilot/db/",        ["01-Architecture/Architecture-Overview.md"]),
    ("CLAUDE.md",                           ["05-Learning/Learning-Log.md", "00-Home/Home.md"]),
    ("docs/ROADMAP.md",                     ["04-Project-Planning/Roadmap.md"]),
    ("docs/DECISIONS.md",                   ["01-Architecture/ADRs.md"]),
    ("pyproject.toml",                      ["01-Architecture/Technical-Stack.md"]),
]


def obsidian_nudge(changed_files: list) -> str | None:
    notes_to_update = []
    seen = set()
    for path in changed_files:
        for prefix, vault_notes in OBSIDIAN_MAP:
            if path.startswith(prefix) or path == prefix.rstrip("/"):
                for note in vault_notes:
                    if note not in seen:
                        notes_to_update.append(note)
                        seen.add(note)
    if not notes_to_update:
        return None
    lines = ["[obsidian] Consider syncing these vault notes:"]
    for note in notes_to_update:
        lines.append(f"  docs/obsidian/{note}")
    lines.append("  → tell Claude: 'sync the obsidian vault'")
    return "\n".join(lines)


def main():
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.strip().splitlines()
    except Exception:
        sys.exit(0)

    changed_files = [line[3:].strip() for line in lines if line.strip()]

    src_changed = any(
        f.startswith("src/") or f.endswith(".py")
        for f in changed_files
    )
    doc_changed = any(
        "docs/" in f or f.endswith(".md")
        for f in changed_files
    )

    if src_changed and not doc_changed:
        print(REMINDER, file=sys.stderr)

    nudge = obsidian_nudge(changed_files)
    if nudge:
        print(nudge, file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
