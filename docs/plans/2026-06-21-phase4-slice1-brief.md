## Session Brief — 2026-06-21 — Phase 4 slice 1 (README polish + portfolio writeup)

### What the owner wants
> "phase 3 is completed lets start phase 4" → picked "README polish + portfolio writeup
> (Recommended)" from the slice menu, then "done" after merging the Phase 3 promotion PR
> ([#29](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot/pull/29)).

Phase 4 — Polish. Slice 1 is the public-facing repo polish so the project reads as a finished
portfolio piece: a top-level README that explains the system to a Manufacturing Engineering
hiring manager in under 60 seconds, an architecture diagram a recruiter can grok at a glance,
real dashboard screenshots, and a case-study writeup suitable for the owner's portfolio site
landing page.

### Goal statement (one sentence)
Rewrite [README.md](README.md) (currently stuck at Phase 0 wording), add a real architecture
diagram, capture Streamlit-dashboard screenshots of the 6 pages, and draft a
[docs/case-study.md](docs/case-study.md) long-form writeup — so a Dallas-area EMS hiring
manager (Celestica / Jabil / Sanmina / Lockheed) can grok the project's value, scope, and
technical depth from the GitHub landing page in one sitting.

### Success looks like
- **README.md** opens with a one-paragraph problem statement, a one-paragraph solution
  statement, a screenshot strip / hero image, a 60-second "what this does" elevator, then the
  technical sections (architecture, stack, install, run, project structure, status). Phase 0
  wording removed. Status reflects Phase 3 shipped + Phase 4 in progress.
- **Architecture diagram** replaces the ASCII-art block — either an embedded Mermaid diagram
  (renders natively on GitHub) or an SVG checked into `docs/img/`. Shows: log → parser → DuckDB
  → analytics + RAG → Streamlit, with the 6 dashboard pages called out.
- **Dashboard screenshots** under `docs/img/`: at minimum Overview, Yield, Pareto, SPC,
  Anomalies, Co-Pilot pages — captured locally against the sample DB. README references them.
- **docs/case-study.md** is the long-form writeup: problem framing, scope decisions (why
  synthetic data, why local-only, why Streamlit), architecture story, RAG-specific design
  choices (hybrid retrieval, anti-hallucination grounding, env-gated live eval), and
  results / metrics (519 tests, 97% coverage, 10/10 eval, 37s end-to-end live latency).
  ~1,500–2,500 words, written for a smart-but-non-AI reader. Embeddable on the portfolio site.
- Doc lint: no broken internal links, no leftover "TODO", no Phase 0 status anywhere, no
  guardrail violations (no IPC verbatim, no Keysight wholesale, no real customer data).
- Suite still green: `uv run pytest -q --no-cov` passes — no test edits expected this slice.

### Out of scope (explicit)
- ❌ **Demo gif / screen recording** — separate Phase 4 slice (slice 2).
- ❌ **Test/coverage hardening** — separate Phase 4 slice (slice 3).
- ❌ **SDK migration** (`google-generativeai` → `google-genai`) — chipped as
  [task_decc4276](spawn_task chip), separate session.
- ❌ **Approval-gated edits**: `pyproject.toml`, `src/flying_probe_copilot/db/schema.py`,
  any `migrations/*`, `.claude/settings.json`, `.env.example`. **`CLAUDE.md`** edits are
  limited to the Step-10 session-log line + the Phase-4 status block.
- ❌ **Code changes** under `src/flying_probe_copilot/**` (this is a docs slice; if a real code
  bug is found, surface it via spawn_task chip — do NOT fix silently).
- ❌ **Cloud deployment / hosting**. Per CLAUDE.md don't-do list: "Don't deploy to cloud in v1."
- ❌ **Real customer data, IPC verbatim text, proprietary Keysight wholesale text** — hard
  guardrails per CLAUDE.md + `docs/GUARDRAILS.md`. Screenshots must show synthetic data only.
- ❌ **Repo-wide doc audit beyond README + case-study**. `docs/ROADMAP.md`, `docs/DECISIONS.md`,
  `docs/SCOPE.md`, etc. stay as-is this slice (those are working docs, not portfolio surface).

### Phase / milestone
ROADMAP Phase 4 — delivers the README + writeup portion of "Public GitHub repo with README,
demo gif, case-study writeup on portfolio site". Demo gif is slice 2.

### Branch
`feature/phase4-slice1-readme` — off `origin/dev` (clean; created 2026-06-21 after PR #29 merge).

### Dependencies
- Streamlit is already locked + green for capturing screenshots locally. Sample DuckDB exists
  at `data/db/sample.duckdb` (gitignored — must be regenerated locally to capture screenshots).
- Mermaid renders natively on GitHub — no new dep if we choose that route. SVG also fine.
- No new dependencies expected (all pure docs + screenshots).

### Tier estimate
**Medium.** Substantial multi-file authoring (README + diagram + 6+ screenshots + case-study),
but no tests, no production code, no schema, no approval-gated edits. Reduced loop appropriate:
Steps 1 → 2 (Explore — what to highlight) → 3 (Plan — file table) → 5 (Verify Plan — red-team
the draft) → 6 (Decision Gate) → 7 (Execute) → 8 (Verify Execution — link-check + read-through)
→ 9 (Triple Check) → 10 (Docs/commit). Skip Step 4 (no tests). Step 11 Manual QA = owner reads
the rendered README on GitHub.

### Open questions for the owner before Decision Gate
1. **Diagram format**: Mermaid (renders inline on GitHub, edits as text, no binary churn) vs.
   SVG (more visual control, opens in any tool, but binary in git). Default recommendation:
   **Mermaid** unless you want pixel-perfect control.
2. **Case-study location**: `docs/case-study.md` in this repo (canonical, version-controlled),
   or draft only here and you copy to the portfolio site? Default: **both** — markdown in the
   repo, copy/adapt to portfolio site.
3. **Screenshot data**: regenerate `data/db/sample.duckdb` locally and capture against that, or
   use the existing sample DB if you have one staged? Either way, must be **synthetic only**.
4. **README hero image**: text-only README, or include a single hero screenshot at the top
   (e.g. the Co-Pilot chat page answering a real question)? Default recommendation: **hero**.
5. **Case-study length**: 1,500-word skim or 2,500-word deep dive? Default: **2,000ish**.
