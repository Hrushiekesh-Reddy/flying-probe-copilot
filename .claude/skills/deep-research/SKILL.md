# Skill: deep-research

> Invoke: `/deep-research`
> Multi-source research with adversarial verification and cited output.
> Use when you need to understand a library, API, framework, or domain topic deeply before building.
> See /skill-sergeant for routing.

---

## When to use

- "How does X library work?" before using it for the first time
- "What's the best way to implement X?" when multiple approaches exist
- "Research X" on a domain topic (e.g., HP3070 log format, DuckDB query patterns)
- Before writing a /plan-architect for a feature that uses an unfamiliar API
- "Find the official documentation for X"

## When NOT to use

- When you already know the answer well enough to act
- Code implementation (use /execute-plan after research)
- Post-implementation verification (use /verify-execution)

---

## Step 1 — Define the research question

State clearly:
```
QUESTION:   [specific question — not vague]
SCOPE:      [what to cover / what to exclude]
DECISION:   [what decision will this research inform?]
GOOD-ENOUGH: [what level of answer is sufficient to proceed?]
```

A vague question produces a vague answer. Be specific:
- Bad:  "How does DuckDB work?"
- Good: "What are DuckDB's supported Python data types for INSERT and what's the recommended bulk load pattern for >100k rows?"

---

## Step 2 — Fan-out searches (parallel)

Spawn 2-4 search agents in parallel, each with a different angle:

```
Agent 1: Official documentation / source
Agent 2: Community examples / Stack Overflow / GitHub issues
Agent 3: Comparison / alternatives / known limitations
Agent 4: Specific to our stack (e.g., "DuckDB Python uv pyproject.toml")
```

Each agent returns: source URL, key finding, direct quote or code snippet.

### Charter for every fan-out search agent (mandatory)

```
ROLE: External research scout. Web-enabled. Return citations, not source files.

CACHE / DOWNLOAD POLICY:
- NEVER persist downloaded source material (PDFs, source files, archives,
  HTML dumps) at the repo root or anywhere inside the project working tree.
- Use the OS scratch location for any disk caching:
    Windows:  %TEMP%\agent-research\<session-id>\
    Unix:     ~/.cache/agent-research/<session-id>/
  Construct paths with the platform-correct join. NEVER concatenate
  "<project-name>" + ".cache_research" + "<filename>" — if the write path
  you are about to use does NOT start with the scratch root, STOP and
  report the path-construction bug.
- Quotes in your report MUST be short (a sentence or two, attributed).
  Do NOT paste entire PDF text, entire source files, or wholesale extracts.
- Third-party source code (LGPL / GPL / AGPL / proprietary) MUST be cited
  by repo URL + commit hash (or release tag + file path). Never copy it
  into the project working tree — not even into a gitignored folder.
- Delete every cached file before returning. Final report MUST end with a
  "Cleanup:" line listing what was removed and from where.

RETURN per finding:
  source: <URL or DOI>
  accessed: <ISO date>
  key claim: <one sentence>
  short quote: <≤2 sentences, in quotes>
  why it matters here: <one sentence>
Cleanup: <N files removed from <scratch path>>
```

If a fan-out agent returns copied source material or a cache path inside
the repo, discard its output and re-run with the policy reinforced.

---

## Step 3 — Adversarial verification

For any finding that will affect an architectural decision:

Spawn 1-2 skeptic agents with this charter:
> Read the finding: [X]. Try to refute it. Find counter-examples, version differences,
> known bugs, or contexts where it doesn't hold. Default to "refuted" if uncertain.

A finding that survives 2 skeptics is trustworthy enough to act on.
A finding that is refuted: discard or note as "contested".

---

## Step 4 — Synthesize with citations

Output format:
```
## Research: [topic]
**Question:** [restated question]
**Verdict:** [answer in 1-3 sentences]

### Key findings
1. [Finding] — Source: [URL or doc name], verified by [adversarial check]
2. [Finding] — Source: [URL or doc name]

### Code example (if applicable)
[minimal working example]

### Limitations / watch-outs
- [known gotcha 1]
- [known gotcha 2]

### What to do next
- [actionable recommendation — which skill to invoke next]
```

---

## Step 5 — Hand off to plan-architect

After research, the natural next step is /plan-architect:
- Paste the key findings into the plan's Context Scout section
- Reference the research doc (save as `docs/research/YYYY-MM-DD-[topic].md`)
- The plan's design decisions are now grounded in cited evidence

---

## Research quality rules

1. **No hallucinated citations** — every claim needs a source you actually read, not one you're assuming exists.
2. **Version-specific** — note which version of the library your findings apply to.
3. **Contested findings** — if adversarial verification flags something, mark it as `[CONTESTED]` not as fact.
4. **Minimal examples** — every actionable finding gets a code snippet that can be copy-pasted and run. Snippets must be written by you to illustrate the API; do NOT paste copyrighted source verbatim. For third-party source (LGPL / GPL / proprietary), cite repo URL + commit hash and paraphrase — never copy.
5. **No repo-resident downloads** — PDFs, archives, and source files belong in `%TEMP%\agent-research\<session-id>\` (Windows) or `~/.cache/agent-research/<session-id>/` (Unix), never under the project tree. Delete the scratch directory before returning and include a `Cleanup:` line in the report.
6. **Stop when good enough** — don't research forever. When the DECISION can be made, stop.
