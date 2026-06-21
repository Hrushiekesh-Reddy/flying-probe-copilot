"""capture_screenshots.py — Headless Playwright screenshot + GIF capture CLI.

Subcommands
-----------
screenshots : Launch Streamlit headless, drive Playwright through all 6 pages,
              write screenshot-{overview,yield,pareto,spc,anomalies,copilot}.jpg
              to --out dir (default docs/img/).
gif         : Stitch existing 6 JPGs from --out dir into demo.gif.
all         : screenshots + gif in one command (default).

Usage
-----
    python scripts/capture_screenshots.py all --db data/db/sample.duckdb

The Co-Pilot page is captured without a live Gemini key: answer_question is
monkeypatched to build_canned_answer via scripts/_capture_app.py shim.
"""

from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence
from urllib.request import urlopen

from PIL import Image

from flying_probe_copilot.rag.answer import Answer

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

CANNED_CITATION_ID = "failure-modes/tombstoning.md#3"

PAGE_CAPTURE_SPECS: tuple[tuple[str, str], ...] = (
    ("Overview", "overview"),
    ("Yield", "yield"),
    ("Failure Pareto", "pareto"),
    ("SPC", "spc"),
    ("Anomalies", "anomalies"),
    ("Co-Pilot", "copilot"),
)

_CANNED_ANSWER_TEXT = (
    "Likely causes of tombstoning: (1) uneven pad heating during reflow causing "
    "one terminal to wet before the other, (2) pad-design imbalance or unequal "
    "copper thermal mass, (3) excess solder paste on one pad pulling the chip "
    "upright via surface tension. The ICT signature is an open across the two "
    "pads — cross-check against the expected refdes value to distinguish "
    "tombstoning from a wrong or missing part."
)

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def build_canned_answer(question: str) -> Answer:
    """Return a grounded canned Answer for the Co-Pilot screenshot.

    The answer is deterministic and grounded entirely in tombstoning.md §3
    (Likely causes + ICT signature).  No LLM call is made.
    """
    return Answer(
        question=question,
        answer_text=_CANNED_ANSWER_TEXT,
        citations=(CANNED_CITATION_ID,),
        refused=False,
        retrieved_ids=(CANNED_CITATION_ID,),
    )


def assemble_gif(
    frames: Sequence[Image.Image],
    out_path,
    frame_duration_ms: int = 2000,
) -> None:
    """Assemble a list of PIL Images into an animated GIF89a file.

    Parameters
    ----------
    frames:
        Sequence of PIL Image objects.  Must be non-empty; all frames must have
        the same dimensions.
    out_path:
        Output path (str or Path).  Parent directory is auto-created.
    frame_duration_ms:
        Duration per frame in milliseconds.  Must be > 0.

    Raises
    ------
    ValueError
        If frames is empty, frame_duration_ms <= 0, or frames have mixed sizes.
    """
    if not frames:
        raise ValueError("assemble_gif: frames list is empty")

    if frame_duration_ms <= 0:
        raise ValueError(
            f"assemble_gif: frame_duration_ms must be > 0, got {frame_duration_ms}"
        )

    # Validate uniform frame size
    first_size = frames[0].size
    for idx, img in enumerate(frames[1:], start=1):
        if img.size != first_size:
            raise ValueError(
                f"assemble_gif: frame size mismatch at index {idx} — "
                f"expected {first_size}, got {img.size}"
            )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy frames to avoid holding open file handles (Windows-critical — BUG-011 pattern)
    safe_frames = [img.copy().convert("RGB") for img in frames]

    safe_frames[0].save(
        out_path,
        format="GIF",
        save_all=True,
        append_images=safe_frames[1:],
        duration=frame_duration_ms,
        loop=0,
        optimize=True,
    )


def pick_free_port() -> int:
    """Return a free ephemeral TCP port on 127.0.0.1.

    Uses the OS's bind-to-0 trick so the selected port is guaranteed free at
    the moment of the call.  Two consecutive calls return different ports
    (the OS advances its ephemeral counter).
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def check_outputs_complete(
    out_dir: Path,
    specs: Sequence[tuple[str, str]],
) -> None:
    """Validate that all expected screenshot files exist and are non-empty.

    Parameters
    ----------
    out_dir:
        Directory that should contain the screenshots.
    specs:
        Sequence of (nav_label, stem) pairs from PAGE_CAPTURE_SPECS.

    Raises
    ------
    FileNotFoundError
        If out_dir does not exist, or if any expected .jpg is missing.
    ValueError
        If any expected .jpg exists but is 0 bytes ("empty screenshot").
    """
    out_dir = Path(out_dir)
    if not out_dir.exists():
        raise FileNotFoundError(
            f"check_outputs_complete: output directory does not exist: {out_dir}"
        )

    for _label, stem in specs:
        expected = out_dir / f"screenshot-{stem}.jpg"
        if not expected.exists():
            raise FileNotFoundError(
                f"check_outputs_complete: missing screenshot: {expected}"
            )
        if expected.stat().st_size == 0:
            raise ValueError(
                f"check_outputs_complete: empty screenshot file: {expected}"
            )


# ---------------------------------------------------------------------------
# Playwright orchestration helpers
# ---------------------------------------------------------------------------


def _wait_for_health(port: int, timeout_s: int = 30) -> None:
    """Poll Streamlit's health endpoint until 200 OK or timeout."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(
        f"Streamlit on :{port} did not become healthy in {timeout_s}s"
    )


