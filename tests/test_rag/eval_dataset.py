"""Phase 3 evaluation dataset — 15 representative root-cause questions.

Each entry maps a natural-language question to the KB-relative doc_id of the
failure-mode document that should ground the answer. Used by both the offline
citation-pattern test and the env-gated live ≥12/15 accuracy test in
``test_eval.py``. Keep in sync with ``docs/eval/phase3-eval-questions.md``.

The set has two question shapes:
- Descriptive scenarios (entries 1-10) — symptom + context, the original Phase 3
  exit-criterion shape.
- Terse "what causes X?" / "what is X?" forms (entries 11-15) — added after the
  2026-06-21 portfolio capture surfaced that short generic queries were losing
  the per-section "Likely causes" chunk under the original top_k=5 default
  (DECISION_LOG 2026-06-21).
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
    # Terse short-form regression set (BUG-014 / portfolio capture 2026-06-21).
    (
        "what causes tombstoning?",
        "failure-modes/tombstoning.md",
    ),
    (
        "what are shorts?",
        "failure-modes/shorts.md",
    ),
    (
        "what are opens?",
        "failure-modes/opens.md",
    ),
    (
        "what is a cold solder joint?",
        "failure-modes/cold-solder-joint.md",
    ),
    (
        "what is insufficient solder?",
        "failure-modes/insufficient-solder.md",
    ),
]
