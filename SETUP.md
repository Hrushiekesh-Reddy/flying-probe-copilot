# Today's Setup Commands

Run these in order on your Windows machine to bootstrap the repo.

---

## Step 1 — Create the project folder

```powershell
cd E:\
mkdir flying-probe-copilot
cd flying-probe-copilot
```

## Step 2 — Drop the starter files in

Copy everything from the `flying-probe-copilot-starter/` archive (provided by Pixel) into `E:\flying-probe-copilot\`. The folder structure should look like:

```
E:\flying-probe-copilot\
├── README.md
├── CLAUDE.md
├── LICENSE
├── .gitignore
├── .env.example
├── .cursor\rules\project.mdc
├── docs\
│   ├── SCOPE.md
│   ├── GUARDRAILS.md
│   ├── REQUIREMENTS.md
│   ├── ROADMAP.md
│   ├── DECISIONS.md
│   └── prompts\
│       ├── claude-code-start.md
│       ├── cursor-start.md
│       └── cowork-start.md
└── specs\
    └── synthetic-log-generator.md
```

Also drop the two requirements files from earlier into `docs/`:
- `docs/SKILLS.md` (formerly `flying-probe-copilot-SKILLS.md`)
- `docs/RESOURCES.md` (formerly `flying-probe-copilot-RESOURCES.md`)

## Step 3 — Initialize git

```powershell
git init
git branch -M main
git add .
git status         # sanity check — confirm .env is NOT staged
git commit -m "Phase 0: project skeleton, docs, and guardrails"
```

## Step 4 — Create the GitHub repo

```powershell
# Either via the GitHub web UI (recommended for privacy settings)
# Or via gh CLI if you have it:
gh repo create flying-probe-copilot --private --source=. --remote=origin --push
```

If using the web UI:
1. Create empty private repo `flying-probe-copilot`
2. ```powershell
   git remote add origin git@github.com:<your-username>/flying-probe-copilot.git
   git push -u origin main
   ```

## Step 5 — Set up Python + uv

```powershell
# Install uv if you don't have it
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Initialize a uv project (this creates pyproject.toml)
cd E:\flying-probe-copilot
uv init --python 3.11
```

## Step 6 — Add the first dependencies (just the essentials for Phase 1a)

```powershell
uv add pydantic python-dotenv pyyaml
uv add --dev pytest pytest-cov ruff
```

We'll add DuckDB, Streamlit, ChromaDB etc. in their respective phases — no need to install them today.

## Step 7 — Create .env (NOT committed)

```powershell
copy .env.example .env
notepad .env   # paste your Google AI Studio key
```

## Step 8 — Verify guardrails

```powershell
# Confirm .env is ignored
git status
# .env should NOT appear in untracked or staged files

# Confirm critical paths are protected
git check-ignore -v .env data/real/test.log 2>$null
# Both should be matched by .gitignore patterns
```

## Step 9 — Final commit for the day

```powershell
git add pyproject.toml uv.lock .env.example
git commit -m "Phase 0: Python project + uv + initial deps"
git push
```

## Step 10 — Update CLAUDE.md session log

Open `CLAUDE.md`, scroll to the bottom, add a line under "Session log":

```
- 2026-06-13 — Phase 0 — Repo bootstrapped, docs committed, Python env ready.
```

Commit it:

```powershell
git add CLAUDE.md
git commit -m "docs: session log update"
git push
```

---

## You're done for today.

Tomorrow / this weekend → open Cursor or Claude Code, paste the appropriate startup prompt from `docs/prompts/`, and begin Phase 1a (synthetic log generator) per `specs/synthetic-log-generator.md`.

---

## Sanity checks before you stop

- [ ] Repo pushed to GitHub (private)
- [ ] `.env` exists locally with your Google AI Studio key, and is NOT in git
- [ ] `CLAUDE.md` has today's session log entry
- [ ] You can describe the project's scope and guardrails to yourself in <60 seconds
- [ ] You've skimmed `specs/synthetic-log-generator.md` so you know what tomorrow looks like
