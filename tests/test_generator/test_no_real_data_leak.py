"""Guardrail: generated logs must contain no sentinel strings.

Phase 1a Step H1 — RED phase. Sentinels match what a careless test could
accidentally use to mimic real data: "customer", "confidential", "proprietary".
Per ``docs/GUARDRAILS.md``.
"""

from __future__ import annotations


def _invoke(argv):
    from flying_probe_copilot.generator.cli import main

    try:
        return main(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0


SENTINELS = ("customer", "confidential", "proprietary")


def test_generated_logs_contain_no_sentinel_strings(tmp_path):
    rc = _invoke(
        ["--board-profile=small", "--count=5", f"--out={tmp_path}", "--seed=42"]
    )
    assert rc == 0
    run = next(tmp_path.iterdir())
    for log_path in (run / "logs").glob("*.log"):
        text = log_path.read_text(encoding="cp1252").lower()
        for sentinel in SENTINELS:
            assert sentinel not in text, (
                f"sentinel {sentinel!r} found in {log_path.name}"
            )
    csv_text = (run / "results.csv").read_text(encoding="utf-8").lower()
    json_text = (run / "results.json").read_text(encoding="utf-8").lower()
    for sentinel in SENTINELS:
        assert sentinel not in csv_text, f"sentinel {sentinel!r} in results.csv"
        assert sentinel not in json_text, f"sentinel {sentinel!r} in results.json"
