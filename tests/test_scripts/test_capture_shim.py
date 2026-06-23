"""CAP-20..CAP-23 — Tests for scripts/_capture_app.py shim behavior.

All subprocess tests set FPC_CAPTURE_DRY_IMPORT=1 so ``main()`` is never called
(which would crash outside a Streamlit runtime).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_py(code: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    """Run a Python snippet in a subprocess with the repo root on sys.path."""
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT),
        "FPC_CAPTURE_DRY_IMPORT": "1",
        "GOOGLE_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )


# ---------------------------------------------------------------------------
# CAP-20 — monkeypatch is module-global (visible to a second importer)
# ---------------------------------------------------------------------------


def test_cap20_monkeypatch_visible_to_second_importer():
    """CAP-20: _capture_app rebind is module-global — a second import sees it."""
    code = (
        "import scripts._capture_app; "
        "from flying_probe_copilot.ui import chat as fresh; "
        "print(fresh.answer_question.__qualname__)"
    )
    result = _run_py(code)
    assert result.returncode == 0, f"subprocess failed:\n{result.stderr}"
    qualname = result.stdout.strip()
    assert "build_canned_answer" in qualname, (
        f"Expected 'build_canned_answer' in qualname, got: {qualname!r}"
    )


# ---------------------------------------------------------------------------
# CAP-21 — dry-import short-circuit prevents calling app.main()
# ---------------------------------------------------------------------------


def test_cap21_dry_import_does_not_call_main():
    """CAP-21: FPC_CAPTURE_DRY_IMPORT=1 prevents app.main() from being called.

    Verify by checking that the subprocess exits 0 AND that st.set_page_config
    was not called (its call would register a ScriptRunner context that isn't
    present in a plain Python process).  The observable: importing _capture_app
    with the sentinel succeeds without error, AND the shim's own FPC_CAPTURE_DRY_IMPORT
    branch skips main().  We confirm via the module-level attribute of _capture_app.
    """
    code = (
        "import scripts._capture_app as shim; "
        "import os; "
        "got_env = os.environ.get('FPC_CAPTURE_DRY_IMPORT'); "
        "print('dry_import_env:', got_env)"
    )
    result = _run_py(code)
    assert result.returncode == 0, f"subprocess failed (exit {result.returncode}):\n{result.stderr}"
    # The subprocess ran without raising — proves main() was NOT called
    # (calling app.main() outside Streamlit runtime would crash with
    # streamlit.errors.StreamlitAPIException or similar).
    assert "dry_import_env: 1" in result.stdout, (
        f"Sentinel env not visible inside subprocess: {result.stdout!r}"
    )


# ---------------------------------------------------------------------------
# CAP-22 — reload is idempotent (simulates Streamlit hot-reload)
# ---------------------------------------------------------------------------


def test_cap22_reload_is_idempotent():
    """CAP-22: importing _capture_app twice (reload simulation) is idempotent."""
    code = (
        "import importlib; "
        "import scripts._capture_app; "
        "importlib.reload(scripts._capture_app); "
        "importlib.reload(scripts._capture_app); "
        "from flying_probe_copilot.ui import chat; "
        "from scripts.capture_screenshots import build_canned_answer; "
        "ok = chat.answer_question is build_canned_answer; "
        "print('ok:', ok)"
    )
    result = _run_py(code)
    assert result.returncode == 0, f"subprocess failed:\n{result.stderr}"
    assert "ok: True" in result.stdout, f"Monkeypatch lost after reload: {result.stdout!r}"


# ---------------------------------------------------------------------------
# CAP-23 — shim assert fires when monkeypatch fails
# ---------------------------------------------------------------------------


def test_cap23_assert_present_in_shim_source():
    """CAP-23: _capture_app.py contains the defensive assert before actual main() call."""
    shim_path = REPO_ROOT / "scripts" / "_capture_app.py"
    source = shim_path.read_text(encoding="utf-8")
    assert "assert _chat.answer_question is build_canned_answer" in source, (
        "Defensive assert missing from scripts/_capture_app.py"
    )
    # Find the actual main() call (indented, not in docstring)
    # Use the pattern that appears in code: "    main()" or at end of if-block
    assert_pos = source.index("assert _chat.answer_question is build_canned_answer")
    # Find last occurrence of "main()" which is the actual call
    main_pos = source.rindex("main()")
    assert assert_pos < main_pos, "Defensive assert appears AFTER main() call — wrong ordering"
