"""F18 — Sidebar DOM-shape canary test (env-gated CAPTURE_RUN_PLAYWRIGHT=1).

Pins the actual sidebar DOM structure on the current Streamlit + browser version.
Catches a future Streamlit release that renames ``data-testid='stSidebarNav'``
so we hear about it from this test instead of a mysterious capture failure.

Run manually:
    CAPTURE_RUN_PLAYWRIGHT=1 uv run pytest tests/test_scripts/test_streamlit_sidebar_dom_shape.py -v
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest

_gate_active = os.environ.get("CAPTURE_RUN_PLAYWRIGHT") == "1"

if not _gate_active:
    pytest.skip(
        "Set CAPTURE_RUN_PLAYWRIGHT=1 to run sidebar DOM shape tests",
        allow_module_level=True,
    )

from scripts.capture_screenshots import pick_free_port, _wait_for_health  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_f18_sidebar_nav_testid_present(ui_db_path, tmp_path):
    """F18: stSidebarNav data-testid is present in the live Streamlit sidebar."""
    from playwright.sync_api import sync_playwright

    port = pick_free_port()
    env = {**os.environ, "FPC_DB_PATH": ui_db_path}
    cmd = [
        sys.executable, "-m", "streamlit", "run", "scripts/_capture_app.py",
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--logger.level", "error",
    ]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            cwd=str(REPO_ROOT))
    try:
        _wait_for_health(port)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"http://127.0.0.1:{port}")
            page.wait_for_load_state("networkidle")

            # Assert sidebar nav testid is present
            sidebar_nav = page.locator("[data-testid='stSidebarNav']")
            assert sidebar_nav.count() > 0, (
                "data-testid='stSidebarNav' not found — Streamlit may have renamed it"
            )

            # Assert at least one sidebar link is found
            links = sidebar_nav.get_by_role("link")
            count = links.count()
            assert count >= 6, (
                f"Expected >= 6 sidebar nav links, found {count}. "
                "Check PAGE_CAPTURE_SPECS vs app.py page titles."
            )

            browser.close()
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
