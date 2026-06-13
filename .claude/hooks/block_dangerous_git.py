#!/usr/bin/env python3
"""
PreToolUse hook — blocks dangerous git commands.
Permanent branches for flying-probe-copilot: main, dev
Exit 2 = blocked. Exit 0 = allowed.
"""
import json
import sys

PERMANENT_BRANCHES = {"main", "dev"}


def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name not in ("Bash", "PowerShell"):
        sys.exit(0)

    cmd = tool_input.get("command", "")
    if not cmd:
        sys.exit(0)

    cmd_lower = cmd.lower()

    # Block force-push variants
    if "git push" in cmd_lower:
        if any(flag in cmd_lower for flag in ["--force", "--force-with-lease", " -f "]):
            _block("Force-push is blocked. Never force-push any branch.")

        # Block direct push to permanent branches
        for branch in PERMANENT_BRANCHES:
            if f"origin {branch}" in cmd_lower or f"origin/{branch}" in cmd_lower:
                _block(
                    f"Direct push to '{branch}' is blocked. "
                    "Use a feature branch — push to origin feature/your-branch instead."
                )

        # Block --all / --mirror (could leak into permanent branches)
        if "--all" in cmd_lower or "--mirror" in cmd_lower:
            _block("git push --all / --mirror is blocked. Push feature branches individually.")

    # Block deletion of permanent branches
    if "git branch" in cmd_lower:
        for branch in PERMANENT_BRANCHES:
            if branch in cmd and ("-d " in cmd_lower or "--delete" in cmd_lower or "-D " in cmd_lower):
                _block(f"Deleting permanent branch '{branch}' is blocked.")
        if "-D " in cmd_lower or "-D\t" in cmd_lower:
            _block("Force-delete branch (-D) is blocked. Use -d for a safe delete.")

    # Block destructive history rewrites
    if "git reset" in cmd_lower and "--hard" in cmd_lower:
        _block("git reset --hard is blocked. Use git stash or git revert instead.")

    if "git clean" in cmd_lower and "-f" in cmd_lower:
        _block("git clean -f is blocked. Remove files manually after confirming.")

    if "git checkout" in cmd_lower and " ." in cmd:
        _block("git checkout . is blocked — discards all uncommitted changes.")

    if "git restore" in cmd_lower and " ." in cmd:
        _block("git restore . is blocked — discards all uncommitted changes.")

    sys.exit(0)


def _block(reason: str) -> None:
    msg = {"decision": "block", "reason": f"[git-guard] {reason}"}
    print(json.dumps(msg))
    sys.exit(2)


if __name__ == "__main__":
    main()
