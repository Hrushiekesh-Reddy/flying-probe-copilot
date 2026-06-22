# DEMO.md — Walkthrough Script

> A scripted, repeatable demo of the Flying-Probe / ICT Test-Log Intelligence Co-Pilot.
> Use it to record the demo gif, to run a live screen-share, or to walk the project
> yourself end-to-end. Target: a viewer understands what the project does in **under 5 minutes**.
>
> Everything here runs against **synthetic data only** (see [GUARDRAILS.md](GUARDRAILS.md)).
> No real customer logs, no live API key required for the dashboard tour.

---

## 0. Prerequisites (one-time)

```bash
# Python 3.11+ and uv installed (https://docs.astral.sh/uv/)
uv sync                      # install all dependencies from the lockfile
```

Optional, for the Co-Pilot page with a *live* LLM (the tour below also works without it):

```bash
cp .env.example .env         # then paste your GOOGLE_API_KEY into .env
```

> The dashboard tour (steps 2–4) needs **no** API key. Only the live Co-Pilot answer
> in step 4 calls Gemini; without a key the page still renders and refuses gracefully.

---

## 1. Generate synthetic data (≈10 s) — *"there is no real data in this repo"*

```bash
uv run generator --board-profile=small --count=20 --out=data/synthetic
```

**Say:** "The generator emits real Keysight Log Record Format logs — the public HP3070 / i3070
format — with three board profiles, configurable fault correlation, three shifts, and
shift-physics-aware timestamps. One thousand panels generate in about a second."

**Show:** the stamped run directory it created:

```bash
ls -dt data/synthetic/run_* | head -1     # e.g. data/synthetic/run_20260622_001530
```

---

## 2. Parse into DuckDB (≈2 s) — *"logs become queryable rows"*

```bash
RUN_DIR=$(ls -dt data/synthetic/run_* | head -1)
uv run parser --input="$RUN_DIR" --db=data/db/sample.duckdb
```

**Say:** "The parser ingests every log line into a 9-table DuckDB schema — five dimension
tables, one run table, three fact tables — with byte-precise round-trip integrity. The whole
thing is a single file, zero-ops."

> For a richer demo dataset (the one behind the committed screenshots), run
> `bash scripts/build-portfolio-data.sh` instead — three 300-panel batches into one DB.

---

## 3. Launch the dashboard — *"the analytics layer"*

```bash
uv run streamlit run src/flying_probe_copilot/ui/app.py
```

Open the local URL Streamlit prints (default `http://localhost:8501`). Walk the six pages
left-to-right in the sidebar:

| Page | What to point at | One-line talking point |
|---|---|---|
| **Overview** | KPI strip + window summary | "Yield, panels tested, top failure at a glance." |
| **Yield** | yield-by-dimension bar chart; switch the group-by to shift / line / operator | "Same metric, sliced by board, shift, line, or operator — all real per-panel data." |
| **Pareto** | top failures by record type + cumulative line | "Classic 80/20 — which failure modes to chase first." |
| **SPC** | Shewhart individuals (XmR) chart with control limits + alarms; pick a board/refdes | "Wheeler-doctrine individuals chart: 3σ limits from MR̄/1.128, plus the run-of-8 rule." |
| **Anomalies** | leave-one-out z-score bars | "Each group scored against a baseline that excludes itself — no self-masking." |
| **Co-Pilot** | the chat box | next step ↓ |

**Say (loading time):** "On 100k records the default page renders in well under two seconds."

---

## 4. Ask the Co-Pilot — *"natural-language root-cause, with citations"*

On the **Co-Pilot** page, type:

```
What causes tombstoning?
```

**Show:** the grounded answer, then **open the Citations expander** — it pins the exact
knowledge-base chunk the answer is grounded on (e.g. `failure-modes/tombstoning.md#3`,
"Likely causes").

**Say:** "Hybrid retrieval — BM25 lexical plus ChromaDB cosine vectors, fused with Reciprocal
Rank Fusion — pulls the relevant failure-mode docs. The answer layer is strictly grounded: every
claim traces to a retrieved citation, and if the evidence is insufficient it **refuses** instead
of inventing a root cause."

**Show the refusal (optional):** ask something off-domain —

```
What is the capital of France?
```

— and point at the refusal. "No supporting evidence in the knowledge base, so it declines."

---

## 5. Show the engineering rigor (optional, ≈30 s)

```bash
uv run pytest -q                       # full suite, green
```

**Say:** "Test-driven throughout — the suite is green at every phase boundary, 97% coverage,
and CI runs lint plus tests on every PR. The RAG layer has an env-gated live eval that scores
the co-pilot against a frozen question set."

The live eval (needs a key) is the Phase 3 exit criterion:

```bash
RAG_RUN_LLM_EVAL=1 uv run pytest tests/test_rag/test_eval.py -v
```

---

## 6. Where to go next

- Architecture diagram + 60-second pitch → [README.md](../README.md)
- The long-form story (problem, scope decisions, three engineering stories, results)
  → [docs/case-study.md](case-study.md)
- The non-negotiable guardrails (synthetic-only, no copyrighted text, no secrets)
  → [docs/GUARDRAILS.md](GUARDRAILS.md)

---

## Recording the demo gif (maintainer note)

The committed `docs/img/demo.gif` and the six dashboard screenshots are regenerated headlessly —
no manual capture, no live key — by:

```bash
bash scripts/build-portfolio-data.sh                       # build the sample DB (once)
uv run python scripts/capture_screenshots.py all \
    --db data/db/sample.duckdb --out docs/img/
```

The Co-Pilot frame uses a canned grounded answer (`scripts/_capture_app.py`) so the gif is
reproducible without calling Gemini.
