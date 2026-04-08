# Command Centre — NOTES.md

## Current State: v3.3.0 (2026-04-08) — Graphs tab (mobile only)

### Session 2026-04-08 — Graphs tab
- Moved charts out of Command tab into dedicated Graphs tab in `mobile.html`
- 6th bottom nav button (📊 Graphs) added; label font reduced to 9px to fit 6 buttons
- `buildCharts()` converted from IIFE to named function; lazy-init on first Graphs tab open
- `index.html` untouched

---

## v3.2.0 (2026-03-28) — validation gates + bug fix

← START HERE NEXT SESSION

### Session 2026-03-28 — Graphs blank + validation gates
- **Bug:** Sessions array had literal newlines in labels (manual edit bypassed automation), breaking JavaScript syntax. Graphs went blank.
- **Root cause:** wrap_update.py never invoked. Someone directly typed into index.html, breaking `const sessions = [...]`
- **Fix:** Corrected malformed session entries, re-deployed to production
- **Prevention:** Added validation gates:
  - Pre-commit hook: blocks manual edits to dynamic content (Last Session, What Shipped, sessions array)
  - wrap_update.py: improved `validate_js_syntax()` to catch incomplete objects
  - Error messages guide users to use wrap_update.py instead
- **Research:** Explored UI UX Pro Max Skill (design automation). Parked pending deeper integration research.
- **Also researched:** Claude-Mem (session recovery + cross-project search) + Superpowers (7-stage TDD workflow). Both parked, need compatibility analysis with wrap protocol.
- **Status:** All changes committed. command-centre deployment validated.

## Previous State: v3.1.0 (2026-03-27) — restored

### Session 2026-03-27 — Paperclip migration + revert
- Paperclip "Best of Both Combined" migration executed: 43 todo issues, 18 done issues seeded, COMPANY.md enriched with 16 sections
- Attempted Paperclip live API integration into index.html (Parking Lot + What Shipped tabs fetching from localhost:3100)
- Integration broke collapsibles + graphs — reverted to index_backup_2026-03-27.html
- Deployed clean restore to claude-command-centre.vercel.app
- **Decision locked:** Paperclip integration = link to Railway URL in new tab, not embedded fetch. Build when Railway deploy is ready.

### Open flags (updated)
- Add "Open Paperclip →" button to Command Centre once Railway deploy is live (swap localhost:3100 for Railway URL)
- Fix "Sunny Hews" typo in Paperclip user profile (not in index.html — in Paperclip UI settings)
- Set Git Repo field for all Paperclip projects

### What shipped — v3.1.0 (2026-03-24)
- **Parking Lot**: single column layout (was 4-col grid), all cards open by default, per-project border colors (Felt=pink, ARIA=blue, BzHub=green, Helm=sky, Gurudev=purple, Swara=amber, ARIA Personal=indigo, Command Module=emerald)
- **expandChart() fixed**: was broken due to `JSON.stringify` deep-copy of Chart.js internal proxy. Now rebuilds config manually from `src.data` — modal chart renders correctly.
- **Collapse bug fixed**: cards in non-active tabs had `scrollHeight=0` at init (tab was hidden). On expand now forces `max-height: none` to measure natural height, then sets it. Token Audit and all non-Command-tab cards now collapse/expand correctly.
- **CLAUDE.md updated**: added verification rule for command-centre HTML changes — open in browser before marking done.
- **Bug audit documented**: 5 Claude oversights, 1 unclear prompt, 3 real bugs — all resolved this session.

### What shipped — v3.0.0 (2026-03-24)
- **Full redesign shipped**: Newdesign.html → index.html (6-tab layout replacing 9-tab dark design)
- **Tabs**: Command | Projects | Parking Lot | Standards | Profile | Reference
- **All content migrated**: 27 sessions, full What Shipped, all Meta Learnings, all project data
- **Parking Lot tab**: 45 items across 7 projects
- **mobile.html restructured**: Insights tab removed, Parking Lot added, charts added to Command tab
- **sessions.json**: Data layer created — source of truth for all session/efficiency data
- **wrap_update.py**: CLI tool for adding sessions, efficiency rows, shipped items without touching HTML
- **Deployed**: claude-command-centre.vercel.app

### Next up
- FEAT-001: Wire wrap_update.py into session_wrap.md so wrap auto-updates sessions.json + syncs HTML
- FEAT-002: Add last-session summary card to Command tab (auto-populated from sessions.json)
- FEAT-003: sessions.json data layer → consider whether index.html can fetch it at load time (static JSON on Vercel)

### Open flags
- Newdesign.html can be deleted after confirming index.html is stable for 1 week
- wrap_update.py sync() regex needs testing against real index.html — do a dry run before trusting it

---

## Current State: v2.5.0 (2026-03-21)

### What shipped in this session
- Mobile top bar fix: brand text hidden on small screens (`display:none` via `@media`), tab row scrollable horizontally — top nav fully usable on phone
- Compression ratio chart resized to full width, canvas height bumped from 280px to 380px
- Session log redesigned: date-grouped blocks, time-stamped entries, no version numbers, per-session learnings
- Skills panel updated: `/lights-out` and `/wrap` added with correct Sunny/gstack source flags
- Project descriptions added to all 6 projects in the projects panel
- Swara Samipyam added to sidebar + project panel count bumped to 6
- Wrap protocol locked: MEMORY.md + command-centre index both mandatory at every wrap; one row per session in efficiency table; git log is source of truth

---

## Session Prompt Log

### 2026-03-21 ~23:30 session
1. "Do it autonomously and then done for now" — resize compression chart + full wrap
