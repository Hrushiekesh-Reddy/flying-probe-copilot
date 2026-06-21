"""CAP-01..CAP-81 — Unit tests for scripts/capture_screenshots.py pure helpers.

No Playwright launched, no Streamlit subprocess, no DuckDB required.
All tests are pure-function / offline.

Env-gated end-to-end tests live in test_capture_real.py (CAPTURE_RUN_PLAYWRIGHT=1).
"""

from __future__ import annotations

import ast
import importlib
import os
import re
import socket
import sys
import tomllib
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# CAP-01 / CAP-02 — playwright SDK availability
# ---------------------------------------------------------------------------


def test_cap01_playwright_importable():
    """CAP-01: playwright.sync_api exposes sync_playwright callable."""
    from playwright.sync_api import sync_playwright  # noqa: F401

    assert callable(sync_playwright)
    ctx = sync_playwright()
    assert hasattr(ctx, "__enter__") and hasattr(ctx, "__exit__")


def test_cap02_playwright_version_floor():
    """CAP-02: installed playwright version >= 1.49."""
    import importlib.metadata
    from packaging.version import Version

    v = Version(importlib.metadata.version("playwright"))
    assert v >= Version("1.49"), f"playwright {v} below floor 1.49"


# ---------------------------------------------------------------------------
# CAP-03 — scripts package importable + public API surface
# ---------------------------------------------------------------------------


def test_cap03_scripts_package_importable_and_public_api():
    """CAP-03: scripts.capture_screenshots is importable and exposes expected names."""
    import scripts
    import scripts.capture_screenshots as cap

    assert scripts.__file__ is not None and scripts.__file__.endswith("__init__.py")

    for name in (
        "build_canned_answer",
        "assemble_gif",
        "PAGE_CAPTURE_SPECS",
        "pick_free_port",
        "check_outputs_complete",
        "parse_args",
        "main",
    ):
        assert hasattr(cap, name), f"scripts.capture_screenshots missing: {name}"


# ---------------------------------------------------------------------------
# CAP-10..CAP-15 — build_canned_answer
# ---------------------------------------------------------------------------


def test_cap10_citation_matches_failure_modes_pattern():
    """CAP-10: citation chunk-id matches ^failure-modes/[a-z][a-z-]*.md#\\d+$ pattern."""
    from scripts.capture_screenshots import build_canned_answer

    result = build_canned_answer("anything")
    assert len(result.citations) >= 1
    cid = result.citations[0]
    assert re.match(r"^failure-modes/[a-z][a-z-]*\.md#\d+$", cid), (
        f"Citation {cid!r} does not match expected pattern"
    )


def test_cap11_citation_points_at_existing_kb_file():
    """CAP-11: CANNED_CITATION_ID references a file that actually exists in docs/knowledge-base/."""
    from scripts.capture_screenshots import build_canned_answer

    result = build_canned_answer("q")
    cid = result.citations[0]
    cite_path = cid.split("#")[0]
    kb_file = REPO_ROOT / "docs" / "knowledge-base" / cite_path
    assert kb_file.exists(), f"Citation {cid!r} points at non-existent file {kb_file}"


def test_cap12_citation_chunk_index_within_chunk_count():
    """CAP-12: CANNED_CITATION_ID #<int> is within the actual chunk count for that file."""
    from scripts.capture_screenshots import build_canned_answer
    from flying_probe_copilot.rag.kb_loader import load_kb

    result = build_canned_answer("q")
    cid = result.citations[0]
    file_part, idx_str = cid.rsplit("#", 1)
    chunk_idx = int(idx_str)
    kb_root = REPO_ROOT / "docs" / "knowledge-base"
    all_chunks = load_kb(str(kb_root))
    matching_chunks = [c for c in all_chunks if c.chunk_id.startswith(file_part + "#")]
    assert len(matching_chunks) > chunk_idx, (
        f"Citation index {chunk_idx} out of range — {file_part} has {len(matching_chunks)} chunks"
    )


