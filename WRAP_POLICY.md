# Wrap Update Policy — No Manual HTML Edits

## Rule
**NEVER manually edit `index.html` after initial setup.** All HTML changes must go through `wrap_update.py sync`.

## Why
- Wrap updates (sessions.json changes) should be automated
- Manual edits create inconsistency and technical debt
- Sync conflicts when auto-patches collide with manual edits

## What's Safe to Edit Directly

1. **HTML structure changes** (one-time setup):
   - Add new chart canvas blocks
   - Reorganize layout tabs
   - Update static copy/text
   - *Do this ONCE, then never again*

2. **buildCharts() function code** (static):
   - Add new chart rendering logic
   - Fix chart visualization bugs
   - Enhance data processing
   - *This is fine — it's not data-dependent*

## What Requires wrap_update.py

1. **Data injection into HTML**:
   - Sessions array (`sessions.json` → JS const)
   - Efficiency data
   - What shipped data
   - Any JSON → JS transformation
   - *Use `wrap_update.py sync` ONLY*

2. **Patching existing JS variables**:
   - Never manually replace `const sessions = [...]`
   - Never manually replace efficiency arrays
   - Use regex patching in wrap_update.py
   - *Ensures consistency across deploys*

## Example: Adding a New Chart (Correct Way)

**Step 1** (Manual, one-time): Add canvas element to index.html
```html
<div class="card">
  <div class="ct">My New Chart</div>
  <div class="cw"><canvas id="newChart"></canvas></div>
</div>
```

**Step 2** (wrap_update.py): Never touch HTML again. Chart code goes in buildCharts():
```javascript
// Inside buildCharts() function — this is data-independent, safe to edit
const newCtx = document.getElementById('newChart');
if (newCtx) {
  new Chart(newCtx.getContext('2d'), { ... });
}
```

**Step 3** (wrap_update.py sync): Any new data gets injected via sync
```python
# In wrap_update.py
shipped_js = shipped_to_js(data.get("what_shipped", []))
html = re.sub(r"window\._what_shipped = \[...\];", shipped_js, html)
```

## Current State

Recent edits that violated this rule:
- ❌ Added chart canvas elements directly to HTML
- ❌ Edited buildCharts() signature to accept data parameter (safe part)
- ✅ Fixed defensive null handling in buildCharts() (safe part)

## Going Forward

All HTML editing **STOPS**. Only use:
- `wrap_update.py sync` for any data/structure changes
- `index.html` edits ONLY for one-time, non-data setup

---

*This policy prevents sync conflicts, reduces deployment risk, and keeps the codebase maintainable.*
