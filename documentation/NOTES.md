# Command Centre — Notes & Design Decisions

---

## Design Decisions

### 2026-03-21 — Hosting
- **Decision:** Host on Vercel via CLI only — no GitHub auto-deploy connection.
- **Why:** Command Centre is a personal tool with sensitive session/appraisal data. CLI-only gives full control over when changes go live. Auto-deploy disabled to prevent accidental exposure.
- **Convention:** `vercel --prod` run manually at each major release only.
- **Live URL:** https://claude-command-centre.vercel.app
- **Alias set:** `claude-command-centre.vercel.app` → `command-centre-hr08oww8c-sunder-vasudevans-projects.vercel.app`

### 2026-03-21 — "How Claude Sees Me" Tab
- **Decision:** Added as a new tab using existing `<details class="section">` collapsible pattern. Four collapsible sections: Assessment (open), Trait Profile, Strengths, Honest Gaps. 15-Day Focus (open) with countdown bar.
- **Why:** Periodic appraisal (every 15 days) to track Sunny's working patterns, gaps, and growth areas. Honest and balanced — not celebratory.
- **Sections open by default:** Assessment + 15-Day Focus. Others collapsed to reduce visual noise.

### 2026-03-21 — 15-Day Appraisal Cycle
- **Decision:** Cycle hardcoded per period (Mar 21 – Apr 5, 2026). JS calculates days remaining + % progress. Badge turns amber when ≤2 days out.
- **Why:** Forces a refresh cadence. Makes the appraisal feel live, not static.
- **Update protocol:** At each new cycle, update cycle dates in hero banner + 15-Day Focus card title + JS `cycleStart`/`cycleEnd` constants.

### 2026-03-21 — Index Page Redesign (Option B — Operator View)
- **Decision:** Full rewrite of index.html using Option B "Operator View" design.
- **Why:** Previous design was built incrementally and felt cluttered. Option B chosen from 3 previews (A: Clear Signal, B: Operator View, C: Broadsheet).
- **Design:** Dark header (#1a1d2e) + Inter font + persistent 240px sidebar (metrics + quick nav) + data panels with alternating row tints + monospace numerics.
- **Version:** v2.2.0
- **Previews saved:** `documentation/design-previews/preview-a.html`, `preview-b.html`, `preview-c.html`

### 2026-03-21 — Edit Approval Gate Exception
- **Decision:** Clear-cut tasks (single file, obvious scope, no content/design decisions) skip the approval gate.
- **Why:** Gate is for ambiguous or risky changes. Trivial well-scoped edits don't need it.