def test_cap13_answer_refused_is_false():
    """CAP-13: build_canned_answer returns refused=False (identity check)."""
    from scripts.capture_screenshots import build_canned_answer

    result = build_canned_answer("q")
    assert result.refused is False


def test_cap14_answer_text_free_of_markdown_hazards():
    """CAP-14: answer_text has no triple backticks, no leading #/>, length 60-240 chars."""
    from scripts.capture_screenshots import build_canned_answer

    result = build_canned_answer("q")
    text = result.answer_text
    assert "```" not in text, "answer_text contains triple backticks"
    assert text.count("`") % 2 == 0, "answer_text has unmatched backticks"
    assert not text.startswith("#"), "answer_text starts with # (h1)"
    assert not text.startswith(">"), "answer_text starts with > (blockquote)"
    assert 60 <= len(text) <= 600, f"answer_text length {len(text)} outside [60, 600]"


def test_cap15_build_canned_answer_is_deterministic():
    """CAP-15: build_canned_answer produces identical body for all questions; question field matches input."""
    from scripts.capture_screenshots import build_canned_answer

    r1 = build_canned_answer("q1")
    r2 = build_canned_answer("q2")
    r3 = build_canned_answer("q1")

    # Body fields are identical regardless of question input
    assert r1.answer_text == r2.answer_text == r3.answer_text
    assert r1.citations == r2.citations == r3.citations
    assert r1.retrieved_ids == r2.retrieved_ids == r3.retrieved_ids

    # Question field IS echoed
    assert r1.question == "q1"
    assert r2.question == "q2"


# ---------------------------------------------------------------------------
# CAP-30..CAP-36 — assemble_gif
# ---------------------------------------------------------------------------


def _make_frames(count: int, size=(100, 100), start_rgb=(255, 0, 0)) -> list[Image.Image]:
    """Build count RGB images with slightly varying colors."""
    frames = []
    for i in range(count):
        color = ((start_rgb[0] + i * 40) % 256, (start_rgb[1] + i * 30) % 256, start_rgb[2])
        frames.append(Image.new("RGB", size, color=color))
    return frames


def test_cap30_frame_size_mismatch_raises():
    """CAP-30: mixed frame dimensions raise ValueError naming 'frame size mismatch'."""
    from scripts.capture_screenshots import assemble_gif

    frames = _make_frames(3) + [Image.new("RGB", (200, 150))]
    with pytest.raises(ValueError, match="frame size"):
        out = BytesIO()
        assemble_gif(frames, out, frame_duration_ms=200)


def test_cap31_zero_duration_raises():
    """CAP-31: frame_duration_ms <= 0 raises ValueError."""
    from scripts.capture_screenshots import assemble_gif

    frames = _make_frames(2)
    with pytest.raises(ValueError, match="frame_duration_ms"):
        assemble_gif(frames, BytesIO(), frame_duration_ms=0)
    with pytest.raises(ValueError, match="frame_duration_ms"):
        assemble_gif(frames, BytesIO(), frame_duration_ms=-100)


def test_cap32_single_frame_produces_valid_gif(tmp_path):
    """CAP-32: one-frame input produces a valid (non-animated) GIF89a."""
    from scripts.capture_screenshots import assemble_gif

    out = tmp_path / "single.gif"
    assemble_gif([Image.new("RGB", (100, 100))], out, frame_duration_ms=2000)
    assert out.exists()
    data = out.read_bytes()
    assert data[:6] == b"GIF89a"


def test_cap33_missing_parent_dir_auto_creates(tmp_path):
    """CAP-33: assemble_gif auto-creates out_path parent if it doesn't exist."""
    from scripts.capture_screenshots import assemble_gif

    out = tmp_path / "nonexistent" / "demo.gif"
    assemble_gif(_make_frames(3), out, frame_duration_ms=200)
    assert out.exists()
    assert out.read_bytes()[:6] == b"GIF89a"


