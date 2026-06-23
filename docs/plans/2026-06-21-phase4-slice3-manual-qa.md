# Manual QA — Phase 4 Slice 3 (CI workflows + ruff config)

**Date:** 2026-06-21
**Owner:** Hrushiekesh Reddy Kanjula
**Branch:** `feature/phase4-slice3-ci-workflows` (renamed from worktree)
**Commits ready to push:** 4
  - `056459e` chore — cleanup pass (ruff --fix + format)
  - `fdc0922` feat — CI workflows + ruff config
  - `a1ab560` docs — exec-report + ROADMAP tick + plan artifacts
  - `eece97c` docs — SESSION_LOG + DECISION_LOG + CLAUDE.md + verify-execution
**Expected duration:** 5-10 min local + 5-8 min watching first CI wall-clock

---

## Pre-push local checks (you can do these in 90 seconds)

### 1. Branch + status
```bash
git branch --show-current
# Expect: feature/phase4-slice3-ci-workflows

git status
# Expect: nothing to commit, working tree clean
#         branch is ahead of 'origin/dev' by 4 commits

git log --oneline -6
# Expect (top to bottom):
#   eece97c docs(phase4-slice3): SESSION_LOG + DECISION_LOG + CLAUDE.md + verify-execution
#   a1ab560 docs(phase4-slice3): exec-report + ROADMAP tick + plan artifacts
#   fdc0922 feat(phase4-slice3): CI workflows (lint + tests + screenshot recapture) + ruff config
#   056459e chore(phase4-slice3): one-time ruff --fix + format cleanup pass
#   49cffef Merge pull request #34 from Hrushiekesh-Reddy/feature/phase4-slice2-screenshots
#   bb92534 docs(phase4-slice2): manual-QA script + agent handoff log
```

### 2. Workflow YAMLs parse
```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('ci.yml OK')"
python -c "import yaml; yaml.safe_load(open('.github/workflows/screenshots.yml')); print('screenshots.yml OK')"
# Both exit 0; both print OK.
```

### 3. Local suite still green
```bash
uv run pytest -q --no-header 2>&1 | tail -3
# Expect: 659 passed, 5 skipped, 1 xfailed, 1 warning  (~85s)
```

### 4. Local lint + format both clean
```bash
uv run ruff check src tests
# Expect: All checks passed!

uv run ruff format --check src tests
# Expect: 102 files already formatted
```

### 5. Eyeball the cleanup commit (sanity-check the size)
```bash
git show --stat 056459e | tail -5
# Expect: 68 files changed, 1517 insertions(+), 1126 deletions(-)

# Spot-check src/ format diff (should be mechanical: collapse short multi-line strings,
# split overlong dict literals, sort imports)
git show 056459e -- src/flying_probe_copilot/ui/data.py | head -25

# Spot-check the load-bearing F811 fix
git show 056459e -- tests/test_ui/test_views_smoke.py | grep -A2 "import duckdb" | head -8
```

---

## Push + PR

### 6. Push the branch
```bash
git push -u origin feature/phase4-slice3-ci-workflows
```

