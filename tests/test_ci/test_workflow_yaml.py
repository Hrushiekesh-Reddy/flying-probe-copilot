"""CI workflow YAML + pyproject.toml shape tests.

Tests: Section A (1) + Section B ci.yml (25) + Section C screenshots.yml (30)
       + Section D pyproject ruff config (17) + Section E cross-workflow (11)
       = 84 total cases (E-08 dropped per W-3/MD-7 — setup-python removed from workflows).

All workflow YAML is loaded via session-scoped fixtures in conftest.py.
Tests treat loaded dicts as READ-ONLY — never call .update(), .pop(), or del on them.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Section A — Sanity / env guard
# ---------------------------------------------------------------------------


def test_workflow_dir_resolves_under_repo_root(_workflow_dir):
    """A.1: _workflow_dir is a directory and repo root contains pyproject.toml."""
    assert _workflow_dir.is_dir(), f"Workflow dir not found: {_workflow_dir}"
    assert (REPO_ROOT / "pyproject.toml").exists(), "pyproject.toml not found at repo root"


# ---------------------------------------------------------------------------
# Section B — .github/workflows/ci.yml
# ---------------------------------------------------------------------------


def test_ci_yml_exists(_workflow_dir):
    """B-01: ci.yml is a file."""
    assert (_workflow_dir / "ci.yml").is_file()


def test_ci_yml_parses(_load_yaml):
    """B-02: yaml.safe_load returns a dict with name, on, jobs; name == 'ci'."""
    data = _load_yaml("ci.yml")
    assert isinstance(data, dict)
    assert set(data) >= {"name", "on", "jobs"}
    assert data["name"] == "ci"


def test_ci_yml_triggers_on_pull_request(_load_yaml):
    """B-03: on.pull_request is defined."""
    data = _load_yaml("ci.yml")
    assert "pull_request" in data["on"]


def test_ci_yml_targets_dev_and_main(_load_yaml):
    """B-04: on.pull_request.branches contains both 'dev' and 'main'."""
    data = _load_yaml("ci.yml")
    branches = set(data["on"]["pull_request"]["branches"])
    assert {"dev", "main"} <= branches


def test_ci_yml_paths_ignore_docs(_load_yaml):
    """B-05: on.pull_request.paths-ignore contains 'docs/**', '**/*.md', 'notebooks/**', '.claude/**'."""
    data = _load_yaml("ci.yml")
    paths_ignore = data["on"]["pull_request"]["paths-ignore"]
    assert "docs/**" in paths_ignore
    assert "**/*.md" in paths_ignore
    assert "notebooks/**" in paths_ignore
    assert ".claude/**" in paths_ignore


def test_ci_yml_has_lint_job(_load_yaml):
    """B-06: jobs.lint exists with runs-on and steps."""
    data = _load_yaml("ci.yml")
    assert "lint" in data["jobs"]
    assert "runs-on" in data["jobs"]["lint"]
    assert "steps" in data["jobs"]["lint"]


def test_ci_yml_has_tests_job(_load_yaml):
    """B-07: jobs.tests exists with runs-on and steps."""
    data = _load_yaml("ci.yml")
    assert "tests" in data["jobs"]
    assert "runs-on" in data["jobs"]["tests"]
    assert "steps" in data["jobs"]["tests"]


def test_ci_yml_lint_job_runs_ruff_check_and_format(_load_yaml):
    """B-08: lint job has ruff check step and ruff format --check step."""
    data = _load_yaml("ci.yml")
    steps = data["jobs"]["lint"]["steps"]
    run_texts = " ".join(s.get("run", "") for s in steps)
    assert "ruff check" in run_texts, "ruff check not found in lint job steps"
    assert "ruff format --check" in run_texts, "ruff format --check not found in lint job steps"


def test_ci_yml_tests_job_runs_pytest_with_coverage(_load_yaml):
    """B-09: tests job runs pytest with --cov=src/flying_probe_copilot."""
    data = _load_yaml("ci.yml")
    steps = data["jobs"]["tests"]["steps"]
    for step in steps:
        run = step.get("run", "")
        if "pytest" in run and "--cov=src/flying_probe_copilot" in run:
            return
    pytest.fail("No pytest step with --cov=src/flying_probe_copilot found in tests job")


def test_ci_yml_uses_python_311(_load_yaml):
    """B-10: setup-uv step uses python-version '3.11' (string, not float)."""
    data = _load_yaml("ci.yml")
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            uses = step.get("uses", "")
            if uses.startswith("astral-sh/setup-uv"):
                w = step.get("with", {})
                if "python-version" in w:
                    v = w["python-version"]
                    assert isinstance(v, str), f"python-version is {type(v).__name__}, expected str"
                    assert v == "3.11", f"python-version is '{v}', expected '3.11'"
                    assert not isinstance(v, (int, float)), "python-version must be a string"


def test_ci_yml_concurrency_cancel_in_progress(_load_yaml):
    """B-11: concurrency.cancel-in-progress is True and group references github.workflow + github.ref."""
    data = _load_yaml("ci.yml")
    conc = data["concurrency"]
    assert conc.get("cancel-in-progress") is True
    group = conc.get("group", "")
    assert "github.workflow" in group, f"concurrency.group missing 'github.workflow': {group}"
    assert "github.ref" in group, f"concurrency.group missing 'github.ref': {group}"


def test_ci_yml_permissions_contents_read(_load_yaml):
    """B-12: permissions.contents == 'read'."""
    data = _load_yaml("ci.yml")
    assert data["permissions"]["contents"] == "read"


def test_ci_yml_both_jobs_use_ubuntu_latest(_load_yaml):
    """B-13: every job uses runs-on: ubuntu-latest."""
    data = _load_yaml("ci.yml")
    for job_name, job in data["jobs"].items():
        assert job.get("runs-on") == "ubuntu-latest", (
            f"Job '{job_name}' uses runs-on '{job.get('runs-on')}', expected 'ubuntu-latest'"
        )


def test_ci_yml_both_jobs_have_timeout_minutes(_load_yaml):
    """B-14: every job declares timeout-minutes as a positive int."""
    data = _load_yaml("ci.yml")
    for job_name, job in data["jobs"].items():
        t = job.get("timeout-minutes")
        assert isinstance(t, int) and t > 0, f"Job '{job_name}' has invalid timeout-minutes: {t!r}"


def test_ci_yml_tests_job_timeout_at_least_10(_load_yaml):
    """B-15: tests job timeout-minutes >= 10."""
    data = _load_yaml("ci.yml")
    assert data["jobs"]["tests"]["timeout-minutes"] >= 10


def test_ci_yml_lint_job_timeout_at_most_10(_load_yaml):
    """B-16: lint job timeout-minutes <= 10."""
    data = _load_yaml("ci.yml")
    assert data["jobs"]["lint"]["timeout-minutes"] <= 10


def test_ci_yml_uses_actions_checkout_v4(_load_yaml):
    """B-17: every actions/checkout step pins @v4."""
    data = _load_yaml("ci.yml")
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            uses = step.get("uses", "")
            if uses.startswith("actions/checkout"):
                assert uses.endswith("@v4"), f"checkout not pinned to @v4: {uses}"


def test_ci_yml_installs_uv_via_setup_uv_action(_load_yaml):
    """B-18: each job has a setup-uv step with @v >= 6 (e.g., @v8)."""
    data = _load_yaml("ci.yml")
    for job_name, job in data["jobs"].items():
        found = False
        for step in job.get("steps", []):
            uses = step.get("uses", "")
            if uses.startswith("astral-sh/setup-uv"):
                # Assert version suffix matches @v[6+]
                match = re.search(r"@v(\d+)", uses)
                assert match, f"setup-uv in '{job_name}' has no @vN suffix: {uses}"
                assert int(match.group(1)) >= 6, (
                    f"setup-uv in '{job_name}' is {uses}, expected @v6 or higher"
                )
                found = True
        assert found, f"Job '{job_name}' has no astral-sh/setup-uv step"


def test_ci_yml_uv_sync_uses_frozen_and_all_groups(_load_yaml):
    """B-19: each job has a uv sync step with --frozen AND --all-groups."""
    data = _load_yaml("ci.yml")
    for job_name, job in data["jobs"].items():
        found = False
        for step in job.get("steps", []):
            run = step.get("run", "")
            if "uv sync" in run and "--frozen" in run and "--all-groups" in run:
                found = True
        assert found, f"Job '{job_name}' missing 'uv sync --frozen --all-groups'"


def test_ci_yml_no_google_api_key_reference(_load_yaml_text):
    """B-20: ci.yml raw text does not contain GOOGLE_API_KEY."""
    text = _load_yaml_text("ci.yml")
    assert "GOOGLE_API_KEY" not in text


def test_ci_yml_no_anthropic_api_key_reference(_load_yaml_text):
    """B-21: ci.yml raw text does not contain ANTHROPIC_API_KEY."""
    text = _load_yaml_text("ci.yml")
    assert "ANTHROPIC_API_KEY" not in text


def test_ci_yml_no_secrets_block_at_all(_load_yaml_text):
    """B-22: ci.yml raw text does not contain 'secrets.'."""
    text = _load_yaml_text("ci.yml")
    assert "secrets." not in text


def test_ci_yml_no_push_trigger(_load_yaml):
    """B-23: on.push is NOT present."""
    data = _load_yaml("ci.yml")
    assert "push" not in data["on"]


def test_ci_yml_lint_job_uses_github_output_format(_load_yaml):
    """B-24: lint job has a ruff check step with --output-format=github."""
    data = _load_yaml("ci.yml")
    steps = data["jobs"]["lint"]["steps"]
    run_texts = " ".join(s.get("run", "") for s in steps)
    assert "--output-format=github" in run_texts


def test_ci_yml_tests_job_runs_pytest_quiet(_load_yaml):
    """B-25: tests job pytest step uses -q (or --quiet)."""
    data = _load_yaml("ci.yml")
    steps = data["jobs"]["tests"]["steps"]
    for step in steps:
        run = step.get("run", "")
        if "pytest" in run and ("-q" in run or "--quiet" in run):
            return
    pytest.fail("No pytest step with -q/--quiet found in tests job")


# ---------------------------------------------------------------------------
# Section C — .github/workflows/screenshots.yml
# ---------------------------------------------------------------------------


def test_screenshots_yml_exists(_workflow_dir):
    """C-01: screenshots.yml is a file."""
    assert (_workflow_dir / "screenshots.yml").is_file()


def test_screenshots_yml_parses(_load_yaml):
    """C-02: yaml.safe_load returns dict with name, on, jobs; name == 'screenshots'."""
    data = _load_yaml("screenshots.yml")
    assert isinstance(data, dict)
    assert set(data) >= {"name", "on", "jobs"}
    assert data["name"] == "screenshots"


def test_screenshots_yml_triggers_on_pull_request_to_dev_and_main(_load_yaml):
    """C-03: on.pull_request.branches contains 'dev' and 'main'."""
    data = _load_yaml("screenshots.yml")
    branches = set(data["on"]["pull_request"]["branches"])
    assert {"dev", "main"} <= branches


def test_screenshots_yml_paths_filter_covers_ui_analytics_kb_scripts(_load_yaml):
    """C-04: on.pull_request.paths is a superset of the 5 required globs."""
    data = _load_yaml("screenshots.yml")
    paths = set(data["on"]["pull_request"]["paths"])
    expected = {
        "src/flying_probe_copilot/ui/**",
        "src/flying_probe_copilot/analytics/**",
        "docs/knowledge-base/**",
        "scripts/capture_screenshots.py",
        "scripts/_capture_app.py",
    }
    assert expected <= paths, f"Missing paths: {expected - paths}"


def test_screenshots_yml_paths_filter_excludes_docs_md(_load_yaml):
    """C-05: path list does NOT contain 'docs/**' or '**/*.md' (those over-trigger)."""
    data = _load_yaml("screenshots.yml")
    paths = data["on"]["pull_request"]["paths"]
    assert "docs/**" not in paths
    assert "**/*.md" not in paths


def test_screenshots_yml_has_capture_job(_load_yaml):
    """C-06: jobs.capture exists with runs-on, steps, and timeout-minutes."""
    data = _load_yaml("screenshots.yml")
    assert "capture" in data["jobs"]
    job = data["jobs"]["capture"]
    assert "runs-on" in job
    assert "steps" in job
    assert "timeout-minutes" in job


def test_screenshots_yml_capture_job_runs_on_ubuntu_latest(_load_yaml):
    """C-07: jobs.capture.runs-on == 'ubuntu-latest'."""
    data = _load_yaml("screenshots.yml")
    assert data["jobs"]["capture"]["runs-on"] == "ubuntu-latest"


def test_screenshots_yml_timeout_minutes_15(_load_yaml):
    """C-08: jobs.capture.timeout-minutes == 15 (exact)."""
    data = _load_yaml("screenshots.yml")
    assert data["jobs"]["capture"]["timeout-minutes"] == 15


def test_screenshots_yml_uses_actions_checkout_v4(_load_yaml):
    """C-09: every actions/checkout step pins @v4."""
    data = _load_yaml("screenshots.yml")
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            uses = step.get("uses", "")
            if uses.startswith("actions/checkout"):
                assert uses.endswith("@v4"), f"checkout not pinned to @v4: {uses}"


def test_screenshots_yml_uses_setup_uv_v6_or_higher(_load_yaml):
    """C-10: setup-uv step uses @v6 or higher (e.g., @v8)."""
    data = _load_yaml("screenshots.yml")
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            uses = step.get("uses", "")
            if uses.startswith("astral-sh/setup-uv"):
                match = re.search(r"@v(\d+)", uses)
                assert match, f"setup-uv has no @vN suffix: {uses}"
                assert int(match.group(1)) >= 6, f"setup-uv is {uses}, expected @v6 or higher"


def test_screenshots_yml_setup_uv_has_python_version_311(_load_yaml):
    """C-11: setup-uv step specifies python-version '3.11' (string, not float)."""
    data = _load_yaml("screenshots.yml")
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            uses = step.get("uses", "")
            if uses.startswith("astral-sh/setup-uv"):
                w = step.get("with", {})
                if "python-version" in w:
                    v = w["python-version"]
                    assert isinstance(v, str), f"python-version is {type(v).__name__}, expected str"
                    assert v == "3.11"
                    assert not isinstance(v, (int, float))


def test_screenshots_yml_installs_playwright_with_deps_chromium(_load_yaml):
    """C-12: a run step contains 'playwright install --with-deps chromium'."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]
    run_texts = " ".join(s.get("run", "") for s in steps)
    assert "playwright install --with-deps chromium" in run_texts


