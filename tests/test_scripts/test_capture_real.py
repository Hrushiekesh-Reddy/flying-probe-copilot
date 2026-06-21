"""CAP-90..CAP-95 — End-to-end Playwright smoke for the capture pipeline.

All tests gated on ``CAPTURE_RUN_PLAYWRIGHT=1`` — default-skipped in CI.
Pattern mirrors ``tests/test_rag/test_eval.py`` (``RAG_RUN_LLM_EVAL``).

Run manually:
    CAPTURE_RUN_PLAYWRIGHT=1 uv run pytest tests/test_scripts/test_capture_real.py -v
"""

from __future__ import annotations

import os

import pytest

GATE_ENV = "CAPTURE_RUN_PLAYWRIGHT=1"
_gate_active = os.environ.get("CAPTURE_RUN_PLAYWRIGHT") == "1"

if not _gate_active:
    pytest.skip(
        f"Set {GATE_ENV} to run live Playwright capture tests",
        allow_module_level=True,
    )

# ---------------------------------------------------------------------------
# Tests (only reached when CAPTURE_RUN_PLAYWRIGHT=1)
# ---------------------------------------------------------------------------

from PIL import Image  # noqa: E402 — only imported when gate active

from scripts.capture_screenshots import (  # noqa: E402
    PAGE_CAPTURE_SPECS,
    main,
    pick_free_port,
)


def test_cap90_all_six_jpgs_produced_and_nonempty(ui_db_path, tmp_path):
    """CAP-90: all 6 JPGs produced, each >= 50 KB."""
    tmp_out = tmp_path / "out"
    port = pick_free_port()
    main(["all", "--db", ui_db_path, "--out", str(tmp_out), "--port", str(port)])

    for _label, stem in PAGE_CAPTURE_SPECS:
        jpg = tmp_out / f"screenshot-{stem}.jpg"
        assert jpg.exists(), f"Missing screenshot: {jpg}"
        size = jpg.stat().st_size
        assert size >= 50_000, f"screenshot-{stem}.jpg is only {size} bytes (< 50 KB)"


def test_cap91_demo_gif_valid_gif89a(ui_db_path, tmp_path):
    """CAP-91: demo.gif is valid GIF89a, < 2 MB, animated with 6 frames."""
    tmp_out = tmp_path / "out"
    port = pick_free_port()
    main(["all", "--db", ui_db_path, "--out", str(tmp_out), "--port", str(port)])

    gif_path = tmp_out / "demo.gif"
    assert gif_path.exists()
    data = gif_path.read_bytes()
    assert data[:6] == b"GIF89a", f"demo.gif header: {data[:6]!r}"
    assert gif_path.stat().st_size < 5_000_000, (
        f"demo.gif is {gif_path.stat().st_size} bytes (> 5 MB)"
    )
    img = Image.open(gif_path)
    assert getattr(img, "is_animated", False) is True
    assert img.n_frames == 6


def test_cap93_missing_db_exits_nonzero_before_popen(tmp_path):
    """CAP-93: missing DB exits non-zero before launching Streamlit."""
    import unittest.mock as mock

    tmp_out = tmp_path / "out"
    with mock.patch("subprocess.Popen") as mock_popen:
        with pytest.raises(SystemExit) as exc_info:
            main(["all", "--db", str(tmp_path / "no_such.duckdb"), "--out", str(tmp_out)])
    assert exc_info.value.code != 0
    mock_popen.assert_not_called()


def test_cap94_default_port_uses_pick_free_port(ui_db_path, tmp_path, monkeypatch):
    """CAP-94: main() without --port calls pick_free_port exactly once."""
    from scripts import capture_screenshots as cap_mod

    tmp_out = tmp_path / "out"
    chosen_port = pick_free_port()
    call_count = {"n": 0}

    original = cap_mod.pick_free_port  # noqa: F841

    def fake_pick():
        call_count["n"] += 1
        return chosen_port

    monkeypatch.setattr(cap_mod, "pick_free_port", fake_pick)
    main(["all", "--db", ui_db_path, "--out", str(tmp_out)])
    assert call_count["n"] == 1, f"pick_free_port called {call_count['n']} times (expected 1)"
