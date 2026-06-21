"""Phase 3 evaluation dataset — 10 representative root-cause questions.

Each entry maps a natural-language question to the KB-relative doc_id of the
failure-mode document that should ground the answer. Used by both the offline
citation-pattern test and the env-gated live ≥8/10 accuracy test in
``test_eval.py``. Keep in sync with ``docs/eval/phase3-eval-questions.md``.
"""

from __future__ import annotations

# (question, expected_doc_id) — expected_doc_id is the POSIX path relative to
# docs/knowledge-base/ (matches the slice-1 kb_loader chunk_id prefix).
EVAL_QUESTIONS: list[tuple[str, str]] = [
    (
        "Why would a chip component stand up on one end during reflow?",
        "failure-modes/tombstoning.md",
    ),
    (
        "A part lifted on one end leaving one terminal unconnected after reflow - name the defect.",
        "failure-modes/tombstoning.md",
    ),
    (
        "What causes two nets that should be isolated to read as connected?",
        "failure-modes/shorts.md",
    ),
    (
        "Adjacent fine-pitch leads are bridged by excess solder - what is this called?",
        "failure-modes/shorts.md",
    ),
    (
        "A resistor measures outside its tolerance limits - what should I check?",
        "failure-modes/out-of-tolerance-analog.md",
    ),
    (
        "Why is there no continuity where the design expects a connection?",
        "failure-modes/opens.md",
    ),
    (
        "A joint looks dull and grainy and fails intermittently with temperature - what is it?",
        "failure-modes/cold-solder-joint.md",
    ),
    (
        "A polarized capacitor appears installed backwards - what failure mode is this?",
        "failure-modes/component-misorientation.md",
    ),
    (
        "The footprint has bare pads where a part should be - what happened?",
        "failure-modes/missing-component.md",
    ),
    (
        "A solder joint has too little fillet and is electrically marginal - what is the defect?",
        "failure-modes/insufficient-solder.md",
    ),
]