def test_screenshots_yml_uv_sync_uses_frozen_and_all_groups(_load_yaml):
    """C-13: capture job has uv sync with --frozen AND --all-groups."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]
    found = False
    for step in steps:
        run = step.get("run", "")
        if "uv sync" in run and "--frozen" in run and "--all-groups" in run:
            found = True
    assert found, "No 'uv sync --frozen --all-groups' in capture job"


def test_screenshots_yml_uses_actions_cache_v4_for_sample_db(_load_yaml):
    """C-14: a step uses actions/cache@v4 with path containing data/db/sample.duckdb."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]
    for step in steps:
        uses = step.get("uses", "")
        if uses.startswith("actions/cache"):
            assert uses.endswith("@v4"), f"actions/cache not pinned to @v4: {uses}"
            cache_path = step.get("with", {}).get("path", "")
            assert "data/db/sample.duckdb" in cache_path
            return
    pytest.fail("No actions/cache step found in capture job")


def test_screenshots_yml_cache_key_uses_hashFiles(_load_yaml):
    """C-15: cache step's key references hashFiles(...)."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]
    for step in steps:
        if step.get("uses", "").startswith("actions/cache"):
            key = step["with"]["key"]
            assert re.search(r"hashFiles\(", key), f"cache key missing hashFiles: {key}"
            return
    pytest.fail("No actions/cache step found")


def test_screenshots_yml_cache_key_includes_generator_parser_buildscript(_load_yaml):
    """C-16: cache key hashFiles includes generator/**, parser/**, build-portfolio-data.sh, and cli.py anchors."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]
    for step in steps:
        if step.get("uses", "").startswith("actions/cache"):
            key = step["with"]["key"]
            assert "generator/**" in key, f"cache key missing generator/**: {key}"
            assert "parser/**" in key, f"cache key missing parser/**: {key}"
            assert "build-portfolio-data.sh" in key, (
                f"cache key missing build-portfolio-data.sh: {key}"
            )
            assert "cli.py" in key, f"cache key missing cli.py anchor: {key}"
            return
    pytest.fail("No actions/cache step found")


def test_screenshots_yml_cache_key_includes_uv_lock(_load_yaml):
    """C-17: cache key references uv.lock."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]
    for step in steps:
        if step.get("uses", "").startswith("actions/cache"):
            key = step["with"]["key"]
            assert "uv.lock" in key, f"cache key missing uv.lock: {key}"
            return
    pytest.fail("No actions/cache step found")


def test_screenshots_yml_build_db_step_runs_on_cache_miss_only(_load_yaml):
    """C-18: build sample DB step has if: referencing cache-hit != 'true'."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]
    for step in steps:
        run = step.get("run", "")
        if "build-portfolio-data.sh" in run:
            condition = step.get("if", "")
            assert "cache-hit" in condition, f"if condition missing cache-hit: {condition}"
            assert "!= 'true'" in condition or '!= "true"' in condition, (
                f"if condition missing != 'true': {condition}"
            )
            return
    pytest.fail("No build-portfolio-data.sh step found in capture job")


def test_screenshots_yml_build_db_step_references_cache_step_id(_load_yaml):
    """C-19: build step's if: references steps.<cache-id>.outputs.cache-hit."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]

    # Find the cache step and read its id
    cache_step = None
    for step in steps:
        if step.get("uses", "").startswith("actions/cache"):
            cache_step = step
            break
    assert cache_step is not None, "No actions/cache step found in capture job"
    assert "id" in cache_step, (
        "actions/cache step has no 'id' field — build step cannot reference its output"
    )
    cache_id = cache_step["id"]

    # Find the build step and verify it references the cache id
    for step in steps:
        run = step.get("run", "")
        if "build-portfolio-data.sh" in run:
            condition = step.get("if", "")
            assert f"steps.{cache_id}.outputs.cache-hit" in condition, (
                f"build step if: '{condition}' does not reference steps.{cache_id}.outputs.cache-hit"
            )
            return
    pytest.fail("No build-portfolio-data.sh step found in capture job")


def test_screenshots_yml_invokes_capture_script_all_mode(_load_yaml):
    """C-20: a run step invokes 'scripts/capture_screenshots.py all'."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]
    run_texts = " ".join(s.get("run", "") for s in steps)
    assert "capture_screenshots.py all" in run_texts


def test_screenshots_yml_capture_script_uses_out_flag(_load_yaml):
    """C-21: capture script invocation includes --out docs/img-ci/."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]
    run_texts = " ".join(s.get("run", "") for s in steps)
    assert "--out docs/img-ci" in run_texts


def test_screenshots_yml_uploads_artifact_with_retention_14(_load_yaml):
    """C-22: actions/upload-artifact@v4 step has retention-days: 14."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]
    for step in steps:
        uses = step.get("uses", "")
        if uses.startswith("actions/upload-artifact"):
            assert uses.endswith("@v4"), f"upload-artifact not @v4: {uses}"
            assert step["with"]["retention-days"] == 14
            return
    pytest.fail("No actions/upload-artifact step found in capture job")


def test_screenshots_yml_upload_artifact_name_is_descriptive(_load_yaml):
    """C-23: artifact name == 'recaptured-dashboard-screenshots'."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]
    for step in steps:
        if step.get("uses", "").startswith("actions/upload-artifact"):
            assert step["with"]["name"] == "recaptured-dashboard-screenshots"
            return
    pytest.fail("No actions/upload-artifact step found")


def test_screenshots_yml_upload_artifact_path_is_docs_img_ci(_load_yaml):
    """C-24: artifact upload path is docs/img-ci/."""
    data = _load_yaml("screenshots.yml")
    steps = data["jobs"]["capture"]["steps"]
    for step in steps:
        if step.get("uses", "").startswith("actions/upload-artifact"):
            assert "docs/img-ci" in step["with"]["path"]
            return
    pytest.fail("No actions/upload-artifact step found")


def test_screenshots_yml_concurrency_cancel_in_progress(_load_yaml):
    """C-25: concurrency.cancel-in-progress is True and group references github.workflow + github.ref."""
    data = _load_yaml("screenshots.yml")
    conc = data["concurrency"]
    assert conc.get("cancel-in-progress") is True
    group = conc.get("group", "")
    assert "github.workflow" in group
    assert "github.ref" in group


def test_screenshots_yml_permissions_contents_read(_load_yaml):
    """C-26: permissions.contents == 'read'."""
    data = _load_yaml("screenshots.yml")
    assert data["permissions"]["contents"] == "read"


def test_screenshots_yml_no_google_api_key_reference(_load_yaml_text):
    """C-27: screenshots.yml raw text does not contain GOOGLE_API_KEY."""
    text = _load_yaml_text("screenshots.yml")
    assert "GOOGLE_API_KEY" not in text


def test_screenshots_yml_no_anthropic_api_key_reference(_load_yaml_text):
    """C-28: screenshots.yml raw text does not contain ANTHROPIC_API_KEY."""
    text = _load_yaml_text("screenshots.yml")
    assert "ANTHROPIC_API_KEY" not in text


def test_screenshots_yml_no_push_trigger(_load_yaml):
    """C-29: on.push is NOT present in screenshots.yml."""
    data = _load_yaml("screenshots.yml")
    assert "push" not in data["on"]


def test_screenshots_yml_no_secrets_block(_load_yaml_text):
    """C-30: 'secrets.' substring absent from screenshots.yml."""
    text = _load_yaml_text("screenshots.yml")
    assert "secrets." not in text


# ---------------------------------------------------------------------------
# Section D — pyproject.toml ruff config
# ---------------------------------------------------------------------------


def test_pyproject_declares_ruff_dev_dep(_pyproject):
    """D-01: [dependency-groups].dev has a 'ruff>=...' entry."""
    dev = _pyproject["dependency-groups"]["dev"]
    assert any(
        s.startswith("ruff") and any(op in s for op in (">=", "~=", "==", "^")) for s in dev
    ), f"No 'ruff>=...' in dev deps: {dev}"


def test_pyproject_ruff_dev_dep_floor_at_least_0_6(_pyproject):
    """D-02: ruff dev dep lower bound >= 0.6 (regex version compare)."""
    dev = _pyproject["dependency-groups"]["dev"]
    ruff_entry = next((s for s in dev if s.startswith("ruff")), None)
    assert ruff_entry is not None, "No ruff entry in dev deps"
    # Extract version number from e.g. "ruff>=0.6"
    match = re.search(r">=(\d+\.\d+)", ruff_entry)
    assert match, f"Cannot parse version from: {ruff_entry}"
    version_str = match.group(1)
    assert re.match(r"^\d+(\.\d+)*$", version_str), f"Version not numeric: {version_str}"
    # Compare as tuple of ints
    parts = tuple(int(x) for x in version_str.split("."))
    floor = (0, 6)
    assert parts >= floor, f"ruff floor {parts} < required {floor}"


def test_pyproject_ruff_section_exists(_pyproject):
    """D-03: [tool.ruff] table is present."""
    assert "ruff" in _pyproject.get("tool", {}), "No [tool.ruff] section in pyproject.toml"
    assert isinstance(_pyproject["tool"]["ruff"], dict)


def test_pyproject_ruff_target_version_py311(_pyproject):
    """D-04: [tool.ruff].target-version == 'py311'."""
    assert _pyproject["tool"]["ruff"]["target-version"] == "py311"


def test_pyproject_ruff_line_length_set(_pyproject):
    """D-05: [tool.ruff].line-length is a positive int between 88 and 120."""
    ll = _pyproject["tool"]["ruff"]["line-length"]
    assert isinstance(ll, int) and ll > 0
    assert 88 <= ll <= 120, f"line-length {ll} outside ergonomic range [88, 120]"


def test_pyproject_ruff_extend_exclude_covers_data_docs_notebooks(_pyproject):
    """D-06: extend-exclude contains 'data', 'docs', 'notebooks'."""
    excl = set(_pyproject["tool"]["ruff"].get("extend-exclude", []))
    assert {"data", "docs", "notebooks"} <= excl


def test_pyproject_ruff_extend_exclude_covers_claude_dir(_pyproject):
    """D-07: extend-exclude contains '.claude'."""
    excl = set(_pyproject["tool"]["ruff"].get("extend-exclude", []))
    assert ".claude" in excl


def test_pyproject_ruff_extend_exclude_covers_scripts(_pyproject):
    """D-08 (was D-16): extend-exclude contains 'scripts' (scripts/ is read-only this slice)."""
    excl = set(_pyproject["tool"]["ruff"].get("extend-exclude", []))
    assert "scripts" in excl, f"'scripts' not in extend-exclude: {excl}"


def test_pyproject_ruff_lint_section_exists(_pyproject):
    """D-08b: [tool.ruff.lint] table exists."""
    assert "lint" in _pyproject["tool"]["ruff"], "No [tool.ruff.lint] section"
    assert isinstance(_pyproject["tool"]["ruff"]["lint"], dict)


def test_pyproject_ruff_lint_select_contains_core_rules(_pyproject):
    """D-09: [tool.ruff.lint].select contains E, F, W, I."""
    select = set(_pyproject["tool"]["ruff"]["lint"]["select"])
    assert {"E", "F", "W", "I"} <= select


def test_pyproject_ruff_lint_select_excludes_unknown_codes(_pyproject):
    """D-10: all select entries match ^[A-Z]+[0-9]*$."""
    select = _pyproject["tool"]["ruff"]["lint"]["select"]
    for code in select:
        assert re.match(r"^[A-Z]+[0-9]*$", code), f"Invalid rule code: {code!r}"


def test_pyproject_ruff_tests_have_per_file_ignores(_pyproject):
    """D-11: per-file-ignores for 'tests/**/*.py' includes 'E501'."""
    pfi = _pyproject["tool"]["ruff"]["lint"].get("per-file-ignores", {})
    assert "tests/**/*.py" in pfi, f"'tests/**/*.py' key not found in per-file-ignores: {pfi}"
    assert "E501" in pfi["tests/**/*.py"]


