# Decision Log — Flying-Probe Co-Pilot

Architectural, design, and process decisions in reverse-chronological order.
Every non-obvious choice gets an entry here: what was decided, why, what was rejected, and when to revisit.

---

## 2026-06-21 — RAG `DEFAULT_TOP_K = 10` and eval-set growth 10 → 15

**Decision:** Bump `answer()` default `top_k` from 5 to 10 (extracted to `DEFAULT_TOP_K` module
constant in `src/flying_probe_copilot/rag/answer.py`), expand `EVAL_QUESTIONS` from 10 to 15
(append 5 terse short-form questions; live threshold scales 8/10 → ≥12/15 at the same 80% pass
rate). Owner-ratified at the in-session Decision Gate after empirical probe.

**Context / Why:**
- Portfolio capture 2026-06-21 surfaced that typing the terse "what causes tombstoning?" in the
  Co-Pilot chat returned a refusal. Empirical probe (real `all-MiniLM-L6-v2` + BM25 + RRF over
  `docs/knowledge-base/`): the relevant `failure-modes/tombstoning.md#3` ("Likely causes") chunk
  is at **rank 9** for that query. The chunk's body uses generic vocabulary ("uneven heating",
  "pad design", "excess paste") with no topic-word anchor; several other docs' own "Likely causes"
  sections out-rank it because they contain "causes" plus their own topic words.
- The original brief proposed `top_k=8` as the cheapest fix; the probe showed 8 is insufficient.
  Probed 7 additional terse queries — tombstoning is the outlier (most targets land within rank 4;
  worst-case-non-tombstoning is "reason for missing components?" at rank 7).
