"""Structural guards for the Phase 4 slice-4 documentation artifacts.

These are doc-shape regression tests in the spirit of ``tests/test_ci`` — they do
not test product code, they pin the structure of the README architecture diagram,
``docs/DEMO.md`` walkthrough, and ``docs/public-flip-checklist.md`` so an accidental
deletion or gutting is caught in CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"
DEMO = REPO_ROOT / "docs" / "DEMO.md"
CHECKLIST = REPO_ROOT / "docs" / "public-flip-checklist.md"


@pytest.fixture(scope="session")
def readme_text() -> str:
    return README.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def demo_text() -> str:
    return DEMO.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def checklist_text() -> str:
    return CHECKLIST.read_text(encoding="utf-8")


# --- README architecture diagram -------------------------------------------------


def test_readme_has_mermaid_architecture_diagram(readme_text: str) -> None:
    assert "```mermaid" in readme_text, "README lost its Mermaid diagram fence"
    assert "flowchart" in readme_text, "Mermaid diagram is not a flowchart"


def test_readme_diagram_covers_full_pipeline(readme_text: str) -> None:
    # generator -> parser -> duckdb -> analytics -> retriever/answer -> UI
    for node in ("PARSER", "DUCKDB", "ANALYTICS", "RETRIEVER", "ANSWER", "UI"):
        assert node in readme_text, f"architecture diagram missing the {node} node"


# --- docs/DEMO.md walkthrough ----------------------------------------------------


def test_demo_file_exists(demo_text: str) -> None:
    assert demo_text.strip(), "docs/DEMO.md is empty"


def test_demo_references_the_real_cli_entrypoints(demo_text: str) -> None:
    # the script must use the actual pyproject [project.scripts] names + app path
    assert "uv run generator" in demo_text
    assert "uv run parser" in demo_text
    assert "src/flying_probe_copilot/ui/app.py" in demo_text


def test_demo_walks_all_six_dashboard_pages(demo_text: str) -> None:
    for page in ("Overview", "Yield", "Pareto", "SPC", "Anomalies", "Co-Pilot"):
        assert page in demo_text, f"DEMO.md does not mention the {page} page"


def test_demo_states_synthetic_only(demo_text: str) -> None:
    assert "synthetic" in demo_text.lower()


# --- docs/public-flip-checklist.md ----------------------------------------------


def test_checklist_records_all_six_guardrail_checks_passing(checklist_text: str) -> None:
    # the §8 results table must show six explicit ✅ Pass rows and no failures
    assert checklist_text.count("✅ Pass") >= 6, "fewer than 6 passing guardrail checks"
    assert "❌" not in checklist_text, "checklist records a failing guardrail check"


def test_checklist_references_guardrails_section_8(checklist_text: str) -> None:
    assert "GUARDRAILS.md" in checklist_text