def test_pyproject_ruff_tests_per_file_ignores_includes_f401(_pyproject):
    """D-12: per-file-ignores for 'tests/**/*.py' includes 'F401'."""
    pfi = _pyproject["tool"]["ruff"]["lint"].get("per-file-ignores", {})
    assert "tests/**/*.py" in pfi
    assert "F401" in pfi["tests/**/*.py"]


def test_pyproject_ruff_format_block_exists(_pyproject):
    """D-13: [tool.ruff.format] table is present (can be empty for defaults)."""
    assert "format" in _pyproject["tool"]["ruff"], "No [tool.ruff.format] section"
    assert isinstance(_pyproject["tool"]["ruff"]["format"], dict)


def test_pyproject_dev_deps_remain_alphabetized(_pyproject):
    """D-14: [dependency-groups].dev list is sorted alphabetically."""
    dev = _pyproject["dependency-groups"]["dev"]
    assert dev == sorted(dev), f"dev deps not alphabetized: {dev}"


def test_pyproject_no_mypy_dev_dep_added(_pyproject):
    """D-15: no 'mypy' entry in [dependency-groups].dev."""
    dev = _pyproject["dependency-groups"]["dev"]
    assert not any(s.startswith("mypy") for s in dev), "mypy found in dev deps (D4: ruff only)"


