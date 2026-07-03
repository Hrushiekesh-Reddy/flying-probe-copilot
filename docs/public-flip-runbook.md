# Public-Flip Runbook

> Step-by-step execution for flipping `Hrushiekesh-Reddy/flying-probe-copilot` from private to public. Walk top-to-bottom during the public-flip session, after the [Public-Flip Guardrails Checklist](public-flip-checklist.md) audit shows ALL CHECKS PASS.
>
> **Sequencing:** Phase 4 slice 3 CI must be landed and green on a real PR first — the `contexts: [...]` arrays below need the literal status-check names GitHub emits, and guessing them silently disables the protection.

---

## Phase A — Before the flip (still private)

### A1. Confirm CI is green and capture check names

After a PR runs end-to-end on the new CI workflow:

```bash
# List the exact status-check names GitHub recorded for the most recent PR
gh pr checks --json name,conclusion | jq -r '.[] | "\(.name)\t\(.conclusion)"'
```

Use those literal names in the `contexts: [...]` arrays in A5 / A6 — guessing them will silently disable the protection.

### A2. Re-run the guardrails audit

```bash
# Re-run the §8 commands from public-flip-checklist.md and update the "Last run" date
```

Expect: all six checks still pass. If any regress, fix before continuing — do **not** flip public with a guardrail breach in history.

### A3. README renders for a logged-out viewer

Cannot test until after the flip — see Phase C smoke test. Pre-flight: confirm the Mermaid block is fenced as ` ```mermaid ` (not ` ```mmd `) and the hero-strip image paths are repo-relative, not absolute.

### A4. Repo settings via UI (Settings → General)

- [X] **Features → Wikis: OFF** (docs live in `/docs`)
- [X] **Features → Discussions: OFF** (flip on later if traction)
- [X] **Pull Requests → Allow squash merging: ON; merge commits + rebase: OFF**
- [X] **Pull Requests → Always suggest updating PR branches: ON**
- [X] **Pull Requests → Allow auto-merge: ON**
- [X] **Pull Requests → Automatically delete head branches: ON**
- [X] **Releases → Enable release immutability: ON**

### A5. Branch protection — `main`

Replace `lint`, `test` with the real check names from A1.

```bash
gh api -X PUT repos/Hrushiekesh-Reddy/flying-probe-copilot/branches/main/protection \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint", "test"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": true
}
EOF
```

> `enforce_admins: true` means **even you (as owner) cannot bypass the rules** on `main`. No direct push, no force-push, no merge without checks passing. If you ever need to bypass for a real emergency, you can temporarily disable the protection (`gh api -X DELETE .../branches/main/protection/enforce_admins`), do the work, then re-enable it (`gh api -X POST .../branches/main/protection/enforce_admins`). Leaving `dev` at `enforce_admins: false` (next block) gives you an escape hatch on the integration branch.

### A6. Branch protection — `dev`

```bash
gh api -X PUT repos/Hrushiekesh-Reddy/flying-probe-copilot/branches/dev/protection \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint", "test"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false,
  "allow_fork_syncing": true
}
EOF
```

### A7. Verify protection landed

```bash
gh api repos/Hrushiekesh-Reddy/flying-probe-copilot/branches/main/protection \
  | jq '{checks: .required_status_checks.contexts, force_push: .allow_force_pushes.enabled, deletions: .allow_deletions.enabled, linear: .required_linear_history.enabled}'
gh api repos/Hrushiekesh-Reddy/flying-probe-copilot/branches/dev/protection \
  | jq '{checks: .required_status_checks.contexts, force_push: .allow_force_pushes.enabled, deletions: .allow_deletions.enabled}'
```

Expect: `force_push: false`, `deletions: false`, `checks: ["lint", "test", ...]` matching A1.

---

## Phase B — The flip

### B1. Flip visibility

```bash
gh repo edit Hrushiekesh-Reddy/flying-probe-copilot \
  --visibility public \
  --accept-visibility-change-consequences
```

This is **irreversible in practice** — anyone who clones in the next minute keeps a copy. Do not run until Phase A is fully ticked.

### B2. Enable platform security (must run AFTER B1 — most settings only apply to public repos)

```bash
# Dependabot alerts + auto security PRs
gh api -X PUT repos/Hrushiekesh-Reddy/flying-probe-copilot/vulnerability-alerts
gh api -X PUT repos/Hrushiekesh-Reddy/flying-probe-copilot/automated-security-fixes

# Secret scanning + push protection (free on public repos)
gh api -X PATCH repos/Hrushiekesh-Reddy/flying-probe-copilot \
  -F 'security_and_analysis[secret_scanning][status]=enabled' \
  -F 'security_and_analysis[secret_scanning_push_protection][status]=enabled'
```

Push protection is the load-bearing piece for guardrail #5 — it blocks a `git push` carrying a recognized secret pattern (Google API key, AWS key, etc.) **before** the push lands.

---

## Phase C — Post-flip smoke tests

### C1. Logged-out viewer test

Open the repo URL in an incognito/private browser window. Confirm:

- [ ] README renders (hero strip visible, Mermaid diagram rendered as a graph, not raw)
- [ ] `docs/case-study.md` opens and renders cleanly
- [ ] `docs/img/demo.gif` plays inline above the hero strip
- [ ] No "404 — not found" or "private repository" message

### C2. Push-protection live test (optional but worth 30 s)

On a throwaway feature branch:

```bash
git checkout -b test/push-protection-check
echo "GOOGLE_API_KEY=AIzaSyD-FAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKE" > /tmp/fake-key.txt
git add /tmp/fake-key.txt 2>/dev/null  # adjust path for your shell
git commit -m "test: should be blocked"
git push origin test/push-protection-check
```

Expect: GitHub rejects the push with a secret-scanning block message. If it **doesn't**, the push-protection setting didn't apply — re-run the `PATCH` in B2 and check the API response.

Then clean up: `git checkout dev && git branch -D test/push-protection-check`.

### C3. Branch-protection live test

Try to push directly to `main`:

```bash
git checkout main
git commit --allow-empty -m "test: should be blocked"
git push origin main
```

Expect: rejection. Clean up with `git reset --hard origin/main` on the local main.

---

## Rollback (if something is wrong)

- **Visibility back to private:** `gh repo edit --visibility private --accept-visibility-change-consequences`. Note this does **not** retract clones already pulled in the public window.
- **Drop branch protection:** `gh api -X DELETE repos/Hrushiekesh-Reddy/flying-probe-copilot/branches/<branch>/protection`
- **Disable secret scanning:** flip the `PATCH` values in B2 from `enabled` to `disabled`.