def capture_screenshots(db_path, out_dir, port: int | None = None) -> None:
    """Launch Streamlit headless, drive Playwright, write 6 JPGs + demo.gif.

    Parameters
    ----------
    db_path:
        Path to the DuckDB sample database.
    out_dir:
        Output directory for screenshots and gif.
    port:
        TCP port to bind Streamlit on.  If None, a free port is picked.
    """
    from playwright.sync_api import sync_playwright
    from playwright.sync_api import Error as PlaywrightError

    port = port or pick_free_port()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "FPC_DB_PATH": str(db_path)}

    # W-3: use sys.executable -m streamlit so terminate() reaches the actual
    # server process (avoids the uv → python orphan-grandchild issue on Windows).
    cmd = [
        sys.executable, "-m", "streamlit", "run", "scripts/_capture_app.py",
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--logger.level", "error",
    ]

    # W-4: proc is the FIRST statement inside try so finally always runs teardown
    proc = None
    try:
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _wait_for_health(port)

        with sync_playwright() as p:
            # W-10: friendly error on missing Chromium binary
            try:
                browser = p.chromium.launch(headless=True)
            except PlaywrightError as exc:
                if "Executable doesn't exist" in str(exc):
                    raise SystemExit(
                        "Chromium binary missing. Run: uv run playwright install chromium"
                    ) from exc
                raise

            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"http://127.0.0.1:{port}")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(4000)  # initial settle: Streamlit hydrate + first-render Plotly (Overview has 2 charts in st.columns that render late)

            for i, (nav_label, stem) in enumerate(PAGE_CAPTURE_SPECS):
                if i > 0:
                    # B-5: regex name + sidebar-scoped locator to handle emoji prefix
                    nav_link = page.locator("[data-testid='stSidebarNav']").get_by_role(
                        "link", name=re.compile(rf"{re.escape(nav_label)}$")
                    ).first
                    nav_link.click()
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2500)  # Plotly settle (skeleton → real chart)

                if stem == "copilot":
                    page.get_by_test_id("stChatInput").locator("textarea").fill(
                        "what causes tombstoning?"
                    )
                    page.keyboard.press("Enter")
                    page.wait_for_load_state("networkidle")
                    # W-5: wait for assistant chat-message before settling
                    page.wait_for_selector("[data-testid='stChatMessage']", state="visible")
                    page.wait_for_timeout(1500)
                    # B-2: click the "Citations (N)" expander so citation is visible.
                    # Streamlit renders st.expander as <details><summary>, NOT <button> —
                    # use get_by_text on the visible label.
                    page.get_by_text(re.compile(r"Citations \(\d+\)")).first.click()
                    page.wait_for_timeout(500)

                page.screenshot(
                    path=str(out_dir / f"screenshot-{stem}.jpg"),
                    full_page=False,
                    quality=95,  # MD-4: quality=95 for cleaner text
                    type="jpeg",
                )

            browser.close()

        check_outputs_complete(out_dir, PAGE_CAPTURE_SPECS)

    finally:
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for capture_screenshots.

    Returns a Namespace with: command, db (Path), out (Path), port (int|None).
    """
    parser = argparse.ArgumentParser(
        prog="capture_screenshots",
        description="Headless Playwright screenshot + GIF capture for the dashboard.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def _add_common(p):
        p.add_argument(
            "--db",
            type=Path,
            default=Path("data/db/sample.duckdb"),
            help="Path to the DuckDB sample database (default: data/db/sample.duckdb)",
        )
        p.add_argument(
            "--out",
            type=Path,
            default=Path("docs/img"),
            help="Output directory for screenshots / gif (default: docs/img)",
        )
        p.add_argument(
            "--port",
            type=int,
            default=None,
            help="TCP port for Streamlit (default: random free port)",
        )

    _add_common(subparsers.add_parser("screenshots", help="Capture 6 JPG screenshots"))
    _add_common(subparsers.add_parser("gif", help="Assemble existing JPGs into demo.gif"))
    _add_common(subparsers.add_parser("all", help="screenshots + gif (default)"))

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point for capture_screenshots CLI."""
    args = parse_args(argv)

    # Pre-flight: DB existence check for screenshots/all subcommands
    if args.command in ("screenshots", "all"):
        if not args.db.exists():
            print(
                f"ERROR: database not found at {args.db}\n"
                "Generate a sample DB first:\n"
                "  bash scripts/build-portfolio-data.sh\n"
                "or:\n"
                "  uv run generator --board-profile=small --count=30 "
                "--out=data/synthetic/\n"
                "  uv run parser --input=data/synthetic/<run_dir> "
                "--db=data/db/sample.duckdb",
                file=sys.stderr,
            )
            raise SystemExit(1)

    # Pre-flight: --out must be a directory (or not-yet-existing path), not a file
    if args.out.exists() and not args.out.is_dir():
        print(
            f"ERROR: --out {args.out} exists but is not a directory. "
            "Point --out at a directory path.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if args.command in ("screenshots", "all"):
        capture_screenshots(args.db, args.out, port=args.port)

    if args.command in ("gif", "all"):
        # For gif-only: check the JPGs are present before loading
        if args.command == "gif":
            try:
                check_outputs_complete(args.out, PAGE_CAPTURE_SPECS)
            except (FileNotFoundError, ValueError) as exc:
                print(
                    f"ERROR: {exc}\n"
                    "Run `python scripts/capture_screenshots.py screenshots` first "
                    "or use `all` to capture + assemble in one step.",
                    file=sys.stderr,
                )
                raise SystemExit(1) from exc

        frames = [
            Image.open(args.out / f"screenshot-{stem}.jpg").copy()
            for _, stem in PAGE_CAPTURE_SPECS
        ]
        assemble_gif(frames, args.out / "demo.gif", frame_duration_ms=2000)


if __name__ == "__main__":
    main()