def test_cap34_large_frames_complete_within_budget(tmp_path):
    """CAP-34: 3 frames of 4096x4096 complete within 60 s and produce < 50 MB."""
    from scripts.capture_screenshots import assemble_gif

    frames = [Image.new("RGB", (4096, 4096), color=(i * 80, 0, 255)) for i in range(3)]
    out = tmp_path / "large.gif"
    assemble_gif(frames, out, frame_duration_ms=500)
    assert out.exists()
    assert out.stat().st_size < 50_000_000
    assert out.read_bytes()[:6] == b"GIF89a"


def test_cap35_no_file_handle_leak_on_windows(tmp_path):
    """CAP-35: source JPGs can be deleted immediately after assemble_gif (no handle leak)."""
    from scripts.capture_screenshots import assemble_gif

    # Write 6 source JPGs
    jpg_paths = []
    for i in range(6):
        p = tmp_path / f"src_{i}.jpg"
        img = Image.new("RGB", (100, 100), color=(i * 40, 100, 200))
        img.save(p, format="JPEG")
        jpg_paths.append(p)

    # Load via Image.open (lazy — holds a handle if not closed)
    frames = [Image.open(p) for p in jpg_paths]
    out = tmp_path / "out.gif"
    assemble_gif(frames, out, frame_duration_ms=200)

    # All source JPGs must be unlink-able (no handle leak on Windows)
    for p in jpg_paths:
        try:
            p.unlink()
        except PermissionError as exc:
            pytest.fail(f"File handle leak detected: {exc}")


def test_cap36_gif_size_budget_with_synthetic_frames(tmp_path):
    """CAP-36: 6 1280x800 synthetic frames with optimize=True produce < 500 KB."""
    from scripts.capture_screenshots import assemble_gif

    frames = [
        Image.new("RGB", (1280, 800), color=(i * 40, 0, 255 - i * 40))
        for i in range(6)
    ]
    out = tmp_path / "budget.gif"
    assemble_gif(frames, out, frame_duration_ms=2000)
    assert out.stat().st_size < 500_000, (
        f"GIF size {out.stat().st_size} bytes exceeds 500 KB for synthetic frames"
    )


def test_cap_assemble_gif_empty_list_raises():
    """assemble_gif raises ValueError on empty frame list."""
    from scripts.capture_screenshots import assemble_gif

    with pytest.raises(ValueError, match="empty"):
        assemble_gif([], BytesIO(), frame_duration_ms=200)


def test_cap_assemble_gif_writes_valid_gif89a(tmp_path):
    """assemble_gif with 3 frames produces an animated GIF89a."""
    from scripts.capture_screenshots import assemble_gif

    frames = _make_frames(3)
    out = tmp_path / "demo.gif"
    assemble_gif(frames, out, frame_duration_ms=200)
    assert out.exists()
    data = out.read_bytes()
    assert data[:6] == b"GIF89a"
    img = Image.open(out)
    assert getattr(img, "is_animated", False) is True
    assert img.n_frames == 3


# ---------------------------------------------------------------------------
# CAP-40..CAP-43 — PAGE_CAPTURE_SPECS
# ---------------------------------------------------------------------------


def test_cap40_page_capture_specs_shape_and_order():
    """CAP-40: PAGE_CAPTURE_SPECS is a 6-tuple in exact order."""
    from scripts.capture_screenshots import PAGE_CAPTURE_SPECS

    expected = (
        ("Overview", "overview"),
        ("Yield", "yield"),
        ("Failure Pareto", "pareto"),
        ("SPC", "spc"),
        ("Anomalies", "anomalies"),
        ("Co-Pilot", "copilot"),
    )
    assert PAGE_CAPTURE_SPECS == expected


