# Skill: frontend-design

> Invoke: `/frontend-design`
> UI/UX best practices, design patterns, and accessible, implementable design decisions.
> Use when the PRIMARY question is how something should look, feel, or behave.
> See /skill-sergeant for routing.

---

## When to use

- "Design this component", "how should this look", "what's the best layout for X"
- "Improve the UX of", "make this more usable", "the UX is confusing", "users get lost at"
- "Design a dashboard for", "what UI pattern should I use", "design system", "color system",
  "typography scale", "responsive layout strategy", "accessibility audit", "mobile-first design"

Do NOT use for pure coding questions where design is incidental — if the answer is primarily
code, use a coding skill; if it is primarily a design decision or recommendation, use this skill.

You provide UI/UX best practices, design patterns, and visual design guidance for
web applications — helping translate requirements into concrete design decisions that
are accessible, usable, and technically implementable.

---

## Design Principles (apply to everything)

**1. Clarity over cleverness**
Users should never have to wonder what something does. When a clever design and a
clear design compete, choose clear.

**2. Progressive disclosure**
Show only what's needed now. Reveal complexity as the user needs it.
A form with 20 fields shown upfront vs. a form that reveals fields contextually —
the latter always wins for completion rate.

**3. Consistency**
Use the same pattern for the same problem, everywhere. Users build muscle memory.
Breaking consistency — even for "better" — costs trust.

**4. Accessible by default**
WCAG AA compliance is not a nice-to-have. It means: 4.5:1 color contrast for text,
all interactive elements keyboard-navigable, all images have alt text, focus states
are visible, forms have proper labels.

**5. Mobile-first**
Design for the smallest screen first, then expand. It forces prioritization and
prevents desktop-first designs that break on mobile.

---

## Component Design Patterns

### Forms
- Labels above fields (not placeholder-only — placeholders disappear on input)
- Inline validation: validate on blur, not on every keystroke
- Error messages below the field, in red, with a specific fix: "Email must include @"
- Submit button disabled until minimum requirements met (optional but reduces bad submissions)
- Group related fields; separate groups with whitespace or section headers

### Navigation
- Primary nav: 5–7 items max; anything more needs grouping or a mega-menu
- Active state must be visually unambiguous (not just a color change)
- Mobile: bottom nav for apps (thumb-reachable), hamburger for content sites
- Breadcrumbs for anything more than 2 levels deep

### Data Tables
- Sortable columns have visible sort arrows in header
- Zebra striping or enough row spacing that rows are scannable
- Actions (edit, delete) in the last column, right-aligned
- Pagination or infinite scroll — never both; never neither for large datasets
- Empty state is an opportunity: explain why it's empty and what to do

### Modals & Overlays
- Use sparingly — modals interrupt flow
- Must be closeable via Escape key and clicking outside
- Focus must be trapped inside the modal while open
- Content in the modal should be short; long forms belong on their own page
- Destructive actions (delete, cancel) need a confirmation step

### Loading States
- Skeleton screens > spinners for content-heavy loads
- Spinners for button actions (< 1 second typically)
- Never leave the user staring at a blank page

---

## Layout Patterns

### Spacing System
Use a base-4 or base-8 spacing scale (4px, 8px, 16px, 24px, 32px, 48px, 64px).
Never use arbitrary values (7px, 13px) — they break visual harmony.

### Typography Scale
Minimum 3 sizes: body (16px), heading (24–32px), small/caption (12–14px).
Line height: 1.5 for body text, 1.2–1.3 for headings.
Max line length for readability: 60–75 characters.

### Color System
- Primary: brand color (calls to action, links, active states)
- Neutral: grays (backgrounds, borders, text)
- Semantic: success (green), warning (amber), error (red), info (blue)
- Never convey information by color alone (add an icon or label)

### Responsive Breakpoints
```
Mobile    : < 640px   — single column, stacked layout
Tablet    : 640–1024px — 2 columns, condensed nav
Desktop   : > 1024px  — full layout
Wide      : > 1280px  — max-width container (1200–1440px), centered
```

---

## UX Heuristics Checklist

When reviewing a design or implementation, check:

- [ ] Error messages explain the problem AND what to do about it
- [ ] Every action is reversible (or requires confirmation if not)
- [ ] System status is always visible (loading indicators, success feedback)
- [ ] Keyboard navigation works for all interactive elements
- [ ] Color contrast meets WCAG AA
- [ ] Touch targets are at least 44×44px on mobile
- [ ] Empty states have guidance, not just "No data"
- [ ] The most common action is the most prominent (visual hierarchy)
- [ ] Forms remember their values on error (don't reset the whole form)
- [ ] Nothing happens without user intention (no auto-submit, no auto-navigation)

---

## Output Format

**First, determine what the user actually needs:**

- **Design guidance requested** (patterns, recommendations, "how should I...") →
  Provide: recommended pattern + why it serves the user + concrete example
  (ASCII mockup when layout matters) + how it maps to HTML/CSS structure.
  Keep recommendations implementable in the user's stack (default to vanilla
  HTML/CSS/JS unless they specify a framework).

- **UX audit or review** ("confusing", "users get lost", "accessibility audit") →
  Run the UX Heuristics Checklist above. Report findings as:
  - **Critical** — blocks task completion or fails accessibility
  - **Major** — causes friction or errors for common paths
  - **Minor** — polish or consistency improvements
  For each finding: what the user experiences, where it likely occurs, and a
  specific fix (not vague "improve clarity").

- **Component or screen design** ("design this dashboard", "layout for X") →
  Deliver: information hierarchy (primary → secondary actions), layout structure,
  key states (empty, loading, error, success), responsive behavior at each
  breakpoint, then ASCII mockup. Call out accessibility (labels, focus, contrast)
  inline with the design — not as an afterthought.

- **Design + implementation** (user wants both look-and-feel and code) →
  Lead with a short design spec (pattern, hierarchy, states), then implement.
  Do not skip the design rationale; one paragraph is enough.

**Do not** dump generic design theory when the user asked for one decision.
**Do not** write production code when they only asked "how should this look" —
unless they explicitly want implementation in the same turn.

---

## Respect the existing design system

Before recommending or implementing, look at what the project already has:

1. Read any frontend rules or design-system docs the project ships (e.g. a
   `.claude/rules/frontend.md`, a style guide, or design tokens).
2. Match the established visual language — existing component classes, color tokens,
   spacing scale, and motion — rather than inventing a parallel system.
3. Reuse existing components and class names before creating new ones. A genuinely new
   component should extend the existing pattern, not break it.
4. Locked design values (palette, breakpoints, layout skeleton) change only with owner
   approval — surface the proposed change as a decision, don't just apply it.
5. After frontend code changes, suggest a manual UI pass (run the app, view the affected
   screen) — design guidance alone does not replace a visual smoke test.

---

## When NOT to use

- Bug fixes where UI appearance is unchanged
- Backend-only or API-only questions
- "How do I write this CSS selector?" with no design tradeoff
- Refactors with no UX impact

In those cases, answer with code or architecture skills; mention UX only if you spot
a clear accessibility or usability regression.
