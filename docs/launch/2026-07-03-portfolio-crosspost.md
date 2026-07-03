# Portfolio-site cross-post prep

The portfolio site lives at `E:\Portfolio` on the Windows machine and is not reachable from this Mac session. This doc gathers everything that needs to move into that repo when you're back on Windows so the case study can be cross-posted with zero editing on the target side.

## Ship list

Copy these files from `flying-probe-copilot/` on this Mac (or clone the public repo on Windows) into the portfolio project:

| Source (this repo) | Target (portfolio) | Notes |
|---|---|---|
| `docs/case-study.md` | `content/projects/flying-probe-copilot.mdx` (or `.md`) | Rename to whatever the portfolio's MDX loader expects. Add frontmatter (below). |
| `docs/img/screenshot-overview.jpg` | `public/projects/flying-probe-copilot/overview.jpg` | 6 hero screenshots — keep the same basenames or update the case-study `![...]` paths. |
| `docs/img/screenshot-yield.jpg` | `public/projects/flying-probe-copilot/yield.jpg` | |
| `docs/img/screenshot-pareto.jpg` | `public/projects/flying-probe-copilot/pareto.jpg` | |
| `docs/img/screenshot-spc.jpg` | `public/projects/flying-probe-copilot/spc.jpg` | |
| `docs/img/screenshot-anomalies.jpg` | `public/projects/flying-probe-copilot/anomalies.jpg` | |
| `docs/img/screenshot-copilot.jpg` | `public/projects/flying-probe-copilot/copilot.jpg` | |
| `docs/img/demo.gif` | `public/projects/flying-probe-copilot/demo.gif` | 748 KB — safe to embed inline. |
| `docs/launch/2026-07-03-blog-post.md` | `content/blog/2026-07-03-pcba-copilot.mdx` | Optional — the blog post is a shorter, punchier variant of the case study; publish either one or both depending on how the portfolio splits case-studies from blog posts. |

## Frontmatter template

If your portfolio uses MDX with a `<content>/projects/*.mdx` convention, prepend this to the case study before publishing:

```yaml
---
title: "Flying-Probe / ICT Test-Log Intelligence Co-Pilot"
slug: flying-probe-copilot
kind: project
role: "Manufacturing Engineer + AI portfolio project"
tech: [Python, DuckDB, ChromaDB, Streamlit, Gemini, RAG]
timeframe: "2026-04 → 2026-07 (8 weeks · evenings + weekends)"
repo: https://github.com/Hrushiekesh-Reddy/flying-probe-copilot
status: "shipped 2026-07-03 — public, MIT"
hero_image: /projects/flying-probe-copilot/overview.jpg
tags: [manufacturing, pcba, spc, rag, portfolio]
excerpt: >
  A Python system that ingests PCBA flying-probe / ICT test logs into a
  DuckDB spine, runs Yield / Pareto / SPC / anomaly analytics, and answers
  natural-language root-cause questions through a strictly-grounded RAG
  co-pilot. 667 tests · 97% coverage · 10/10 live RAG eval.
---
```

Swap key names to whatever your portfolio's frontmatter schema uses (many Next.js/Astro portfolios use `title`, `description`, `tags`, `date`, `cover`).

## Image path rewrites in the case study

`docs/case-study.md` uses **repo-relative** paths that render on GitHub (`docs/img/…`). On the portfolio site those paths won't resolve. Two options:

- **Option A — Rewrite paths at publish time.** Run this once against the copy in the portfolio repo:
  ```bash
  # From the portfolio repo root, after copying the case study in place
  sed -i.bak 's|docs/img/|/projects/flying-probe-copilot/|g' content/projects/flying-probe-copilot.mdx
  # Also fix internal doc links so they point back at the public repo, not local docs/
  sed -i.bak 's|](logs/BUG_LOG.md)|](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot/blob/main/docs/logs/BUG_LOG.md)|g' content/projects/flying-probe-copilot.mdx
  sed -i.bak 's|](DECISIONS.md)|](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot/blob/main/docs/DECISIONS.md)|g' content/projects/flying-probe-copilot.mdx
  sed -i.bak 's|(../scripts/|(https://github.com/Hrushiekesh-Reddy/flying-probe-copilot/blob/main/scripts/|g' content/projects/flying-probe-copilot.mdx
  sed -i.bak 's|(plans/|(https://github.com/Hrushiekesh-Reddy/flying-probe-copilot/blob/main/docs/plans/|g' content/projects/flying-probe-copilot.mdx
  rm content/projects/flying-probe-copilot.mdx.bak
  ```
- **Option B — Use `<Image>` MDX components** (if your portfolio wraps images through `next/image` or similar). Manually convert the six `![alt](path)` blocks into your portfolio's Image component. More work, better LCP.

Verify with `sed -n 's|.*(\([^)]*\)).*|\1|p' content/projects/flying-probe-copilot.mdx | sort -u` — every path should either be an absolute URL (`https://…`) or an in-portfolio absolute path (`/projects/…`), no `docs/…` and no `../` left.

## Blog post variant

`docs/launch/2026-07-03-blog-post.md` is the shorter portfolio-blog variant of the case study — same structure, tighter prose, ends with a hire-me line. Cross-post decision:

- If the portfolio has separate **projects** and **blog** sections, publish both — the case study as the project page, the blog post as a launch announcement that links to the project.
- If the portfolio has only one long-form section, publish the case study and skip the blog post (or use the blog post's opening + hire-me close as the LinkedIn message and skip it entirely).

## Verify before shipping

```bash
# From the portfolio repo, after cross-posting:
npm run dev  # or whatever launches the local site
# Then:
# 1. Open the new project page in a browser
# 2. Confirm the six hero images load (no broken img icons)
# 3. Confirm the demo.gif plays inline
# 4. Confirm the "flying-probe-copilot" GitHub link opens the public repo
# 5. Confirm the BUG_LOG / DECISIONS / plans links resolve to the public GitHub URL
# 6. Run `npm run build` (or `astro build`) to catch any broken MDX
```

Once the portfolio site is deployed, tick the "Case-study cross-post on portfolio site" line in `docs/public-flip-checklist.md` and the corresponding row in `docs/ROADMAP.md` Phase 4.
