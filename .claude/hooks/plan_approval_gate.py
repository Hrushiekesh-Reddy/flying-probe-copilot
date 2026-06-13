#!/usr/bin/env python3
"""
UserPromptSubmit hook — reminds agent to verify TDD and scope gates
when the owner approves a plan.
Advisory only. Always exits 0.
"""
import json
import sys

APPROVAL_HINTS = [
    "go ahead", "execute the plan", "execute this", "approved",
    "looks good", "proceed", "ship it", "do it", "implement this",
    "run it", "yes, go", "go for it", "start", "begin", "implement",
    "build it", "let's do it",
]

REMINDER = """
╔══════════════════════════════════════════════════════════════════════╗
║  PLAN APPROVAL GATE — Flying-Probe Co-Pilot                         ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Before executing, confirm ALL of the following:                     ║
║                                                                      ║
║  1. BRANCH    Are you on a feature branch (not main or dev)?        ║
║  2. TDD       Tests written FIRST. Red before Green. No exceptions. ║
║  3. SCOPE     Only current-phase deliverables. Nothing from Phase+1.║
║  4. DECISIONS Any architectural choices logged in DECISION_LOG.md?  ║
║  5. CRITICAL  Does this touch an approval-gated file?               ║
║               (pyproject.toml, schema files, migration files,       ║
║                .claude/settings.json, .env.example)                 ║
║               If yes — explicit owner sign-off required.            ║
║                                                                      ║
║  All 5 green? Proceed. Any red? STOP and resolve first.             ║
╚══════════════════════════════════════════════════════════════════════╝
"""


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    prompt = data.get("prompt", "").lower()

    if any(hint in prompt for hint in APPROVAL_HINTS):
        print(REMINDER, file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
