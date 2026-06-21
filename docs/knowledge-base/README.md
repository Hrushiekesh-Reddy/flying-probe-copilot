# Failure-Mode Knowledge Base

This directory holds the failure-mode knowledge base (KB) the RAG co-pilot retrieves
over. Each markdown document describes one PCBA / ICT failure mode in operator-facing
language: symptoms, likely causes, the flying-probe / in-circuit-test signature, and
corrective actions.

## How it is used

The Phase 3 retrieval layer (`src/flying_probe_copilot/rag/`) loads every `.md` file
under this directory, splits each into heading-anchored chunks, and indexes the chunks
for hybrid (vector + lexical) retrieval. `README.md` and any file whose name starts with
`_` are **skipped** by the loader — keep meta/notes in such files.

## Authoring guardrails (NEVER violate)

- **Synthetic / owner-authored only.** No real customer data, no real defect reports.
- **No IPC-A-610 / J-STD-001 verbatim text.** These standards are copyrighted. Summarize
  and paraphrase in your own words; cite acceptance criteria **by section number only**
  (e.g. "see IPC-A-610 §8.3.x"), never by quoting the text.
- **No proprietary Keysight manual text.** Reference public i3070 / 3070 manual sections
  by name; do not paste manual content.

## Structure

- `00-index.md` — human index of the categories below.
- `failure-modes/` — one document per failure mode (the retrievable corpus).

## Expanding the KB

The seeded documents are starter stubs. Add real, field-learned failure modes over time —
one `.md` per mode, same heading structure (Summary / Symptoms / Likely causes /
ICT signature / Corrective actions / References) so chunking stays consistent.
