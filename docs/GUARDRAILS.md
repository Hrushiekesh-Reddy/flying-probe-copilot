# GUARDRAILS.md — Non-Negotiable Rules

These rules protect IP, copyright, employer obligations, and project integrity. Violating any of them is a project-ending error. They apply to the owner, to Claude Code, to Cursor, and to any subagent.

---

## 1. Real data isolation (the #1 rule)

### Rule
Real customer / employer flying-probe or ICT log data **must never**:
- Be committed to this repo (public or private)
- Be copied to a personal machine
- Be sent through a non-employer LLM API (Gemini, Claude, OpenAI, etc.)
- Be screenshotted into chat tools
- Be discussed in any way that includes identifying customer / board / part-number content

### Enforcement
- `data/real/`, `data/private/`, `*.real.log`, `*.confidential.log` are in `.gitignore`.
- Real-data validation happens exclusively on the employer's network, on employer-approved equipment.
- Validation outputs that come home are **structural metrics only**: parser pass rates, field-extraction accuracy, schema fit. No raw values.
- Before any commit, mentally check: "Could any element of this content be linked back to a real customer or product?" If yes, sanitize or remove.

### Why this matters
EMS hiring managers consider data-IP discipline a baseline competence. Demonstrating it is a hiring signal. Violating it is a career-ending risk.

---

## 2. Copyright on standards documents

### Rule
- **IPC-A-610**, **J-STD-001**, and other IPC / JEDEC / ANSI standards are copyrighted. Verbatim text from them must not appear in:
  - Code comments
  - Documentation
  - The failure-mode knowledge base
  - LLM training / fine-tuning data
  - The vector store index

### Allowed
- Owner-authored **summaries and paraphrases** of acceptance criteria.
- Citations by section number ("see IPC-A-610 §7.5.4").
- References to publicly available IPC press releases, white papers, and Wikipedia entries.

### If the RAG needs to reason about IPC criteria
- Index owner-authored summaries, not the standards themselves.
- The LLM's job is to compose an answer from those summaries, not to recite the standard.

---

## 3. Keysight / equipment-vendor documentation

### Rule
- Public Keysight manuals (i3070 BT-Basic Programming Manual, Test Methods Manual) may be **referenced** by section but not redistributed in the repo.
- Format details extracted into the synthetic generator must be **described in your own words**.

---

## 4. API key handling

### Rule
- All keys live in `.env` (gitignored). A `.env.example` template lives in the repo with placeholder values only.
- Keys are loaded via `python-dotenv`; never imported from constants in code.
- Never log a key, never print a key, never paste a key into chat.
- Rotate keys if any of the above happens accidentally.

### Required `.env.example` contents
```
GOOGLE_API_KEY=your_google_ai_studio_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here_optional
```

---

## 5. LLM grounding rule

### Rule
The co-pilot must never invent test results, yield numbers, or root-cause claims. Every assertion in an answer must trace to:
1. A row retrieved from the DuckDB query layer, OR
2. An entry in the failure-mode knowledge base, OR
3. A clearly labeled "general PCBA knowledge" caveat.

### Enforcement
- All LLM prompts include the instruction: "If you don't have evidence from retrieved context, say so. Do not invent."
- Responses display the citations used.
- Adversarial tests in Phase 4: ask questions with no supporting data and verify the model refuses.

---

## 6. Scope discipline

### Rule
- One phase at a time. No starting Phase 2 code while Phase 1 is incomplete.
- Out-of-scope ideas go to `docs/DECISIONS.md` (parking lot section) for later evaluation.

### Why
Scope creep is the dominant failure mode of solo portfolio projects. The 8-week timeline assumes phase discipline.

---

## 7. AI-assisted coding discipline

### Rule
- Every AI-generated module must be read line by line by the owner before commit.
- No "vibe coding" without comprehension — the project's defensibility in interviews depends on the owner being able to explain every line.
- Generated tests count as code: they must be reviewed too.

---

## 8. Public repo readiness check

Before flipping the repo public (end of Phase 4), verify:
- [ ] No `data/real/` content anywhere in git history (use `git log --all -- data/real/`)
- [ ] No API keys in history (use `gitleaks` or manual review of `.env*` patterns)
- [ ] No copyrighted standards text in any file
- [ ] No employer / customer names in commits, comments, or docs
- [ ] All commits authored under your personal GitHub identity, not a work account
- [ ] README and case-study writeup explicitly state synthetic-data design

If any check fails, the fix is `git filter-repo` or starting from a clean branch — not papering over it.

---

## 9. Cross-project information flow

When working on related repos (`E:\my-assembly-hub`, `E:\Portfolio`), apply the same rules. Cross-project findings surface as `spawn_task` chips, not silent copies. No work from `my-assembly-hub` enters this repo unless it is already public there.

---

## 10. When in doubt

The default is the **more cautious** choice. If you can't articulate why a piece of content is safe to include, leave it out and ask.