- The existing eval dataset was descriptive-shape only ("Why would a chip component stand up on
  one end during reflow?"), so the live eval gate never exercised the terse short-form failure mode.

**What was rejected:**
- `top_k=8` alone — empirically insufficient (target at rank 9).
- `top_k=8 + heading-aware boost` (Option 2 in the brief) — adds branching keyword logic ("cause" /
  "why" / "reason" → upweight chunks with heading "Likely causes" / "Root cause") for marginal gain
  on an 8-doc KB. Saved for the parking lot.
- Cross-encoder rerank (Option 3 in the brief) — needs an approval-gated `pyproject.toml` dep add
  (`sentence-transformers[cross-encoder]` or similar) and is overkill at the current corpus size.
  Revisit only if the KB grows past ~50 docs and a heading boost stops being enough.
- Re-chunking the KB to prepend doc title to every chunk's indexed text — fixes the root cause but
  is an architectural change to `kb_loader` with downstream effects on citation display. Too much
  risk for the current scope.
- Replacing some descriptive eval questions with terse ones to keep the count at 10 — would lose
  scenario coverage. Additive expansion preserves both shapes.

**How to apply:**
- `top_k` is now a soft contract: `answer()` defaults to `DEFAULT_TOP_K` (10), but explicit callers
  may pass any non-negative int. Tests that depended on the number 5 (`ANS-24`) now import
  `DEFAULT_TOP_K` and assert against the constant — self-updating on future bumps with a
  bidirectional value pin.
- New env-gated test file `tests/test_rag/test_retrieval_real.py` (`RAG_RUN_MODEL_TESTS=1`) pins
  the canonical regression at the retrieval layer: target chunk in `top_k=DEFAULT_TOP_K` hits.
  Catches retrieval regressions without burning an API call.
- Eval-set growth pattern is additive: any future failure-mode discovered through portfolio /
  manual QA gets a new entry, the live threshold scales as `ceil(0.8 * N)`.

**Revisit when:** the KB grows past ~30 docs (re-evaluate whether `top_k=10` is still enough — at
that corpus size a heading-aware boost or doc-title prepend in the loader probably wins); OR a future
KB doc has a "Likely causes" section that lands deeper than rank 10 for its terse query (the
env-gated retrieval test will surface this).

---

## 2026-06-20 — Phase 3 slice 3: chat UI + evaluation contracts

**Decision:** The Co-Pilot chat page + 10-question evaluation ship with these contracts
(owner-ratified "use your recommendations" at `docs/plans/2026-06-20-phase3-slice3-decision-gate.md`).

1. **Chat is a 6th `st.navigation` page** inside the existing DB-gated dashboard shell (not a separate
   entrypoint). The chat logic needs no DB, but the dashboard still requires the DuckDB to launch
   (unchanged Phase-2 `st.stop()` behavior). Rejected: standalone chat entrypoint (more surface, splits app).
2. **Backend failures degrade gracefully:** `render_chat` wraps the `answer_question` call in
   `try/except Exception → st.error`, appending no turn. Covers the live no-key `ValueError` / network
   errors without crashing the page. Rejected: propagating the exception.
3. **Injectable backend for offline tests.** `get_retriever`/`get_client`/`answer_question` are
   `# pragma: no cover` live seams; `render_chat` calls the module-global `answer_question`, which tests
   monkeypatch to a fake. AppTest smoke uses self-contained `_smoke_chat` wrappers with inner imports
   (because `AppTest.from_function` source-extracts only the passed function's body). An autouse env-strip
   was added to `tests/test_ui/conftest.py` (the slice-2 strip covered only `tests/test_rag/`).
4. **Evaluation is split:** an OFFLINE citation-pattern test (scripted StubRetriever + FakeLLMClient
   proving each question→expected-doc citation for all 10, deterministically) PLUS an env-gated live
   accuracy test (`@skipif(not RAG_RUN_LLM_EVAL)`, default-skipped) that measures the ≥8/10 exit criterion
   against the real Gemini model. The actual ≥8/10 number is the owner's manual/env-gated run — the
   offline suite cannot measure real accuracy (needs model + embeddings + key). The live test must be
   verified by skip-inspection only, never executed in CI.
5. **`EVAL_QUESTIONS` (10) live in code** (`tests/test_rag/eval_dataset.py`) mirrored by
   `docs/eval/phase3-eval-questions.md`; expected_doc is the KB-relative POSIX doc_id
   (`failure-modes/<name>.md`), matching the slice-1 `kb_loader` chunk_id prefix. All 8 seeded docs covered.
6. **Declared deviation from additive-only:** `ui/app.py` edited to register the page + update its
   "5 pages" docs to "6 pages". No approval-gated files touched.

**Phase 3 close:** with this slice all Phase 3 code deliverables are shipped; the owner runs the live
≥8/10 eval with the (rotated) key and promotes `dev → main` at the Phase 3 boundary.

---

## 2026-06-20 — Phase 3 slice 2: LLM answer-layer contracts

**Decision:** The Gemini answer layer ships with these contracts (owner-ratified "use your
recommendations" at `docs/plans/2026-06-20-phase3-slice2-decision-gate.md`).

1. **Strict anti-hallucination grounding.** A non-refused `Answer` requires ALL of: retrieval hits,
   a valid JSON object, `sufficient is True` (strict identity — missing/`"yes"`/`0`/`false` all
   refuse), non-empty `answer_text`, and ≥1 citation that is in the retrieved chunk ids. Any failure
   → refuse with a fixed `REFUSAL_TEXT` + `citations=()`. Rejected: trusting the model's own
   sufficiency claim (lenient) — ungrounded answers could escape, defeating the project's point.
2. **The LLM is never called when there is nothing to ground on** — blank/None question or zero
   retrieval hits return a refusal WITHOUT invoking the client (proven in tests via a client that
   raises if called).
3. **Citations = chunk_ids, returned in retrieval order, de-duplicated.** Non-retrieved ("hallucinated")
   citations are dropped; non-string items ignored; if none remain → refuse.
4. **Lock to google-generativeai 0.8.6.** Migrating to the newer `google-genai` SDK is a parking-lot
   item (revisit at Phase 4 polish). google-genai is not installed.
5. **Gemini only; no Claude fallback** this slice (CLAUDE.md parks the backup-LLM decision until after
   Phase 3).
6. **Offline + secret-safe test suite.** The live path (`GeminiClient._call_model`) lazily imports
   google-generativeai and is `# pragma: no cover`; an autouse conftest fixture strips
   `GOOGLE_API_KEY`/`ANTHROPIC_API_KEY` from the environment for every test; the missing-key guard
   raises `ValueError` and is covered offline. No test reads a real key or makes a network call.
7. **`GeminiClient` requests `response_mime_type="application/json"`** but the orchestrator parses +
   validates the JSON DEFENSIVELY regardless (never trusts the model blindly). `response_schema` is
   intentionally NOT used in slice 2.
8. **Declared deviation from additive-only:** the slice-1 test
   `test_public_api.py::test_api03_all_lists_exactly_the_public_names` was edited to expect the 11-name
   `__all__` set (7 slice-1 + answer/Answer/GeminiClient/LLMClient) — required to keep the full suite green.

**Security note:** a real `GOOGLE_API_KEY` placed in the gitignored `.env` surfaced in a subagent's
analysis this session. Not committed (repo exposure nil), but the owner should rotate it.

---

## 2026-06-20 — Phase 3 slice 1: RAG retrieval-core contracts

**Decision:** The offline hybrid-retrieval core (`src/flying_probe_copilot/rag/`) ships with these
contracts. Slicing + the 9 gate decisions were owner-ratified ("use your recommendations") at the
Decision Gate (`docs/plans/2026-06-20-phase3-slice1-decision-gate.md`).

1. **Phase 3 is sliced into 3.** Slice 1 = offline retrieval core + KB scaffold (this session, no
   Gemini key); slice 2 = Gemini LLM + citation prompt + anti-hallucination; slice 3 = chat UI +
   10-Q eval. Rejected: building all 7 deliverables at once (blocks on the API key, high single-session
   risk). Revisit: never — Phase 2 precedent (3 slices) validated.
2. **ChromaDB collection uses `hnsw:space="cosine"`, not the default L2.** Red-team B1: under default
   L2, raw bag-of-words vectors rank by magnitude, not overlap. Cosine + binary presence vectors (the
   test fake embedder) make nearest = most-overlapping. Production ST embeddings are unit-norm-friendly
   under cosine. Collection name is per-instance `kb_{uuid}` because `EphemeralClient` shares
   process-level state (a fixed name collided across instances in one test run).
3. **Lexical match = token overlap, NOT BM25 score > 0.** Red-team B3: `rank_bm25` returns ≤0 scores
   for a term present in the only/most documents, so a sole matching chunk can score ≤0. A chunk is a
   candidate iff it shares ≥1 query token; candidates are ranked by BM25 score (negatives allowed),
   tiebreak chunk_id ASC. Rejected: "drop score ≤0" (would erase legitimate single-doc matches).
4. **RRF: `score = Σ 1/(rrf_k + rank)`, rank base 1, `rrf_k=60`, equal weight; sort score DESC then
   chunk_id ASC.** Red-team B2: RRF does NOT universally rank a both-list chunk above a one-list chunk
   (a one-list rank-1 chunk at `1/61` can beat a both-list pair at high ranks). SUCCESS-WHEN re-scoped
   to the low-rank regime of the small RET-01 corpus; no general guarantee is claimed.
5. **Embedder is injectable; the default `SentenceTransformerEmbedder` (all-MiniLM-L6-v2) is lazy.**
   Unit tests inject a deterministic model-free fake embedder → the suite is fully offline + reproducible
   with no model download. The real model is exercised only by an env-gated test
   (`RAG_RUN_MODEL_TESTS`, default-skipped); its load/embed body is `# pragma: no cover` so the ≥80%
   coverage gate is attainable offline. Rejected: tests hitting the real model (slow, network-dependent,
   CI-fragile).
6. **`RetrievedChunk` exposes the fused score + per-retriever ranks (`lexical_rank`/`vector_rank`,
   `None` if absent) — NOT raw per-retriever scores.** Ranks are what RRF + future citation need; raw
   scores deferred. Revisit if slice 2 citation needs raw relevance scores.
7. **Chunking:** ATX-heading sections, fence-aware (a `#` inside a ```` ``` ```` block is not a heading);
   preamble/heading-less → one chunk with `heading=""`; bodies > `MAX_CHUNK_CHARS=1200` sub-split on
   blank lines, hard char-split as fallback; deterministic ids `"{posix_relpath}#{ordinal}"`. Bad
   `kb_dir` raises `FileNotFoundError`/`NotADirectoryError` (never a silent `[]`).
8. **`top_k`/`rrf_k` boundaries:** `top_k==0 → []`, `top_k<0 → ValueError`, `rrf_k<1 → ValueError`,
   uniform across lexical/vector/retriever.
9. **Slice 1 retrieves over the KB markdown corpus only**, not DuckDB rows — row-grounding waits for
   the LLM (slice 2/3). No approval-gated file touched (all deps already in `pyproject.toml` + `uv.lock`).

---

## 2026-06-18 — Phase 2 slice 3: Streamlit dashboard UI contracts

**Decision:** The `src/flying_probe_copilot/ui/` Streamlit dashboard ships with these contracts. The two
headline product choices were owner-ratified at the Decision Gate
(`docs/plans/2026-06-18-phase2-slice3-decision-gate.md`).

1. **No `pyproject.toml` edit.** `streamlit>=1.40` + `plotly>=5.24` were already declared (Phase 0 stack
   lock) and present in `uv.lock` (verified: 1.58.0 / 6.8.0 import + app launches). The handover's
   anticipated approval-gated dependency add was **moot**; zero gated files touched this slice.
2. **Yield page = bar of yield % per group, NOT a time-series line.** `yield_over_time` returns one
   aggregate row per group for the window; `group_by="day"` was deferred at the analytics layer
   (DECISION_LOG 2026-06-16). Faking a trend by looping the function per day would reimplement the
   deferred bucketing AND produce overlapping windows. Owner approved bar-per-group.
3. **"Drill-down" = data-table `st.expander` + Plotly hover + the dimension/value filters**, NOT
   analytics-layer value-subsetting. The four analytics functions aggregate-by-dimension and do not
   accept a "show only board X" filter; adding one would change their signatures (out of scope). The
   value multiselect post-filters the returned grouped rows in the UI (`data.filter_df_by_key`).
4. **Date-range → analytics window mapping.** The sidebar date-range picker maps to the native window API
   via `data.date_range_to_window(start, end)`: `as_of = combine(end, 23:59:59)` (naive UTC, includes the
   whole end day) and `window_days = max(1, (end - start).days + 1)`. The `+1` over-includes at most one
   day (minus one second) on the low end — the **safe** direction (never silently drops the chosen start
   day), since the analytics window is `[as_of - window_days, as_of]` and exposes no separate lower bound.
5. **Connection caching = `st.cache_resource`, read-only.** `data.get_connection(db_path)` opens
   `duckdb.connect(db_path, read_only=True)` once per process (the dashboard never writes; read-only also
   lets the file open while a generator/parser holds a writer elsewhere). Query results are cached with
   `st.cache_data` returning **DataFrames**; the connection is passed as `_con` (leading underscore →
   excluded from the cache hash) and `db_path` is the hashed cache key.
6. **DB path via `FPC_DB_PATH` env var**, default `data/db/sample.duckdb` (gitignored, regenerated
   locally). Missing DB → `st.error` + `st.stop()` (no traceback). Empty window → `st.info` guidance.

**Why:** Honour the pure-function analytics contracts rather than bending them for presentation — the UI
formats what the functions return and never reimplements analytics logic. Read-only cached connection +
`cache_data`-on-results is the documented Streamlit + DuckDB pattern and meets the < 2 s / 100k exit
criterion (measured 0.23 s page load on the 70-panel sample). Loud missing-DB / empty-window states avoid
the silent-wrong-data class the project has repeatedly guarded against.

**Rejected:**
- **UI-composed daily yield trend line** — overlapping windows + reimplements deferred `day` grouping.
- **Analytics-layer value filters / new `where=` params** — would change the four tested function
  signatures; out of scope for a UI slice.
- **`width='stretch'` instead of `use_container_width=True`** — cleaner on 1.58 but unsupported on the
  declared `streamlit>=1.40` floor; deferred behind an approval-gated floor bump (BUG-012).
- **Caching the connection with `st.cache_data`** — wrong tool (connections aren't serializable);
  `cache_resource` is the correct primitive.
- **Streamlit `pages/` magic directory** — replaced by explicit `st.navigation` + a `views.py` module of
  `render_*(con, filters)` functions, which is unit/`AppTest`-testable and keeps filter state in one place.

**Revisit when:**
- A real consumer needs a genuine yield time-series → add `group_by="day"` (or a bucketed variant) at the
  **analytics** layer first, then a line chart consumes it.
- A page needs true single-value drill-down → add an optional `where`/value filter to the analytics
  function (additive) rather than post-filtering in the UI.
- The Streamlit floor is bumped → migrate `use_container_width` → `width=` (BUG-012).

**Verification:** 81 new tests in `tests/test_ui/` (pure helpers + chart builders unit-tested; views + app
via `AppTest`, incl. empty-window, no-boards, empty-DB, missing-DB branches). Full suite 373 passed /
1 xfailed / 97% coverage (`ui/data.py` + `ui/charts.py` 100%). Live `streamlit run` + `AppTest.from_file`
against the real sample DB render the default page with 5 KPI cards in 0.23 s. See
`docs/plans/2026-06-18-phase2-slice3-{plan,decision-gate,triple-check,manual-qa}.md`.

---

## 2026-06-18 — Phase 2 slice 2: SPC (individuals chart) + z-score anomaly contracts

**Decision:** The SPC + anomaly slice ships two pure-library functions —
`individuals_chart` and `z_score_anomalies` — with the following contracts. All four headline
choices were owner-ratified at the Decision Gate (`docs/plans/2026-06-18-phase2-slice2-decision-gate.md`).

1. **Alarm-rule family = Wheeler / XmR doctrine.** Default-on `rules=('rule_1','rule_4')`; opt-in
   `('rule_2','rule_3')`. rule_1 = point beyond 3σ; rule_4 = run of **8** consecutive points one side
   of the centre line; rule_2 = 2-of-3 beyond 2σ same side; rule_3 = 4-of-5 beyond 1σ same side. A rule
   flags **every** point whose trailing window satisfies its pattern (so a 9-run flags points 8 and 9).
2. **Sigma estimator = MR̄ / 1.128** (d2 for span-2 moving ranges). Limits = `mean ± 3·(MR̄/1.128)`.
   The literal `2.66` (= 3/1.128 rounded) is never used in code or test assertions — exact division only.
3. **Individuals-chart value = per-panel `mean(measured_value)` for a single `(board_profile_id, refdes)`**
   (optional `record_type`). Signature gains required `refdes`. Window/validation contracts mirror slice 1.
4. **Anomaly metric = per-group failure rate** (`failed/total`, `failed = COUNT(btest_status != 0)`).
   `by ∈ {board, shift, line, operator}` (slice-1 vocabulary).
5. **Leave-one-out baseline.** For group `g`, `baseline_mean`/`baseline_std` are computed over the
   failure rates of all OTHER in-window groups (g excluded from both). `baseline_std` uses **ddof=1**
   (sample). `< 2` peers ⇒ `baseline_std = 0.0` (never call `statistics.stdev` on one element).
   `baseline_std == 0` ⇒ `z = 0.0`, not flagged (no divide-by-zero).
6. **`flagged = abs(z) >= threshold`** (two-sided). `threshold <= 0` raises `ValueError`.
7. **Anomaly ordering = `abs(z_score) DESC, group_key ASC`** (severity-first). **Diverges** from slice-1's
   universal `group_key ASC` (2026-06-16 Decision #2) — anomaly lists are inherently severity-ranked, and
   the slice-1 log already left an additive `order_by` revisit path open. `individuals_chart` orders
   `start_ts ASC, panel_serial ASC` (time-ordered, required for the moving-range sequence).
8. **Stretch items deferred (owner choice).** **X-bar/R** charts deferred — they need rational subgroups
   of size > 1, which the per-panel synthetic data does not naturally have (forcing artificial subgroups
   would fabricate variance structure). **Isolation Forest** deferred — it needs a `sklearn` dependency
   (`pyproject.toml` is approval-gated) and clashes with the deterministic leave-one-out z-score. **No
   schema change** — existing `measurements`/`components`/`test_runs`/`panels` columns are sufficient.

**Why:** The data is the textbook XmR case — one reading per time point, no rational subgroup. Wheeler's
"Rule 1 by default, others in reserve" avoids the ~4–9× false-alarm inflation that stacking zone rules
causes on autocorrelated, possibly-skewed per-panel data (Step 2 research: NIST/SEMATECH e-Handbook ARL
370→91.75 for all-WECO; Nelson all-8 ARL→38). MR̄/1.128 is mandatory over the global sample stdev because
the global stdev silently absorbs the sustained shifts the chart exists to detect, widening the limits.
`duration_s` is hardcoded to 12 (zero variance), so a refdes-selected `measured_value` is the only
defensible continuous I-MR value; failure rate / counts are attribute data that want c/u/p-charts, not
individuals. Leave-one-out prevents an anomalous group from inflating its own baseline and hiding itself.

**Rejected:**
- **Nelson 8-rule set** — N7/N8 require subgroups (n≥2); our chart is n=1 per refdes. Full stack → ARL≈38.
- **Rule-1-only** — misses the sustained small shifts rule_4 catches.
- **`duration_s` as the I-MR value** — constant 12 in synthetic data → a flat, useless chart.
- **Raw failure count** as the anomaly metric — scales with group volume → high-volume groups self-flag.
- **Binary per-panel pass/fail z-score** — 0/1 attribute data, infinite-tail z.
- **Population std (ddof=0)** for the baseline — understates spread on small peer sets.
- **One-sided z flag** — would miss anomalously-LOW failure rates (which can also signal a process change).
- **X-bar/R now / Isolation Forest now** — deferred per the owner Decision Gate (above).

**Revisit when:**
- A genuine rational subgroup emerges (e.g. replicate probes per net per panel) → add X-bar/R.
- A real consumer wants ML anomaly detection → add `sklearn` + Isolation Forest behind the same
  `AnomalyRow` shape (owner-approved dependency add).
- A real caller needs proportion-z normality at small N → add a logit/arcsin transform option to
  `z_score_anomalies` (additive; default stays raw proportion).
- A caller wants the MR chart companion (UCL = D4·MR̄ = 3.267·MR̄) → add a sibling function.

**Verification:** 57 new tests (29 SPC + 24 anomaly + 4 public-API) in `tests/test_analytics/test_spc.py`
and `test_anomaly.py`; `spc.py` + `anomaly.py` 100% coverage; full suite 292 passed / 1 xfailed / 0 failed;
repo coverage 97%. Plan + red-team resolutions in `docs/plans/2026-06-18-phase2-slice2-{plan,test-plan,
triple-check}.md`.

---

## 2026-06-18 — Tests never write to the repo tree; use `tmp_path` (BUG-011)

**Decision:** Test helpers that need a file on disk MUST write to pytest's per-test `tmp_path` (or `NamedTemporaryFile`), never to a fixed path inside the repo working tree. Applied to `_render_to_text` in `tests/test_parser/test_log_parser.py`, which had been writing to `repo_root / "tmp_test_render.log"`.

**Why:** A fixed path in the repo tree is (a) shared across every caller — two tests using the helper raced the same file under any parallel/repeated execution — and (b) actively watched by editors (VS Code file watcher), git, antivirus, and the Windows Search indexer, which take transient locks on freshly-created repo-tree files. During a full-suite run that produced partial reads (assertion failures) and `PermissionError [WinError 32]`, while the test passed in isolation. `tmp_path` is unique per test and lives under the OS temp dir, outside those watchers. This was the root cause of BUG-011.

**Rejected:**
- **Unique-named file still at the repo root** (e.g. `f"tmp_render_{uuid}.log"`). Fixes the cross-caller sharing but not the repo-tree-watcher lock face of the bug, and litters the working tree if a test crashes before cleanup.
- **In-memory render (no file).** Cleanest in theory, but `render_log` is a file-only serializer (`Path(path).write_bytes(...)`); adding a bytes-returning path would change production code for a test-only convenience — out of scope for a flaky-test fix.
- **Forcing `PYTHONHASHSEED` / adding a randomization plugin.** Would only matter if test *content* were hash-dependent; it isn't (the generator threads all randomness through `random.Random(seed)` and the fixture path never calls `hash()`). Treating the symptom, not the cause.

**Revisit when:** Never expected to reverse. If a future test genuinely needs a stable cross-test artifact, it belongs in a fixture with an explicit scope and teardown, still rooted under `tmp_path_factory`, never the repo tree.

---

## 2026-06-16 — Phase 2 analytics: 6 v1 contract decisions

**Decision:** The Phase 2 analytics foundation (`yield_over_time` + `failure_pareto`) ships with six v1 contracts that intentionally diverge from the Phase 1b notebook in places. Owner approved all six at Decision Gate as recommended.

1. **Pareto v1 groups by `record_type` only.** Notebook Query 2 groups by `(record_type, failure_category)` — a 2-column key. `failure_pareto(by="record_type")` collapses across `failure_category`, returning one row per record_type. Adding `failure_category` to `ParetoRow` is deferred (would require an asymmetric optional field). Notebook Q2 row-for-row match is **not** a v1 contract.
2. **Yield ordering: `group_key ASC` universally.** Matches notebook Q1 (`board_profile_id` ASC). Diverges from Q4 (`panels_tested DESC, operator_id`). Callers re-sort by count via `sorted(rows, key=lambda r: -r.total)` if needed.
3. **Percentages are unrounded floats.** `yield_pct`, `pct_of_total`, `cumulative_pct` are raw IEEE-754 doubles from SQL. Notebook Q3/Q4/Q5/Q6 `ROUND(..., 2)` is NOT matched. Caller rounds at presentation. Y-01's row-for-row match against Q1 uses `math.isclose(rel_tol=1e-9)`.
4. **`window_days <= 0` raises `ValueError`.** Not "zero days = today only", not "negative = whole DB" — strict positive int contract. Programmer mistakes are loud.
5. **`top_n <= 0` raises `ValueError`.** Same family. DuckDB `LIMIT -1` behavior is implementation-defined; we don't expose it.
6. **Tz-aware `as_of` raises `ValueError`.** DuckDB TIMESTAMP is naive. Silent-strip masks bugs (e.g. Streamlit passing local-tz "now" gets converted with no warning). Callers explicitly `.replace(tzinfo=None)` after asserting UTC.

**Why:** v1's job is to surface the analytics contract clearly. Matching every notebook query row-for-row would lock the analytics layer to one set of presentation rules (rounded floats, count-descending per-query). Lock the analytics layer to a single uniform contract, then let any future presentation layer (Streamlit, notebook v2) format from it. Loud validation up front avoids silent-wrong-data classes of bug that the BUG-007 deferral already taught us to fear.

**Rejected:**
- **`ParetoRow.failure_category` as a sometimes-populated field.** Would salvage Q2 row-for-row match. Cost: dataclass becomes type-asymmetric (populated for `by="record_type"`, None for `by="refdes"`). Downstream code has to null-check every call site.
- **Per-group_by ordering rules embedded in `yield_over_time`.** Most faithful to notebook. Cost: 4 different ORDER BY clauses to maintain, 4 different test contracts, hardest to reason about.
- **Caller-controlled `decimals: int | None = None`.** Punts on the rounding question. Cost: doubles the test matrix; future Streamlit pages each pick a different decimals value and reports drift.
- **`window_days=0` returns `[]` silently.** Comfortable but silent. Two cases (caller meant "no rows" vs caller bug) become indistinguishable.
- **`top_n=0` returns `[]` silently.** Same.
- **Silent strip of tz-aware `as_of`.** Streamlit habit will pass local-tz datetimes; silent conversion = silent window shift = silent wrong answer.

**Revisit when:**
- A real Streamlit dashboard demands the Q2 2-column Pareto view → add `ParetoRow.failure_category` (optional, populated for record_type). Don't change the existing contract.
- A real consumer needs Q4-style "biggest groups first" → add an `order_by: Literal["group_key", "count_desc"] = "group_key"` parameter (additive, default preserves current contract).
- A real caller wants tz-aware datetimes → add a `tz: timezone | None = None` parameter that converts internally to UTC before validation (additive).
- `window_days = 0` becomes a real use case ("just today's data") → add explicit support with documented semantics (e.g. `[as_of, as_of]`).

**Verification:** All six decisions enforced in `src/flying_probe_copilot/analytics/yield_metrics.py`, `pareto.py`, `_window.py` and asserted in 39 analytics tests under `tests/test_analytics/`. Full repo suite 224/224 green.

---

## 2026-06-18 — Drop `placeholder_fields` field from `YieldRow` / `ParetoRow`

**Decision:** Remove the `placeholder_fields: tuple[str, ...]` field from both analytics dataclasses. Simplify `_GROUP_BY_CONFIG` in `yield_metrics.py` from `(SELECT col, JOIN clause, placeholder tuple)` to `(SELECT col, JOIN clause)`. Drop the `placeholder_fields=` kwarg from both `YieldRow(...)` and `ParetoRow(...)` constructors. Retire P-12 / P-13 and refactor Y-08 / Y-09 / Y-10 / Y-11 into plain group_by smoke tests.

**Why:** BUG-007 closed via Path A on 2026-06-17 (PR #12). The marker's whole purpose was to signal "this column's source data is placeholder" — now the source data is real per-panel data on every code path. Keeping a vestigial field that's always `()` on every result row leaves a self-described "this is placeholder" promise the dataclass can't keep. Two options were on the table:

- **(a) Drop the field entirely (chosen).** Breaking change to a public API surface (`YieldRow.placeholder_fields`). No downstream consumers today (no notebook reads it, no Streamlit page exists yet). Cleanest end-state.
- **(b) Keep the field, always emit `()`.** Backward-compatible but dishonest — the docstring promises "lists the specific column name(s) when something is", and now nothing ever is. Vestigial code rots faster than absent code.

(a) wins because Phase 2 slice 1 has not shipped beyond `dev`; there is no external API contract to preserve. The 2026-06-16 decision's "Forward-compat: ... auto-update" promise is what carries us through the rename — consumers that would have written `if row.placeholder_fields: warn(...)` get a clean `AttributeError` instead of a silently empty check.

**Rejected:**
- **Option (b) above.** Quieter but leaves a vestigial field future readers will ask about.
- **Wait until a real Streamlit consumer exists, then decide.** Cost: ship the placeholder marker into a third file (Streamlit page), making future removal harder.

**Revisit when:** A future schema regression re-introduces silent-placeholder data on shift / line_id / operator_id. At that point the marker pattern should come back as a result-set wrapper (see Rejected list in the 2026-06-16 entry) rather than a per-row field, since the failure mode is global to a group_by call, not per-row.

**Verification:** 238 tests passing, 1 xfailed, 97% coverage on branch `feature/analytics-drop-placeholder-markers`. A-02 / A-03 expected field sets reduced from 5 to 4 fields each. `grep -rn placeholder_fields src/ tests/` returns only one comment-only line (test section header narrating the history).

---

## 2026-06-16 — Per-row `placeholder_fields` marker for BUG-007

**Decision:** Every analytics output row (`YieldRow`, `ParetoRow`) carries a `placeholder_fields: tuple[str, ...]` field naming columns whose source data is currently BUG-007-affected. The tuple is empty `()` when nothing is affected, and lists the specific column name(s) when something is.

| Call | `placeholder_fields` |
|------|----------------------|
| `yield_over_time(group_by="board")` | `()` |
| `yield_over_time(group_by="shift")` | `("shift",)` |
| `yield_over_time(group_by="line")` | `("line_id",)` |
| `yield_over_time(group_by="operator")` | `("operator_id",)` |
| `failure_pareto(by="record_type")` | `()` |
| `failure_pareto(by="refdes")` | `()` |

**Why:** BUG-007 means `panels.shift = 'A'` and `panels.line_id = 'LINE-A'` are uniform placeholders today, and `test_runs.operator_id` is per-run not per-panel. Computing per-shift / per-line / per-operator yield therefore returns degraded data — useful for testing the analytics pipeline, dangerous if a downstream dashboard renders it without warning. Per-row marker (vs result-set-level wrapper) lets each row self-describe — survives filtering, slicing, mapping, and any pandas/Streamlit reshape downstream. Forward-compat: when BUG-007 is properly fixed, the marker tuple becomes `()` for those group_by values; consumers that check `if row.placeholder_fields: warn(...)` auto-update.

**Rejected:**
- **Docstring-only caveat, no runtime marker.** Lowest friction. Cost: a future Streamlit page that prints per-shift yield has no programmatic way to attach a caveat banner. Silent placeholder data is the exact wrong-data risk the brief warned against.
- **Result-set wrapper `Result(rows=[...], placeholder_fields=("shift",))`.** Cleaner type. Cost: slicing/merging loses self-description. A page that combines two queries' rows can't tell which rows came from a placeholder-affected source.
- **Raise on placeholder-affected `group_by` until BUG-007 is fixed.** Hardest contract; punishes callers who explicitly want to see the degraded data (e.g. for testing the analytics pipeline).

**Revisit when:** BUG-007 is properly fixed via path A (generator extension), B (results.json sidecar), or C (schema nullability). At that point the relevant `placeholder_fields` tuple flips to `()` and one-line edits in `_GROUP_BY_CONFIG` suffice.

**Verification:** Y-08 (board=`()`), Y-09 (shift=`("shift",)`), Y-10 (line=`("line_id",)`), Y-11 (operator=`("operator_id",)`), P-12 (record_type=`()`), P-13 (refdes=`()`).

> **Resolved 2026-06-18 — marker removed entirely.** BUG-007 closed via Path A in PR #12 (operator_id at field 12, shift at field 13, line_id at field 14, all NOT NULL). The forward-compat "tuple flips to `()`" path predicted above became "every tuple is now `()`" — a vestigial field on every output row. Per Decision 2026-06-18 (below) the field is dropped from `YieldRow` and `ParetoRow`; Y-08 / Y-09 / Y-10 / Y-11 / P-12 / P-13 retired or refactored into plain group_by smoke tests.

---

## 2026-06-16 — Analytics window anchor: `MAX(test_runs.start_ts)`, inclusive both ends, naive UTC

**Decision:** Both `yield_over_time` and `failure_pareto` anchor their default rolling window on `SELECT MAX(start_ts) FROM test_runs`. Caller may override via `as_of` parameter. Window is `[as_of - window_days, as_of]`, inclusive on both ends. All datetimes are naive UTC (no tzinfo).

**Why:** Anchoring on `MAX(start_ts)` matches the Phase 1b notebook's canonical query (`notebooks/01-queries.ipynb`, Query 1 cell 4) and `_YIELD_BY_BOARD_LAST_WEEK_SQL` in `tests/test_parser/test_yield_query.py:28-43`. This gives deterministic replay against any fixture: the window floats with the data's actual range, so tests run correctly whether the fixture spans April 2026 or any other epoch. Anchoring on `CURRENT_TIMESTAMP` instead would require every test to mock time or pass `as_of` explicitly. Inclusive-on-both-ends boundary semantics matches the notebook's `>=` lower clause and the natural reading of "the last 7 days". DuckDB TIMESTAMP is naive — accepting only naive `datetime` from callers prevents silent UTC drift.

**Brief drafting note:** the original Session Brief said "anchor `MAX(panels.scheduled_ts)`" — that was a drafting error. `scheduled_ts` is when a panel was scheduled (could be future); `start_ts` is when testing actually happened. Plan Revision 1 corrected to `MAX(test_runs.start_ts)`. Decision Gate confirmed.

**Rejected:**
- **Anchor on `CURRENT_TIMESTAMP`.** Production-realistic. Cost: tests have to mock time everywhere.
- **No default — caller always passes `as_of`.** Most explicit. Cost: every call site has to compute `MAX(start_ts)` itself.
- **Exclusive upper bound (`< as_of`).** Common in streaming contexts. Cost: counter-intuitive for a "last 7 days" query (a row at exactly `as_of` is excluded).

**Revisit when:** A real Streamlit dashboard wants a live-clock anchor. Add an alternate constructor `yield_over_time_live(con, ...)` that wraps the existing function with `as_of=datetime.utcnow().replace(tzinfo=None)`. Don't change the default.

**Verification:** Y-01 (canonical SQL match), Y-04 (window excludes old rows), Y-05 (custom as_of override), R1-K (boundary inclusion at both ends), R1-M (tz-aware raises).

---

## 2026-06-16 — Empty-anchor short-circuit (`MAX(start_ts) IS NULL` → `[]`)

**Decision:** When `_resolve_anchor(con, as_of=None)` queries an empty `test_runs` table, the `MAX(start_ts)` query returns NULL → the helper returns `None`. Both public functions check the return: if `None`, they return `[]` immediately without executing the main SELECT. `failure_pareto` adds a secondary short-circuit: if the in-window `failures` set is empty (e.g. `by="refdes"` and all in-window failures have NULL refdes), return `[]`.

**Why:** Computing `anchor - INTERVAL ...` on a NULL anchor raises `TypeError: unsupported operand type(s) for -: 'NoneType' and 'datetime.timedelta'`. Computing `cumulative_pct = count / total` on `total == 0` raises `ZeroDivisionError`. Both classes of "empty input" should yield `[]` not an exception — they're a normal case (fresh DB, narrow window, restrictive filter). Short-circuit at the Python boundary (not in SQL) keeps the SQL itself simple and lets the empty-list pathway exercise a separate test case (Y-02, P-10, and the new `test_pareto_by_refdes_with_all_null_refdes_returns_empty_list`).

**Rejected:**
- **Raise on empty DB.** Caller has to wrap every call in try/except. Noisy for a normal state.
- **Return `[YieldRow(group_key="(no data)", ...)]`.** Sentinel rows are fragile; downstream code has to filter.
- **Run the SQL anyway and let `COALESCE(SUM(...), 0)` paper over it.** Doesn't help with the anchor-arithmetic crash; still needs a Python guard.

**Verification:** Y-02 (empty DB → `[]`), Y-03 (empty DB → `[]` for every group_by), P-10 (zero failures → `[]`), new `test_pareto_by_refdes_with_all_null_refdes_returns_empty_list`.

---

## 2026-06-14 — `.claude/settings.json` hook paths use `${CLAUDE_PROJECT_DIR}` (Option A)

**Decision:** All three hook commands in `.claude/settings.json` were changed from relative paths to project-root-relative absolute paths using the harness-substituted `${CLAUDE_PROJECT_DIR}` env var. Same fix stamped upstream into `E:\hrk-agent-starter\.claude\settings.json` so future stamps don't carry the bug.

```diff
-"command": "python .claude/hooks/block_dangerous_git.py"
+"command": "python ${CLAUDE_PROJECT_DIR}/.claude/hooks/block_dangerous_git.py"
```

(and similarly for `plan_approval_gate.py` + `doc_reminder_stop.py`).

**Why:** Relative paths in hook commands resolve against the shell session's cwd, not the project root. A single `cd notebooks/` mid-session shifts the resolved path to `notebooks/.claude/hooks/...`, which doesn't exist. The hook then errors with `No such file or directory`, exit code 1, and the harness treats that as a hard block on every subsequent Bash + PowerShell tool call. The sticky cwd persists across tool calls in the same shell session, so once the bug fires the only recovery is a fresh prompt (which resets the harness cwd). This actually happened mid-session on 2026-06-14 during the Phase 1b notebook session and killed the rest of the shell work for that turn (see BUG_LOG BUG-007 placement and SESSION_LOG entry for the notebook session).

`${CLAUDE_PROJECT_DIR}` is set by the Claude Code harness to the project root regardless of the shell session's current directory, so substituting it into the hook command produces an absolute path that's invariant under cwd drift.

**Rejected:**
- **Option B — hard-coded `python E:/flying-probe-copilot/.claude/hooks/...`.** Bulletproof on Windows even if `${CLAUDE_PROJECT_DIR}` substitution ever silently failed, but locks the path to one machine and one directory. The hrk-agent-starter portable kit stamps `.claude/settings.json` into every future project verbatim; hard-coded paths would break the moment a stamped project lives at a different path. Kept as a documented fallback if A ever fails on this Windows machine.
- **Wrap each hook script in a wrapper that does its own `cd` to project root.** Adds a layer of indirection inside the hook itself and still requires every hook script author to remember the discipline. Fixing the *config* (one place) beats fixing the *contract* (every hook).
- **Leave it broken and just train myself to never `cd` into a subdir mid-session.** Discipline can't be enforced; the agent is the one running `cd` and surrenderingt control. The first `cd` into any sub-directory is a session-killer.

**Verification:** Smoke test in the same session as the edit — `cd notebooks && pwd && cd ..` succeeded immediately after the change. Under the bug this sequence hard-blocked with `PreToolUse:Bash hook error: ... No such file or directory`. The smoke test proves the harness IS substituting `${CLAUDE_PROJECT_DIR}` on this Windows machine, so Option A is sufficient.

**Revisit:** If a future Claude Code release ever changes `${CLAUDE_PROJECT_DIR}` substitution behaviour, or if the kit gets stamped on a non-Windows platform that handles the variable differently. The fallback to Option B is documented above; switching is a one-line edit per command.

---

## 2026-06-14 — Phase 1b: DuckDB schema shape (boards + panels split, global components, persisted limits, ParseReport, runs metadata)

**Decision:** The Phase 1b DuckDB schema uses 9 tables organised as 5 dimension + 1 metadata + 3 fact:

- **Dimensions:** `boards` (board profiles only — small/medium/large + their BOM metadata; ~3 rows ever), `panels` (per-serial unit-under-test instances; one row per panel ever produced), `operators` (per `operator_id` seen in `@BATCH`), `components` (global per `(board_profile_id, refdes)` — N=~120 for small, ~450 for medium, ~1600 for large — looked up at ingest with `INSERT OR IGNORE` on the `UNIQUE` index), `tests` (per `(board_profile_id, block_designator, record_type)`).
- **Metadata:** `runs` (one row per generator run-directory ingested; columns sourced from `manifest.json` plus the directory basename as `run_id` and `ingested_at` defaulted to `CURRENT_TIMESTAMP`).
- **Facts:** `test_runs` (one per `@BTEST` record per panel), `measurements` (one per `@A-*` / `@D-T` / `@TS` / `@TJET` / `@PF` record, with type-specific nullable columns including `limit_high`/`limit_low`/`limit_nominal` from `@LIM2`/`@LIM3`), `failures` (denormalized convenience table: one row per non-PASS measurement, with `panel_serial` + `board_profile_id` carried for fast Pareto without joins).

The parser returns a structured `ParseReport` (errors + notes + record_count) rather than logging silently — testable, audit-friendly.

**Why:** All four decisions came from the Phase 1b brief's Step 2 explore + the owner's pre-plan answers:

1. *boards (profile) vs panels (instance) split:* "yield by board over last week" reads naturally as per-profile aggregation for a manufacturing engineer (small profile = X% yield); per-serial yield would be 100%/0% noise. The split keeps the semantic clean and lets the same `panels` table back per-serial drill-downs in Phase 2 dashboards.
2. *Components global per (profile, refdes):* per-panel rows would explode the components table 100–1000× and make cross-panel "how does R12 behave?" queries expensive. Global per (profile, refdes) keeps the dim stable.
3. *Limits persisted as nullable columns:* +3 nullable floats per measurement row is cheap. Without them, Phase 2 "which measurements failed because spec tightened" queries would have to re-parse logs or re-derive from the spec — both lossy.
4. *ParseReport object:* testable assertions on error counts + line numbers; matches the brief's "captured in a `parse_report` or logged" success criterion line.
5. *runs metadata table from manifest:* free during ingest; enables cross-run comparison queries ("compare fault rates across runs") and is the natural anchor for the re-ingest guard (#WARNING-13 below).

**Rejected:**
- *Single `boards` table conflating profile + instance* — wrong semantics for the named exit query; would have forced per-serial yield aggregation.
- *Per-panel `components` rows* — table size explosion + duplicate-key handling pain on every ingest.
- *Skip limits* — irrecoverable for downstream Pareto analysis.
- *Silent error logging instead of ParseReport* — untestable.
- *Skip manifest ingest* — single-run-only parser, no cross-run comparison.

**Test contracts pinned:**
- `tests/test_parser/test_schema.py::test_init_database_creates_all_9_tables` — `TABLES` constant length == 9; `SHOW TABLES` set-equals constant.
- `tests/test_parser/test_schema.py::test_each_table_has_expected_columns` — per-table column shape audit.
- `tests/test_parser/test_ingest.py::test_ingest_components_global_per_profile_refdes` — re-ingesting the same panel twice leaves `components` row-count unchanged for that profile.

**Revisit:** End of Phase 2. If the failures denormalization shows drift symptoms (e.g. `failures.board_profile_id` differs from the joined `panels.board_profile_id`), add a constraint or a periodic reconciliation query. If the surrogate-PK Python counter approach proves slow on >1M-row ingests, swap to DuckDB sequences.

---

## 2026-06-14 — Phase 1b: `test_runs.operator_id` nullable; per-panel operator recovery deferred to Phase 2

**Decision:** `test_runs.operator_id` is declared `VARCHAR` (nullable), not `VARCHAR NOT NULL`. The parser populates it from the single `@BATCH.operator_id` field on the per-board log file. Per-panel operator recovery (which the generator currently does NOT preserve in per-board logs) is deferred to Phase 2.

**Why:** Per-board `.log` files contain `@BATCH.operator_id` once. The generator's `cli.py:140` uses `boards[0].panel.operator_id` for that field — so every per-board file in a run inherits the first panel's operator. The actual per-panel `PanelInstance.operator_id` is preserved only in `results.json` / `results.csv`, which the brief explicitly excluded from ingest. Three repair options were considered:
- Edit the generator to add `operator_id` to `@BTEST` — out of Phase 1b scope (generator edits prohibited).
- Read `results.json` as a sidecar during ingest — violates the brief's "log files only" promise.
- Use `@BATCH.operator_id` and document the degradation — chosen.

Making the column nullable converts a silent-degraded-data risk into an explicit "this column may be incomplete" contract, which downstream analytics + dashboards can opt into respecting.

**Rejected:**
- *`NOT NULL` constraint:* would have crashed ingest on the first panel of any run that didn't expose an operator anywhere — and silently degraded data on every run that did, since every panel in a run gets the same operator.
- *Generator change in Phase 1b:* out of scope, scope-creep risk.
- *`results.json` sidecar read:* violates the brief's CSV/JSON-not-ingested commitment.

**Test contract:** No specific test for nullability today; the schema's column declaration + `init_database` idempotency tests verify the column is `VARCHAR` without a `NOT NULL` modifier. Phase 2's operator-id repair will need a dedicated test.

**Revisit:** Phase 2 first session. Decide whether to extend `@BTEST` (generator change) or to ingest `results.json` as an authorized sidecar. Either path lets the column flip to `NOT NULL` if we want strict integrity.

> **Resolved 2026-06-16** — Path A landed via `feature/per-panel-operator` (see plan `docs/plans/2026-06-14-phase2-operator-plan.md` + brief `docs/plans/2026-06-14-phase2-operator-brief.md` + BUG_LOG entry BUG-009). `@BTEST` now carries a mandatory `operator_id` at positional index 12; `test_runs.operator_id` is `VARCHAR NOT NULL`; multi-operator runs ingest with per-panel-distinct operators (`tests/test_parser/test_ingest.py::test_multi_operator_run_distinct_operators_per_panel`). `results.json` sidecar path NOT taken — log files remain the single source of truth.

---

## 2026-06-14 — Phase 1b: re-ingest guarded at CLI, not at schema (single-run idempotency contract)

**Decision:** The parser CLI does a pre-flight `SELECT 1 FROM runs WHERE run_id = ?` before any insert. If the run is already present, the CLI exits with code 2 and a stderr message. The schema itself is NOT idempotent on fact tables (`panels`, `test_runs`, `measurements`, `failures` would all PK-conflict or duplicate on re-insert). Dimension tables use `INSERT OR IGNORE` semantics (`boards`, `operators`, `components`, `tests` — shared across runs).

**Why:** Two options were on the table — make the entire ingest idempotent (UPSERT everywhere) or guard at the CLI. The guard approach is simpler for v1: it surfaces a clear error to the operator ("this run is already ingested; use --overwrite in Phase 2"), prevents accidental double-counting in yield/Pareto queries, and avoids the complexity of teaching every fact table how to dedup against an in-progress ingest. UPSERT-everywhere would also have masked partial-ingest failures (half a run already in, second attempt silently completes the other half).

**Rejected:**
- *UPSERT every table:* hides partial failures and over-promises idempotency on facts that genuinely shouldn't double-count.
- *Silently allow duplicates and let Phase 2 dedup at query time:* poisons analytics until the dedup layer ships.
- *No re-ingest support at all (exit code 0 + skip):* hides operator intent — the operator may have wanted to re-ingest to refresh after a parser bug fix.

**Test contracts:**
- `tests/test_parser/test_cli.py::test_cli_exits_with_code_2_when_run_already_ingested` — pin the CLI behaviour.

**Revisit:** Phase 2. Add `--overwrite` flag that performs `DELETE FROM <table> WHERE run_id = ?` across fact tables before re-inserting. Or add `--append` that ignores the guard and lets duplicates accumulate (useful for stress testing).

---

## 2026-06-14 — Fault correlation wired through `generate_blocks` (addendum to 2026-06-13)

**Decision:** The refdes-numerical clustering heuristic documented in the 2026-06-13 entry below now actually fires during panel generation. `generate_blocks` (in `src/flying_probe_copilot/generator/blocks.py`) picks the primary failing component as before, then calls a new `_pick_correlated_failures(primary, profile, rng)` helper that performs per-candidate Bernoulli secondary-failure draws against same-family components. The candidate draw uses `rate = BASELINE_SECONDARY_RATE * correlation_multiplier(primary, candidate)` with `BASELINE_SECONDARY_RATE = 0.3`, and the draw is **only performed when `correlation_multiplier > 1.0`** (i.e., for ±3 refdes neighbors). Far candidates and cross-family candidates get no secondary draw.

**Why:** PR #1 landed `correlation_multiplier` and `correlated_failure_rate` in `faults.py` with unit tests, but they were never invoked from the CLI output path. `_pick_failing_component` marked exactly one component as failing per panel, so the realistic clustered-failure Pareto curves the heuristic was designed to produce never appeared in real generator output. Bugbot caught this in PR #3 review (comment id 3409766432, medium severity). The fix wires the existing heuristic into the panel-construction pipeline so it actually does its job.

The "multiplier > 1.0 only" gate matters: applying the baseline to every same-family component (multiplier == 1.0 for far candidates) would produce uniform secondary noise across the whole family and visually dilute the ±3 cluster around the primary. Gating on multiplier > 1.0 keeps far candidates clean and lets the Pareto curve show real clustering. `correlation_multiplier`'s contract is unchanged; only the *integration interprets* a 1.0 return as "no secondary draw."

**Rejected:**
- **Apply baseline to all same-family candidates** (uniform secondary rate, neighbors only get a multiplicative bump). Produces no visible aggregate Pareto signal — far candidates outnumber near ones and their cumulative secondary fails wash out the cluster.
- **Bias the primary draw with the multiplier instead of doing secondary Bernoulli draws.** Changes what `_pick_failing_component` *means* (no longer uniform across the family) and complicates seed-reproducibility tests. Per-panel secondary draws keep the primary draw clean and add clustering as a separate orthogonal layer.
- **Higher baseline (e.g. 0.5).** Empirically reaches the same Pareto target but makes failing panels dominated by 3–5 simultaneous component fails, which over-states realistic FP/ICT failure patterns. 0.3 was chosen as the lowest value that comfortably meets the test thresholds in `tests/test_generator/test_blocks.py` while keeping per-failing-panel fail counts in the 1–4 range.

**Test contracts pinned (`tests/test_generator/test_blocks.py`):**
- `test_neighbor_fail_rate_elevated_vs_far_when_primary_pinned` — 500 seeded panels with primary monkeypatched to R50: combined R49+R51 fail counts ≥ 3× R10 fail count.
- `test_failure_pareto_clusters_around_primary_under_correlation` — 1000 seeded panels with primary monkeypatched to R50: top-3 failing refdes account for >30% of all failures (and the top-3 must include R50 plus at least one ±1 neighbor).
- `test_correlation_secondary_fails_stay_within_same_family` — 500 seeded DIGITAL panels with primary pinned to U8: zero cross-family secondary fails.

**Revisit:** When Phase 2 analytics surface the failure Pareto. If clustering looks too tight (always exactly R50 ±1) or too loose (per-panel fail counts ≥5), retune `BASELINE_SECONDARY_RATE` rather than the multiplier table — the multiplier is the heuristic's public contract.

---

## 2026-06-14 — Dedicated `exec` sub-agent with hard tool restrictions

**Decision:** Step 5 of the 10-step session-workflow uses a dedicated `exec` sub-agent defined at `.claude/agents/exec.md`, with a tool allowlist enforced by the agent definition itself. Other sub-agent roles (Explore, Plan-Reviewer, Verifier) continue to use the built-in `Explore` agent type or the existing skills.

**Why:** Skills can *advise* a sub-agent on scope discipline; an agent definition can *enforce* it via tool restrictions. The executor is the highest-blast-radius role (it's the one writing files), so tool-level guardrails are most valuable there. Specifically, the `exec` agent cannot spawn further sub-agents (no recursion), cannot fetch the web, cannot control the browser or desktop, cannot enter/exit plan mode, and cannot invoke nested workflows — even if a misread plan instruction tries to make it.

**Rejected:**
- Custom agents for every role (Explore, Plan-Reviewer, Verifier, Exec). Diminishing returns — Explore is already well-served by the built-in `Explore` agent type, and the other roles benefit more from skill-level prompting than tool restriction.
- Continuing to rely on `execute-plan` skill alone. A skill is advisory; the executor could ignore it. Tool restrictions cannot be ignored.

**Revisit:** End of Phase 1b. If the executor's tool list turns out to be too restrictive (e.g. we discover legitimate need for `WebFetch`), expand the allowlist deliberately rather than dropping restrictions wholesale.

---

## 2026-06-14 — Tier-based step selection for the 10-step workflow

**Decision:** The 10-step loop is no longer uniformly applied. Sessions classify as Trivial (Steps 1, 7, 8), Small (1, 3, 5, 7, 8), Medium (1, 2, 3, 5, 7, 8), or Large (full 1–10). Tier is chosen at Step 1 using the five-minute decision rule in `.claude/templates/tiering.md`. Mid-session escalation is allowed via the escalation protocol (STOP → log → reset brief → restart at the new tier's correct step).

**Why:** Running the full loop on a typo fix or a 50-LOC helper is ~4–8x token overhead with near-zero quality gain. Step 6 (Verify Execution) in particular has the lowest yield-per-token in the loop because Step 7 (parent Triple Check) already catches what Step 6 would. Tiering preserves rigor where it matters (parser, schema, RAG core) and removes it where it doesn't (config tweaks, doc edits).

**Rejected:**
- Two-tier system (fast path vs full loop). Too coarse — most Phase 1a work falls between "typo" and "build the parser".
- Letting sub-agents self-select tier. Parent owns this — sub-agents see only their assigned tier's charter.

**Revisit:** After 5 full-loop sessions of real Phase 1a/1b work. If Step 6 catches something Step 7 missed, restore Step 6 to Medium tier.

---

## 2026-06-14 — Context-cache brief block for sub-agent prompts

**Decision:** Every sub-agent dispatch in a Medium or Large tier session is prefixed with a byte-for-byte identical "context brief" block, templated at `.claude/templates/sub-agent-brief.md`. The brief contains phase, tier, branch, guardrails-in-force, decisions-in-force, OUT-OF-SCOPE, fixtures-to-leave-alone, and resolved open questions.

**Why:** Two reasons:
1. **Direct context savings.** Without the brief, each sub-agent reads CLAUDE.md (~150 lines) + agent-conduct.md (~80 lines) + the relevant phase doc to learn the rules — ~3-5k input tokens per dispatch, or ~12-20k across a 4-sub-agent Large-tier loop.
2. **Prompt-cache prefix reuse.** Anthropic prompt caching keys on identical token prefix with a 5-minute TTL. An identical brief across the 4 sub-agents of one loop pays the prefix cost once and reads cache (~10x cheaper) on the other three. See `.claude/templates/prompt-caching.md` for the mechanics and timeline.

**Rejected:**
- Letting sub-agents read CLAUDE.md fresh each time. Wasteful; same content re-encoded each call.
- Including volatile content (diffs, test output) in the brief. Breaks the cache. Volatile content goes in the role-specific tail of the prompt, not the brief.

**Revisit:** After 3 Medium/Large sessions, measure `cache_read_input_tokens` vs `input_tokens` ratio. Target: >60% cache reads on dispatches 2–4 of a loop. If lower, the brief is drifting between calls — investigate and tighten.

---

## 2026-06-13 — Phase 1a: log format target = real Keysight Log Record Format (not simplified text report)

**Decision:** The synthetic generator emits files in the **real Keysight i3070 Log Record Format** — a record-oriented format with `{@PREFIX|field|...}` syntax, numeric status codes (no literal `"PASS"`/`"FAIL"` strings), scientific-notation floats (`+1.246700E+01`), CRLF Windows-1252 encoding by default, `@LIM2`/`@LIM3` limit subrecords following analog records, and full `@BTEST` status-code vocabulary. NOT the originally-drafted simplified human-readable text-report format.

**Why:** The spec drafted at Phase 0 described a sectioned text report (Header / Shorts / Analog / Digital / Summary) because the owner did not have Keysight manuals locally. Phase 1a Step 2 external-research subagent found the authoritative format chapter (Keysight "i3070 Log Record Format") publicly mirrored in the Virinco WATS-Client-Converter GitHub repo, with the format chapter as a PDF + an independent regex grammar in a C# parser (LGPL-3.0). With the real format in hand, generating the simplified format would have produced output that any manufacturing engineer who has used an i3070 would immediately recognize as fake — defeating the portfolio purpose. The real format raises renderer complexity from ~150 LOC to ~400 LOC, but every test, sample, and downstream phase becomes a precise simulation of real ICT output. The Phase 1b parser will be a defensible Python equivalent of the Virinco C# parser.

**Rejected:**
- **Simplified format as written** — easier and faster but loses portfolio credibility; Phase 1b parser would target a custom format with no real-world consumers.
- **Dual-format support** (real + simplified) — too much scope for v1; the simplified format has no consumer.

**Revisit:** After Phase 1b — if the parser confirms the format is correct against the generator output. If owner ever regains access to real i3070 logs at work, cross-check the real-vs-synthetic output for the remaining unknowns listed in `specs/synthetic-log-generator.md` "Open items".

**Guardrail compliance:** No verbatim Keysight or Virinco text copied into source. Grammar regexes derived from format-chapter field descriptions in the spec; Virinco repo cited only as cross-validation reference in `grammar.py` module docstring. Cached PDF + LGPL source files were deleted from `.cache_research/` and from repo root before Step 5 execution.

---

## 2026-06-13 — Phase 1a: @BTEST status derivation = categorical precedence rule

**Decision:** `models.derive_btest_status(blocks)` derives the overall `@BTEST` status from contained subtest statuses using **categorical precedence**: scan failing subtest records in this order, first match wins:

1. `FAIL_SHORTS` (4) — `@TS` shorts records
2. `FAIL_ANALOG` (6) — `@A-*` analog records (any of 14 types)
3. `FAIL_DIGITAL` (8) — `@D-T` digital records
4. `FAIL_PIN` (2) — `@PF` pins-failed records
5. `FAIL_TJET` (14) — `@TJET` VTEP records
6. `FAIL_POLARITY` (15) — `@PCHK` records (deferred Phase 5; placeholder in code)
7. `FAIL_CCHK` (16) — `@CCHK` connect-check records (deferred Phase 5; placeholder)
8. `FAIL_FUNCTIONAL` (9) — functional records (deferred; placeholder)
9. `FAIL_POWER` (7) — power-supply records (deferred; placeholder)
10. `FAIL_UNCATEGORIZED` (1) — catch-all (placeholder)

If no failures, return `PASS` (0). Environmental codes (`FAIL_HANDLER=11`, `FAIL_BARCODE=12`, `XD_OUT=13`, `RUNTIME_ERROR=80`, `ABORTED_STOP=81`, `ABORTED_BREAK=82`) are NEVER returned by this function — set externally by the orchestrator.

**Why:** Keysight's format chapter does not document an explicit precedence ordering for `@BTEST` status — only the categorical meaning of each code. Conventional ICT test ordering runs shorts → analog → digital → functional, and if shorts fails, the board is invariably reported as a shorts-failure regardless of what else fails downstream (shorts tests run first and gate the rest). The chosen precedence matches that operational logic and is defensible to a manufacturing engineer.

**Rejected:**
- **"First non-PASS encountered, in record order"** — simplest but semantically wrong. A board that has an analog test fail before the shorts test runs would be reported as analog-fail, which is wrong.
- **"Numerically smallest non-zero status code"** — would happen to match this ordering in most cases (4 < 6 < 8 < 14 < 15 < 16), but is a coincidence not a contract; doesn't gracefully extend if new codes are added.

**Revisit:** If the Phase 1b parser, when fed real customer logs (if owner ever gains access), reveals a different precedence is used in practice. Until then, the chosen ordering is the project's canonical synthesis convention.

**Forward extensibility:** The `_PRECEDENCE` list in `models.py` includes all 10 categories. The 5 deferred ones (POLARITY, CCHK, FUNCTIONAL, POWER, UNCATEGORIZED) have `lambda r: False` predicates today; a Phase 5 addition only needs to swap the predicate.

---

## 2026-06-13 — Phase 1a session: branch merge fast-path (one-time exception)

**Decision:** During Phase 0 cleanup at the start of the Phase 1a session, three in-flight feature branches (`fix/commit-uv-lock`, `feature/gitignore-data-synthetic-v2`, `feature/pyproject-dependency-groups`) were merged **directly to `main`** with `--no-ff`, instead of the canonical `feature/* → dev → main` flow specified in the branching-strategy decision. `dev` was then fast-forwarded from `main` to keep the two permanent branches in sync.

**Why:** Solo portfolio project. The three branches each contained small, isolated, non-conflicting changes (uv.lock commit, gitignore broadening, PEP 735 migration). Routing each through `dev` first would have meant 6 merge commits + 3 fast-forwards for content already owner-approved. The fast-path takes 4 merges total with no loss of history or attribution.

**Rejected:**
- **Canonical `feature/* → dev → main`** — correct per the branching-strategy decision but adds ceremony without adding clarity for a solo project. Original strategy decision explicitly says "Lowest overhead, cleanest history" as the rationale — fast-path is more consistent with that intent for this specific case.

**Scope of exception:** This applies ONLY to the 3 branches landed during Phase 0 cleanup at the start of the 2026-06-13 Phase 1a session. The canonical flow remains the default for all subsequent work.

**Revisit:** Never. One-time exception for one specific cleanup. Phase 1b and later sessions use the canonical flow.

---

## 2026-06-13 — Phase 1a: fault correlation = refdes-numerical clustering heuristic

**Decision:** Within-panel fault correlation in `faults.py` uses a **refdes-numerical clustering heuristic** rather than an explicit net-graph. When a component fails, components whose refdes differs by ±1 in the same family (R12 ↔ R13) receive a `1.5×` failure-rate multiplier; ±3 receives `1.2×`; further gets baseline `1.0×`. No `BoardProfile.net_adjacency` field is added in v1.

**Why:** The spec requires fault correlation to produce realistic Pareto curves (clustering rather than flat noise). A faithful net-graph would require either modeling actual board topology (out of scope) or synthesizing a random adjacency matrix per panel (extra state + reproducibility complications). Refdes-numerical clustering exploits the real-world tendency for adjacent reference designators to share routing concerns — it's a synthesis convenience that produces visibly clustered failure patterns without inflating the data model.

**Rejected:**
- **Explicit net-graph in `BoardProfile`** — out of v1 scope; would require generating a topology that doesn't currently inform anything else.
- **Per-panel random adjacency matrix** — adds state, complicates seed-reproducibility tests, and provides no realism benefit over a clustering heuristic.
- **No correlation at all** — produces unrealistic flat-noise Pareto curves; defeats the realism rule in the spec.

**Documented as a heuristic, not a physical claim:** `faults.py` module docstring states this is "a synthesis convenience, not a physical claim." If the project ever needs to claim physical realism (e.g., for a published paper), the heuristic would need to be replaced.

**Revisit:** When Phase 2 analytics surface (failure Pareto + SPC). If clustering looks "too clean" or "too noisy", retune the multipliers or move to a sparse adjacency model.

---

## 2026-06-13 — Synthetic data `.gitignore` — samples-only allow-list

**Decision:** `.gitignore` excludes `data/synthetic/*` broadly and re-includes only `data/synthetic/samples/`. Bulk generator outputs (20–50 MB `results.csv` / `results.json` from 1k-panel runs) must go to `data/synthetic/<run_id>/` or any sibling of `samples/` — never into `samples/` itself. Only deliberately curated small example files belong in `samples/`.

**Why:** A `git add .` after a generator run would otherwise drop ~50 MB blobs into the index and blow past GitHub's 100 MB file limit (or at minimum bloat the repo). Guardrail #4 in CLAUDE.md ("all committed data is synthetic") does not mean all synthetic data should be committed — only small samples for documentation / parser fixtures.

**Implementation notes:**
- Used `data/synthetic/*` (not `data/synthetic/`) because the trailing-slash form blocks gitignore re-include rules for any subpath of the excluded directory. The `/*` form excludes one level of entries and lets `!data/synthetic/samples/` actually take effect.
- Also narrowed the existing `!data/synthetic/**/*.log` re-include to `!data/synthetic/samples/**/*.log` so a bulk run's `.log` files don't sneak back in via the broader `*.log` rule.
- `data/synthetic/samples/.gitkeep` committed so the samples dir exists in fresh clones.

**Rejected:** Per-extension exclude (`data/synthetic/**/*.csv`, `**/*.json`) — fragile; a new output format would silently slip through. Excluding by size — git doesn't natively support it.

**Revisit:** If the generator gains a "minimal demo" output mode that's small enough to commit alongside parser fixtures, place those under `samples/` and document the convention in the generator's spec.

---

## 2026-06-13 — Branching strategy: Option A (feature/* → dev → main)

**Decision:** Two permanent branches (`main`, `dev`). All work on short-lived `feature/[name]` branches. Merge feature → dev as tasks complete; dev → main at phase boundaries.

**Why:** Solo portfolio project. ROADMAP.md already tracks phase gates — git branches don't need to mirror them. Lowest overhead, cleanest history.

**Rejected:** Option B (phase/[name] branch layer between feature and dev). Adds merge ceremony without adding clarity for a solo project.

**Revisit:** After first contributor joins — may layer in phase branches then.

---

## 2026-06-13 — hrk-agent-starter as portable governance kit

**Decision:** All AI agent skills, hooks, rules, and log templates live in a separate repo (`-hrk-agent-starter` on GitHub). New projects are stamped via `stamp.ps1` or GitHub template. Skills are owned by the kit repo; project-specific adaptations live in the project.

**Why:** Owner wants to start any future project with the same governance discipline without rebuilding it from scratch each time. Single source of truth for skills means improvements propagate across all future projects.

**Rejected:** Keeping skills only in each project (no canonical source, diverges over time). Git submodule (too much overhead for a stamp-and-forget workflow).

**Revisit:** After 2-3 projects stamped — decide whether to version the kit with releases.

---

## 2026-06-13 — 10-step multi-agent loop as canonical workflow

**Decision:** The session-workflow skill defines a 10-step loop with specific agent roles. Steps 3 (Plan) and 7 (Triple Check) are parent-only and can never be delegated. Out-of-scope bugs are logged immediately and surfaced via spawn_task at step 8.

**Why:** The triple comparison (Found vs Planned vs Executed) catches executor drift, report inflation, and plan gaps — three failure modes that aren't caught by tests alone. The explicit handoff step ensures no context is lost between sessions.

**Rejected:** Simpler linear pipeline with no triple check. Catches fewer failure modes.

**Revisit:** After Phase 1b — tune step count and agent charters based on real usage.

---

## 2026-06-13 — Governance system adopted from my-assembly-hub

**Decision:** Use the same agent-governance pattern as `my-assembly-hub`:
hooks (block_dangerous_git, plan_approval_gate, doc_reminder_stop), rules (agent-conduct,
session-workflow, testing), skills (plan-architect, execute-plan, test-generator, session-workflow,
diagnose), and log files (BUG_LOG, DECISION_LOG, AGENT_HANDOFF_LOG, SESSION_LOG).

**Why:** Owner already runs assembly-hub this way successfully. Consistent pattern across projects
means zero ramp-up time. The governance layer enforces discipline without needing to re-explain it.

**Rejected:** A lighter-weight approach (just CLAUDE.md). Too easy to skip steps on a portfolio project
that no one else is reviewing.

**Revisit:** After Phase 2 — add skills for analytics-specific patterns if needed.

---

## 2026-06-13 — TDD as the default workflow

**Decision:** Tests are written before implementation in every phase. Red → Green → Refactor.
No implementation is committed without a corresponding test.

**Why:** Portfolio project — demonstrates software engineering discipline. Also prevents silent bugs
in the synthetic-data → parser → DuckDB pipeline where a wrong value produces wrong analytics silently.

**Rejected:** Build-then-test. Explicitly rejected by owner.

**Revisit:** Never. Standing rule.

---

## 2026-06-13 — Tech stack locked

**Decision:** Python 3.11+, uv, DuckDB, ChromaDB + sentence-transformers + rank-bm25,
Gemini API (primary LLM), Claude API (backup), Streamlit + Plotly.

**Why:** Full AI engineering stack on a portfolio-demonstrable footprint. DuckDB handles
analytical queries without a server process. ChromaDB + BM25 gives hybrid retrieval.
Streamlit keeps the UI fast to build. Gemini is free-tier friendly for portfolio work.

**Rejected:** PostgreSQL (overkill for local-only), React frontend (too much overhead for
a solo portfolio project), OpenAI as primary (cost + Gemini is sufficient).

**Revisit:** After Phase 3 — if Gemini quality disappoints, switch to Claude API.

---

## 2026-06-13 — HP3070 / Keysight i3070 log format as v1 target

**Decision:** Target HP3070-style flying-probe logs as the only supported format in v1.
Generic multi-format parser is deferred.

**Why:** Narrow scope = shippable within the timeline. HP3070 is the format the owner
encounters most in their professional context. Good enough for portfolio demonstration.

**Rejected:** Multi-format parser in v1 (too broad; makes Phase 1a unbounded).

**Revisit:** After Phase 1b — decide if Takaya format is worth adding for variety.

---

## Template

```
## YYYY-MM-DD — Short title

**Decision:** What was decided, in plain English.

**Why:** The reason — include constraints, tradeoffs, and stakeholder input.

**Rejected:** What alternatives were considered and why they were ruled out.

**Revisit:** When (phase boundary, date, condition) and what might change the decision.
```
