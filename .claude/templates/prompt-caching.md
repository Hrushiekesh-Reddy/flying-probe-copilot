# Prompt caching — how it works and how to leverage it

> Anthropic's prompt caching is API-level. Claude Code uses it automatically — you can't directly set `cache_control` from the CLI.
> But how you STRUCTURE work determines whether the cache hits or misses.
> This doc explains the mechanics and the practical workflow rules.

---

## The mechanics (short version)

- Anthropic caches token prefixes on the API side with a **5-minute TTL** (refreshed on each hit).
- A cache hit is ~10× cheaper than a fresh read AND ~2× faster (no re-encoding).
- The cache keys on **identical token prefix**. One byte different at position 0 → full miss.
- The cache is **per-conversation** in the sense that the prefix must come from the same logical session — but parallel sub-agents within the same Claude Code run CAN share prefix cache if their prompts share an identical prefix.

---

## What the Claude Code harness already does for you

- Caches the system prompt (this huge thing) across turns in the same session.
- Caches the conversation history prefix — earlier turns are cached as long as you don't compact / edit them.
- Caches CLAUDE.md and other context-injected files at the boundary they're injected.

You **don't need to configure this**. It happens automatically. What you control is whether your structure HELPS or HURTS the cache.

---

## Five practical rules for cache-friendly sessions

### 1. Keep stable instructions stable

The CLAUDE.md / rules / agent-conduct files are loaded into context at session start. **Do not edit them mid-session.** Every edit invalidates every downstream cache hit. If you must change a rule, do it at the START of a new session.

### 2. Front-load stable content; tail-load volatile content

Order in any composed prompt:
```
[STABLE — CLAUDE.md, rules, brief]      ← cached
[STABLE — sub-agent role/charter]       ← cached
[VOLATILE — current diff, test output]  ← fresh tokens
[VOLATILE — your specific question]     ← fresh tokens
```
Putting volatile content at the top breaks the cache for everything after it.

### 3. Pass an IDENTICAL brief block to parallel sub-agents

This is why `.claude/templates/sub-agent-brief.md` is structured as it is. If Explore, Verify-Plan, Exec, and Verify-Exec all see the same brief block at position 0, the brief is paid for ONCE (full price) and reused ~3× at cache-hit pricing.

**Critical:** the brief must be byte-for-byte identical. If you tweak a single character between dispatches, the cache misses.

### 4. Batch sub-agent dispatches into the same 5-minute window

The TTL is 5 minutes. If you launch Explore at 10:00, do something else for 10 minutes, then launch Exec at 10:10 — the brief prefix has expired, you pay full price again. Run the full chain back-to-back when you can.

For Medium/Large tiers, the parent should:
- Step 1 (Document) — write the brief
- Step 2 (Explore) — dispatches sub-agent #1
- Read result (≤1-2 min)
- Step 3 (Plan) — parent work
- Step 4 (Verify Plan, if Large) — dispatches sub-agent #2 with same brief
- Step 5 (Execute) — dispatches sub-agent #3 with same brief
- Step 6 (Verify Exec, if Large) — dispatches sub-agent #4 with same brief

If you take a long break between Step 3 and Step 5, that's fine for human reasons — but understand the brief prefix will cost full price on the next dispatch.

### 5. Don't change the parent's history mid-loop

The parent agent's conversation history is itself a cached prefix. If you compact, edit a tool result, or do anything that rewrites earlier turns — the cache is dropped.

Practical implications:
- Don't paste large file contents into the chat that you could pass via tool results instead.
- Don't make the parent reread CLAUDE.md mid-loop — it's already in context.
- If you find yourself wanting to "start over" mid-loop, do — but understand it's a cache reset.

---

## What this looks like in practice — annotated session

Imagine a Medium-tier session. Cache behavior:

```
T+00:00  Parent loads. CLAUDE.md + rules + skills cached. [PAID once, full price]
T+00:30  Parent writes Step 1 brief. [tiny incremental cost]
T+01:00  Parent dispatches Explore sub-agent.
         Sub-agent gets: [system prompt] + [brief block] + [Explore charter]
         [system prompt] hits parent's session cache → cheap
         [brief block] is new → PAID once, full price, NOW CACHED
         [Explore charter] is new → PAID once
T+03:00  Parent gets Explore result, writes Plan. [parent work, no sub-agent]
T+05:30  Parent dispatches Exec sub-agent.
         Sub-agent gets: [system prompt] + [brief block] + [Exec charter]
         [system prompt] → cache hit, cheap
         [brief block] → cache hit (still within 5-min TTL), cheap   ← THE WIN
         [Exec charter] is new → PAID once
T+15:00  Parent dispatches Verify-Exec sub-agent.
         [system prompt] → cache hit
         [brief block] → MISS (>5 min since last use) — PAID full price again
         [Verify-Exec charter] → PAID
```

The brief block win shows up between Explore and Exec because they fired close together. Verify-Exec missed because we lingered. For tiered workflows, this is fine — you're trading some cache hits for the parent's careful Step-7 read.

---

## Measuring whether caching is helping

Claude Code's API responses include cache_read_input_tokens vs cache_creation_input_tokens vs input_tokens. You can see these in the response metadata (debug mode). A healthy multi-sub-agent session should show cache_read_input_tokens dominating across sub-agent calls 2, 3, 4.

If you see uniformly high input_tokens across all sub-agents, the brief block isn't being reused identically — check for whitespace or template-variable drift.

---

## Anti-patterns

- **Paraphrasing the brief block between sub-agents** — even reordering bullets misses the cache. Copy-paste verbatim.
- **Inserting a timestamp at the top of the brief** — kills the cache by design.
- **Loading CLAUDE.md inside every sub-agent prompt** — already in their system prompt; this is doubly-loaded.
- **One sub-agent at a time, hours apart** — TTL is 5 minutes. Batch.
- **Editing rules mid-session** — every downstream call pays full price.

---

## TL;DR

You don't configure prompt caching directly. You enable it by being disciplined about prefix stability. The brief-block template + tier-batching strategy in this repo are designed to maximize cache hits across the 4 sub-agents of a full loop. Expect ~30–50% input-token savings on Medium/Large sessions when followed strictly.