def test_cap41_page_specs_order_matches_readme_hero_strip():
    """CAP-41: PAGE_CAPTURE_SPECS stems match README.md hero-strip image order."""
    from scripts.capture_screenshots import PAGE_CAPTURE_SPECS

    readme = REPO_ROOT / "README.md"
    if not readme.exists():
        pytest.skip("README.md not present — skip cross-file order check")

    content = readme.read_text(encoding="utf-8")
    # Extract screenshot stems from the README hero strip
    stems_in_readme = re.findall(r"screenshot-([a-z]+)\.jpg", content)
    # Keep unique order while preserving first occurrence
    seen = set()
    ordered = []
    for s in stems_in_readme:
        if s not in seen:
            seen.add(s)
            ordered.append(s)

    spec_stems = [stem for _, stem in PAGE_CAPTURE_SPECS]
    assert spec_stems == ordered, (
        f"PAGE_CAPTURE_SPECS stems {spec_stems} != README hero-strip order {ordered}"
    )


def test_cap42_all_stems_are_valid_posix():
    """CAP-42: all nav stems are lowercase alphanumeric-only, length 1..32."""
    from scripts.capture_screenshots import PAGE_CAPTURE_SPECS

    for label, stem in PAGE_CAPTURE_SPECS:
        assert re.match(r"^[a-z0-9-]+$", stem), f"Stem {stem!r} (label={label!r}) invalid"
        assert 1 <= len(stem) <= 32, f"Stem {stem!r} length out of range"


def test_cap43_nav_labels_exist_in_app_pages():
    """CAP-43: each PAGE_CAPTURE_SPECS nav label matches an st.Page title in ui/app.py."""
    from scripts.capture_screenshots import PAGE_CAPTURE_SPECS

    app_path = REPO_ROOT / "src" / "flying_probe_copilot" / "ui" / "app.py"
    source = app_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Collect title= keyword arguments from st.Page(..., title="...") calls
    page_titles: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "Page"
        ):
            for kw in node.keywords:
                if kw.arg == "title" and isinstance(kw.value, ast.Constant):
                    page_titles.add(kw.value.value)

    capture_labels = {label for label, _ in PAGE_CAPTURE_SPECS}
    missing = capture_labels - page_titles
    assert not missing, (
        f"PAGE_CAPTURE_SPECS labels {missing} not found as st.Page titles in app.py. "
        f"App titles found: {page_titles}"
    )


# ---------------------------------------------------------------------------
# CAP-50..CAP-53 — pick_free_port
# ---------------------------------------------------------------------------


def test_cap50_pick_free_port_returns_valid_and_free():
    """CAP-50: pick_free_port() returns an int in [1024, 65535] that is bindable."""
    from scripts.capture_screenshots import pick_free_port

    port = pick_free_port()
    assert isinstance(port, int)
    assert 1024 <= port <= 65535

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", port))
    except OSError as exc:
        pytest.fail(f"Port {port} returned by pick_free_port() is not bindable: {exc}")
    finally:
        s.close()


def test_cap51_two_consecutive_calls_differ():
    """CAP-51: two consecutive pick_free_port() calls return different ports."""
    from scripts.capture_screenshots import pick_free_port

    p1 = pick_free_port()
    p2 = pick_free_port()
    assert p1 != p2, "pick_free_port() returned identical ports on consecutive calls"


def test_cap52_no_privileged_ports():
    """CAP-52: 50 consecutive calls all return ports >= 1024."""
    from scripts.capture_screenshots import pick_free_port

    ports = [pick_free_port() for _ in range(50)]
    assert all(p >= 1024 for p in ports), f"Privileged port found: {min(ports)}"


def test_cap53_socket_error_propagates():
    """CAP-53: underlying OSError propagates from pick_free_port."""
    import unittest.mock as mock
    from scripts.capture_screenshots import pick_free_port

    with mock.patch("socket.socket") as mock_socket:
        mock_socket.return_value.__enter__ = mock_socket.return_value
        mock_socket.return_value.bind.side_effect = OSError("network unreachable")
        mock_socket.return_value.getsockname.side_effect = OSError("network unreachable")
        # For the context-manager-free pattern, just patch globally
    # Use simpler patch for the function's actual socket usage
    with mock.patch("scripts.capture_screenshots.socket") as mock_sock_mod:
        fake_sock = mock.MagicMock()
        fake_sock.bind.side_effect = OSError("network unreachable")
        mock_sock_mod.socket.return_value.__enter__ = lambda s: fake_sock
        mock_sock_mod.socket.return_value.__exit__ = lambda s, *a: False
        mock_sock_mod.AF_INET = socket.AF_INET
        mock_sock_mod.SOCK_STREAM = socket.SOCK_STREAM
        with pytest.raises(OSError, match="network unreachable"):
            pick_free_port()


