# Dependabot triage log — 2026-07-03

Three alerts fired at the moment the repo flipped public. This doc records each triage: fixed, dismissed with reason, and the reasoning behind that call. Future auditors: start here.

**Repo:** [Hrushiekesh-Reddy/flying-probe-copilot](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot)
**Flip date:** 2026-07-03
**Alerts fired at flip:** 3 (1 critical / 1 medium / 1 low)

| # | Package | Sev | Advisory | Outcome | PR |
|---|---|---|---|---|---|
| 1 | chromadb | critical | GHSA-f4j7-r4q5-qw2c | Dismissed — `not_used` | — |
| 2 | torch | low | GHSA-rrmf-rvhw-rf47 | Bumped 2.12.0 → 2.12.1 | [#49](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot/pull/49) |
| 3 | pydantic-settings | medium | GHSA-4xgf-cpjx-pc3j | Bumped 2.14.1 → 2.14.2 | [#45](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot/pull/45) |

---

## #1 · chromadb 1.5.9 · critical · GHSA-f4j7-r4q5-qw2c

**Advisory summary:** "ChromaDB Python project has a pre-authentication code injection vulnerability."

**Vulnerable range:** `>= 1.0.0, <= 1.5.9`
**Patched version (per GHSA):** `null` — no upstream patch exists as of 2026-07-03
**Pypi latest:** 1.5.9 (identical to our pin — no newer version available at triage time)
**CWE:** CWE-94 (Improper control of code generation)

### Attack vector (from advisory)

> A pre-authentication, code injection vulnerability in version 1.0.0 or later of the ChromaDB Python project allows an unauthenticated attacker to run arbitrary code on the server by sending a malicious model repository and `trust_remote_code` set to true in the `/api/v2/tenants/{tenant}/databases/{db}/collections` endpoint.

### Our usage

`src/flying_probe_copilot/rag/vector_index.py:72`:

```python
self._client = chromadb.EphemeralClient()
```

- `EphemeralClient` = in-process, in-memory. No HTTP server. No REST surface.
- No `chromadb.HttpClient`, no `chromadb.PersistentClient` server mode, no `chroma run` daemon anywhere in the codebase (verified via `grep -rn "chromadb\|HttpClient\|PersistentClient\|chroma run" src/ tests/`).
- No `trust_remote_code` code path — we don't pass user-controlled model repositories to Chroma.
- No `/api/v2/…` endpoint exposed — we're a library consumer, not a server operator.

### Exposure assessment

**Zero exposure.** The vulnerable code path is the REST endpoint on a running ChromaDB server. We use `EphemeralClient` as an embedded, in-process, in-memory vector index. The vulnerable attack surface does not exist in this deployment.

### Decision

**Dismissed** via `PATCH /repos/…/dependabot/alerts/1` with:

```
dismissed_reason: "not_used"
dismissed_comment: "EphemeralClient only; vulnerable REST endpoint not exposed. See docs/security/dependabot-triage-2026-07-03.md"
```

### Watch conditions

Re-open the triage if any of the following becomes true:

- The RAG layer migrates to `HttpClient` / `PersistentClient` server mode.
- Any file under `src/flying_probe_copilot/` starts a `chroma run` daemon or spins up an HTTP-exposed Chroma.
- A `trust_remote_code=True` argument appears anywhere in the codebase.
- Upstream chromadb ships a patched version and Dependabot re-fires with a `first_patched_version` — take the bump then.

---

## #2 · torch 2.12.0 · low · GHSA-rrmf-rvhw-rf47

**Advisory summary:** "PyTorch is vulnerable to memory corruption through its `torch.jit.script` function."

**Vulnerable range:** `<= 2.12.0`
**Patched version (per GHSA):** `null` — but pypi has 2.12.1 (post-advisory)
**CWE:** CWE-119 (Improper restriction of operations within the bounds of a memory buffer)

### Our usage

Torch is a **transitive** dependency pulled in via `sentence-transformers` for the RAG embedding pipeline (`all-MiniLM-L6-v2`). We do not call `torch.jit.script` anywhere:

```
$ grep -rn "torch\.jit\|jit\.script" src/ tests/
(no matches)
```

We also do not pass untrusted input to any torch API — the embedding pipeline consumes fixed local knowledge-base markdown.

### Exposure assessment

**Low-to-zero.** The vulnerable function is not called. Even if it were, we don't pass untrusted input.

### Decision

**Bumped** 2.12.0 → 2.12.1 (lockfile only) in [PR #49](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot/pull/49), which moves us out of the `<= 2.12.0` flagged range. GHSA hadn't updated `first_patched_version` to point at 2.12.1 as the fix at triage time — but the version increment sits outside the vulnerable window, and the change is a clean lockfile-only patch bump with the full suite green (667 passed / 5 skipped / 1 xfailed).

If Dependabot re-flags 2.12.1 explicitly later, we'll take a fresh alert.

---

## #3 · pydantic-settings 2.14.1 · medium · GHSA-4xgf-cpjx-pc3j

**Advisory summary:** "`NestedSecretsSettingsSource` follows symlinks outside `secrets_dir`, enabling local file read and bypassing `secrets_dir_max_size`."

**Vulnerable range:** `>= 2.12.0, < 2.14.2`
**Patched version (per GHSA):** `2.14.2`

### Our usage

pydantic-settings is a **transitive** dep pulled in via `chromadb`. We do not use `NestedSecretsSettingsSource` anywhere:

```
$ grep -rn "NestedSecretsSettingsSource\|secrets_dir" src/ tests/
(no matches)
```

### Exposure assessment

**Zero exposure.** The vulnerable feature is not touched.

### Decision

**Bumped** 2.14.1 → 2.14.2 (lockfile only) in [PR #45](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot/pull/45). Clean patch bump, defense-in-depth. Auto-closed alert #3.

---

## Method — reproduce this triage

```bash
# 1. List open Dependabot alerts
gh api repos/Hrushiekesh-Reddy/flying-probe-copilot/dependabot/alerts \
  --jq '[.[] | select(.state == "open") | {number, package: .dependency.package.name, severity: .security_advisory.severity, vuln_range: .security_vulnerability.vulnerable_version_range, patched: .security_vulnerability.first_patched_version.identifier, ghsa: .security_advisory.ghsa_id}]'

# 2. For each alert, fetch the underlying advisory to see the *attack vector* text (Dependabot only surfaces the summary)
gh api /advisories/<GHSA-ID> --jq '{summary, description, vulnerabilities: [.vulnerabilities[] | {name: .package.name, vulnerable_version_range, first_patched_version}]}'

# 3. Check pypi for a newer version — GHSA's first_patched_version field lags
curl -sS https://pypi.org/pypi/<package>/json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["info"]["version"])'

# 4. Grep our codebase for the vulnerable API surface — this determines exposure
grep -rn "<vulnerable-function-or-class>" src/ tests/

# 5a. If exposure is real → bump via `uv lock --upgrade-package <name>` and open a PR
# 5b. If exposure is zero → dismiss via API:
gh api -X PATCH repos/Hrushiekesh-Reddy/flying-probe-copilot/dependabot/alerts/<N> \
  -f state=dismissed -f dismissed_reason=not_used \
  -f "dismissed_comment=<reason + pointer to this doc>"
```

**dismissed_reason values GitHub accepts:** `fix_started` · `inaccurate` · `no_bandwidth` · `not_used` · `tolerable_risk`.