### 7. Open the PR
```bash
gh pr create \
  --base dev \
  --title "feat(phase4-slice3): GitHub Actions CI workflows + ruff config" \
  --body "$(cat <<'EOF'
## Summary

- Two NEW workflow files: `.github/workflows/ci.yml` (lint + tests parallel jobs) and `.github/workflows/screenshots.yml` (path-filtered screenshot recapture on UI/analytics/KB PRs).
- Approval-gated `pyproject.toml` edit: `ruff>=0.6` dev dep + 4 ruff config blocks (D5 minimal rule set, D6/W-8 per-file-ignores, D16 scripts-excluded, format defaults).
- One-time `ruff --fix` + `ruff format` cleanup pass across `src/` + `tests/` ratified at Decision Gate as a slice-3 exception to the read-only `src/**` guardrail (D17 = A).
- 93 new tests in `tests/test_ci/` validating YAML shape, path filters, action version pins, no-secrets defense-in-depth, and pyproject ruff config.

## Test plan
- [ ] CI's `lint` job goes green (ruff check + format --check both pass)
- [ ] CI's `tests` job goes green (659 passing / 5 skipped / 1 xfailed / 97% coverage)
- [ ] `screenshots.yml` correctly does NOT run on this PR (no UI/analytics/KB/script paths touched — per D14)
- [ ] First UI-touching PR after merge triggers `screenshots.yml` end-to-end (separate manual-QA on the next PR)

Decisions ratified at Step 6 Decision Gate: D1-D4 (brief) + D5-D15 (Plan) + D16/D17/D17.1 (Plan Rev1) + MD-4/BR/BUNDLE. Step 5 red-team caught 7 BLOCKERs all closed in Rev1 before Execute. Step 8 verify-execution PASSED. See `docs/plans/2026-06-21-phase4-slice3-*.md` for full artifacts.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Watch the first CI run

### 8. Open the Actions tab and watch ci.yml
- Both jobs (`lint`, `tests`) should appear in the PR's checks section within ~30 s of the PR being created.
- **Expected wall-clock:**
  - `lint` job: ~1-2 min (cold cache) / ~30 s (warm)
  - `tests` job: ~3-5 min (cold cache) / ~1-2 min (warm)
  - Both run in parallel — total ~3-5 min cold.

### 9. Verify `screenshots.yml` did NOT trigger
- In the PR's checks section, only `ci / lint` and `ci / tests` should appear.
- No `screenshots / capture` check.
- This is **correct** per D14 — the PR only adds `.github/workflows/*` + `pyproject.toml` + `tests/test_ci/*` + docs, none of which match the screenshot path filter (`src/ui/**`, `src/analytics/**`, etc.).

### 10. If CI is RED
- **`lint` red?** Run `uv run ruff check . --output-format=github` locally and check output. Most likely: a file I missed in the cleanup pass surfaced a new violation, or the per-file-ignores key doesn't actually match. Fix-forward on the branch — do NOT roll back the cleanup commit.
- **`tests` red?** Compare local 659-passing vs CI's actual count. Most likely: a test depends on a Windows-only path or env var. Fix-forward.
- **YAML parse error?** Should never reach CI (local check #2 catches it). If it does, `git revert` the workflow commit and investigate offline.

### 11. After CI goes green
- Merge the PR via `gh pr merge --squash` (or your usual flow).
- Confirm the workflows now live on `dev`.

---

## Post-merge verification (next session pickup)

After PR is merged to `dev`:
1. Make a trivial UI commit on a follow-up branch (e.g., `chore: typo in src/flying_probe_copilot/ui/views.py`).
2. Open a PR to `dev`.
3. Expect: BOTH `ci / lint` + `ci / tests` AND `screenshots / capture` to trigger.
4. Watch `screenshots / capture` run end-to-end (~3-4 min cold, ~40-50 s warm).
5. Download the `recaptured-dashboard-screenshots` artifact from the Actions tab and eyeball the 6 JPGs + gif.
6. Close the test PR without merging.

---

## What this slice does NOT cover (you'll handle these in slice 4)

- Repo flip to public (per D3 deferral)
- Branch-protection rules requiring CI green on PRs to `main`
- CI status badge in README
- `docs/DEMO.md` walkthrough script
- Blog post / LinkedIn post / resume bullet
- Final guardrails audit checklist (run `docs/GUARDRAILS.md` §8 top-to-bottom)

---

## If something feels off

Tell next-session Claude what you observed; the AGENT_HANDOFF_LOG entry at Step 12 will have full context. The whole slice is reversible at the commit level — each commit is logically separate, so `git revert <hash>` on any of `056459e` / `fdc0922` / `a1ab560` / `eece97c` removes just that change.