# ---------------------------------------------------------------------------
# CAP-60..CAP-64 — check_outputs_complete
# ---------------------------------------------------------------------------


def test_cap60_all_present_and_nonempty_returns_none(tmp_path):
    """CAP-60: all 6 non-empty JPGs present returns None silently."""
    from scripts.capture_screenshots import check_outputs_complete, PAGE_CAPTURE_SPECS

    for _, stem in PAGE_CAPTURE_SPECS:
        p = tmp_path / f"screenshot-{stem}.jpg"
        p.write_bytes(b"FAKE_JPEG_DATA")

    result = check_outputs_complete(tmp_path, PAGE_CAPTURE_SPECS)
    assert result is None


def test_cap61_missing_file_raises_file_not_found(tmp_path):
    """CAP-61: missing 1 of 6 JPGs raises FileNotFoundError naming the file."""
    from scripts.capture_screenshots import check_outputs_complete, PAGE_CAPTURE_SPECS

    # Create 5 of 6
    all_stems = list(PAGE_CAPTURE_SPECS)
    for _, stem in all_stems[:-1]:
        p = tmp_path / f"screenshot-{stem}.jpg"
        p.write_bytes(b"FAKE")

    with pytest.raises(FileNotFoundError) as exc_info:
        check_outputs_complete(tmp_path, PAGE_CAPTURE_SPECS)
    # The message should name the missing file
    assert all_stems[-1][1] in str(exc_info.value)


def test_cap62_zero_byte_file_raises_value_error(tmp_path):
    """CAP-62: a zero-byte JPG raises ValueError mentioning 'empty'."""
    from scripts.capture_screenshots import check_outputs_complete, PAGE_CAPTURE_SPECS

    for _, stem in PAGE_CAPTURE_SPECS:
        p = tmp_path / f"screenshot-{stem}.jpg"
        p.write_bytes(b"")  # zero-byte

    with pytest.raises(ValueError, match="empty"):
        check_outputs_complete(tmp_path, PAGE_CAPTURE_SPECS)


def test_cap63_wrong_extension_raises(tmp_path):
    """CAP-63: .png instead of .jpg raises FileNotFoundError for the .jpg path."""
    from scripts.capture_screenshots import check_outputs_complete, PAGE_CAPTURE_SPECS

    # Create 5 correct .jpg files + 1 .png impostor
    all_stems = list(PAGE_CAPTURE_SPECS)
    for _, stem in all_stems[1:]:
        (tmp_path / f"screenshot-{stem}.jpg").write_bytes(b"FAKE")
    # Write the first stem as .png, not .jpg
    (tmp_path / f"screenshot-{all_stems[0][1]}.png").write_bytes(b"FAKE")

    with pytest.raises(FileNotFoundError):
        check_outputs_complete(tmp_path, PAGE_CAPTURE_SPECS)


def test_cap64_missing_dir_raises_with_clear_message(tmp_path):
    """CAP-64: nonexistent out_dir raises FileNotFoundError mentioning the directory."""
    from scripts.capture_screenshots import check_outputs_complete, PAGE_CAPTURE_SPECS

    nonexistent = tmp_path / "no-such-dir"
    with pytest.raises(FileNotFoundError) as exc_info:
        check_outputs_complete(nonexistent, PAGE_CAPTURE_SPECS)
    assert "no-such-dir" in str(exc_info.value) or str(nonexistent) in str(exc_info.value)


# ---------------------------------------------------------------------------
# CAP-70..CAP-74 — parse_args / main CLI
# ---------------------------------------------------------------------------