def test_pyproject_project_requires_python_311_unchanged(_pyproject):
    """D-16: project.requires-python is still '>=3.11'."""
    assert _pyproject["project"]["requires-python"] == ">=3.11"


def test_pyproject_existing_main_deps_unchanged(_pyproject):
    """D-17: all 10 baseline main dependencies are still present."""
    deps = _pyproject["project"]["dependencies"]
    required_prefixes = [
        "duckdb",
        "chromadb",
        "sentence-transformers",
        "rank-bm25",
        "google-genai",
        "streamlit",
        "plotly",
        "pydantic",
        "pyyaml",
        "python-dotenv",
    ]
    for prefix in required_prefixes:
        assert any(d.startswith(prefix) for d in deps), (
            f"Main dep starting with '{prefix}' not found in project.dependencies"
        )


# ---------------------------------------------------------------------------
# Section E — Cross-workflow tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("secret_name", ["GOOGLE_API_KEY", "ANTHROPIC_API_KEY"])
@pytest.mark.parametrize("workflow_name", ["ci.yml", "screenshots.yml"])
def test_no_workflow_uses_secret(_load_yaml_text, workflow_name, secret_name):
    """E-01/E-02: neither workflow references GOOGLE_API_KEY or ANTHROPIC_API_KEY."""
    text = _load_yaml_text(workflow_name)
    assert secret_name not in text, f"{workflow_name} references {secret_name}"


