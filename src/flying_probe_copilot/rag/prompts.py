"""Prompt construction for the grounded-answer co-pilot.

`build_answer_prompt` renders the retrieved evidence and instructs the model to
answer ONLY from that evidence, cite the chunk ids it used, and self-refuse
(`sufficient=false`) when the evidence is inadequate — emitting strict JSON the
answer layer then validates.
"""

from __future__ import annotations

from .models import Chunk

ANSWER_SYSTEM = """\
You are a PCBA / ICT test-analytics co-pilot. Answer the engineer's question \
using ONLY the evidence chunks provided below. Do not use outside knowledge.

Rules:
- Cite the chunk_id of every chunk you actually used, in a "citations" list.
- Only cite chunk_ids that appear in the evidence below.
- If the evidence does not adequately answer the question, set "sufficient" to \
false and do not fabricate an answer.

Respond with STRICT JSON and nothing else, in exactly this shape:
{"answer": "<your answer>", "citations": ["<chunk_id>", ...], "sufficient": true|false}
"""


def _render_chunk(chunk: Chunk) -> str:
    heading = chunk.heading or "(no heading)"
    return f"[{chunk.chunk_id}] ({heading})\n{chunk.text}"


def build_answer_prompt(question: str, chunks: list[Chunk]) -> str:
    """Build the grounded-answer prompt from a question and evidence chunks.

    The output always contains the verbatim question, every chunk's id, heading,
    and text, and a JSON + citation instruction. With no chunks it still returns
    a well-formed prompt (the answer layer refuses before reaching that case).
    """
    if chunks:
        evidence = "\n\n".join(_render_chunk(c) for c in chunks)
    else:
        evidence = "(no evidence retrieved)"

    return (
        f"{ANSWER_SYSTEM}\n"
        f"=== EVIDENCE ===\n{evidence}\n\n"
        f"=== QUESTION ===\n{question}\n"
    )