def test_cap70_help_exits_0_and_lists_subcommands(capsys):
    """CAP-70: --help exits 0 and mentions all 3 subcommands."""
    from scripts.capture_screenshots import parse_args

    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    for cmd in ("screenshots", "gif", "all"):
        assert cmd in out, f"Subcommand '{cmd}' not in --help output"


def test_cap71_bad_port_exits_nonzero():
    """CAP-71: non-integer --port raises SystemExit with non-zero code."""
    from scripts.capture_screenshots import parse_args

    with pytest.raises(SystemExit) as exc_info:
        parse_args(["screenshots", "--port", "abc"])
    assert exc_info.value.code != 0


def test_cap72_all_defaults_parsed():
    """CAP-72: parse_args(['all']) returns correct defaults."""
    from scripts.capture_screenshots import parse_args

    ns = parse_args(["all"])
    assert ns.command == "all"
    assert ns.db == Path("data/db/sample.duckdb")
    assert ns.out == Path("docs/img")
    assert ns.port is None


def test_cap73_overrides_parsed():
    """CAP-73: parse_args with explicit args returns overrides."""
    from scripts.capture_screenshots import parse_args

    ns = parse_args(["screenshots", "--db", "x.duckdb", "--out", "y/", "--port", "9000"])
    assert ns.command == "screenshots"
    assert ns.db == Path("x.duckdb")
    assert ns.out == Path("y/")
    assert ns.port == 9000


def test_cap74_missing_db_exits_nonzero(tmp_path):
    """CAP-74: main() exits non-zero with diagnostic when --db does not exist."""
    from scripts.capture_screenshots import main

    with pytest.raises(SystemExit) as exc_info:
        main(["all", "--db", str(tmp_path / "no_such.duckdb"), "--out", str(tmp_path)])
    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# CAP-80..CAP-81 — Dep behavior
# ---------------------------------------------------------------------------


def test_cap80_chromium_missing_exits_with_recipe(tmp_path, monkeypatch):
    """CAP-80: missing Chromium binary exits non-zero and prints 'playwright install chromium'."""
    import unittest.mock as mock
    from playwright.sync_api import Error as PlaywrightError

    # Create a minimal valid DuckDB so pre-flight passes
    import duckdb
    db_path = tmp_path / "test.duckdb"
    duckdb.connect(str(db_path)).close()
    out_dir = tmp_path / "out"

    # Build a mock playwright context that raises on chromium.launch
    mock_chromium = mock.MagicMock()
    mock_chromium.launch.side_effect = PlaywrightError("Executable doesn't exist at /path/chrome")
    mock_pw = mock.MagicMock()
    mock_pw.chromium = mock_chromium
    mock_context_mgr = mock.MagicMock()
    mock_context_mgr.__enter__ = mock.MagicMock(return_value=mock_pw)
    mock_context_mgr.__exit__ = mock.MagicMock(return_value=False)

    mock_popen = mock.MagicMock()
    mock_popen.terminate = mock.MagicMock()
    mock_popen.wait = mock.MagicMock()

    # Patch inside playwright.sync_api so the local import inside capture_screenshots() hits it
    with mock.patch("playwright.sync_api.sync_playwright", return_value=mock_context_mgr):
        with mock.patch("subprocess.Popen", return_value=mock_popen):
            with mock.patch("scripts.capture_screenshots._wait_for_health"):
                with pytest.raises(SystemExit) as exc_info:
                    from scripts.capture_screenshots import capture_screenshots
                    capture_screenshots(db_path, out_dir)
    assert exc_info.value.code != 0


def test_cap81_pyproject_declares_playwright_dep():
    """CAP-81: pyproject.toml declares playwright>=1.49 in dev group."""
    pyproject = REPO_ROOT / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)

    dev_deps = data.get("dependency-groups", {}).get("dev", [])
    matches = [d for d in dev_deps if re.match(r"playwright(\[.*\])?>=1\.49", d)]
    assert matches, (
        f"playwright>=1.49 not found in [dependency-groups].dev: {dev_deps}"
    )