@pytest.mark.parametrize("workflow_name", ["ci.yml", "screenshots.yml"])
def test_no_workflow_uses_any_secrets_substring(_load_yaml_text, workflow_name):
    """E-03: 'secrets.' does not appear in either workflow."""
    text = _load_yaml_text(workflow_name)
    assert "secrets." not in text, f"{workflow_name} contains 'secrets.' reference"


@pytest.mark.parametrize("workflow_name", ["ci.yml", "screenshots.yml"])
def test_both_workflows_have_concurrency_block(_load_yaml, workflow_name):
    """E-04: both workflows declare concurrency with cancel-in-progress."""
    data = _load_yaml(workflow_name)
    assert "concurrency" in data, f"{workflow_name} missing top-level concurrency block"
    assert data["concurrency"].get("cancel-in-progress") is True


@pytest.mark.parametrize("workflow_name", ["ci.yml", "screenshots.yml"])
def test_both_workflows_have_permissions_contents_read(_load_yaml, workflow_name):
    """E-05: both workflows have permissions.contents == 'read'."""
    data = _load_yaml(workflow_name)
    assert data.get("permissions", {}).get("contents") == "read"


@pytest.mark.parametrize("workflow_name", ["ci.yml", "screenshots.yml"])
def test_both_workflows_pin_jobs_to_ubuntu_latest(_load_yaml, workflow_name):
    """E-06: every job in every workflow uses runs-on: ubuntu-latest."""
    data = _load_yaml(workflow_name)
    for job_name, job in data["jobs"].items():
        assert job.get("runs-on") == "ubuntu-latest", (
            f"{workflow_name} job '{job_name}' uses '{job.get('runs-on')}'"
        )


