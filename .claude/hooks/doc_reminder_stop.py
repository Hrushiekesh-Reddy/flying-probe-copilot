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


def main():
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.strip().splitlines()
    except Exception:
        sys.exit(0)

    src_changed = any(
        line[3:].startswith("src/") or line[3:].endswith(".py")
        for line in lines
    )
    doc_changed = any(
        "docs/" in line or line[3:].endswith(".md")
        for line in lines
    )

    if src_changed and not doc_changed:
        print(REMINDER, file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