@pytest.mark.parametrize("workflow_name", ["ci.yml", "screenshots.yml"])
def test_both_workflows_use_actions_checkout_v4(_load_yaml, workflow_name):
    """E-07: every actions/checkout step in every workflow pins @v4."""
    data = _load_yaml(workflow_name)
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            uses = step.get("uses", "")
            if uses.startswith("actions/checkout"):
                assert uses.endswith("@v4"), f"{workflow_name}: checkout not pinned to @v4: {uses}"


@pytest.mark.parametrize("workflow_name", ["ci.yml", "screenshots.yml"])
def test_both_workflows_set_python_version_as_string_not_float(_load_yaml, workflow_name):
    """E-09: python-version is always string '3.11', never float 3.11."""
    data = _load_yaml(workflow_name)
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            uses = step.get("uses", "")
            if uses.startswith("astral-sh/setup-uv"):
                w = step.get("with", {})
                if "python-version" in w:
                    v = w["python-version"]
                    assert isinstance(v, str), (
                        f"{workflow_name}: python-version is {type(v).__name__}, not str"
                    )
                    assert v == "3.11"
                    assert not isinstance(v, (int, float))


@pytest.mark.parametrize("workflow_name", ["ci.yml", "screenshots.yml"])
def test_both_workflows_have_top_level_name_field(_load_yaml, workflow_name):
    """E-10: both workflows have a non-empty 'name' field."""
    data = _load_yaml(workflow_name)
    assert isinstance(data.get("name"), str) and data["name"], (
        f"{workflow_name} missing non-empty 'name' field"
    )


def test_workflow_file_count_is_exactly_two(_workflow_dir):
    """E-11: .github/workflows/ contains exactly 2 *.yml files: ci.yml and screenshots.yml.

    Any additional workflow file requires explicit owner sign-off at Decision Gate.
    """
    yml_files = set(p.name for p in _workflow_dir.glob("*.yml"))
    assert yml_files == {"ci.yml", "screenshots.yml"}, (
        f"Expected exactly {{ci.yml, screenshots.yml}}, found: {yml_files}"
    )
