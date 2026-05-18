#!/usr/bin/env python3
"""
wrap_update.py — Command Centre one-command wrap updater
Run at the end of every session wrap. Replaces all manual HTML editing.

── FULL WRAP (one call does everything) ──────────────────────────────────────
  python3 wrap_update.py wrap \
    --project "Meta" \
    --mins 60 \
    --tokens 45000 \
    --po-mins 60 \
    --equiv-mins 480 \
    --shipped "Item 1" "Item 2" "Item 3" \
    --last-session "Bullet 1" "Bullet 2" \
    --meta-learning "Operational insight this session"

── INDIVIDUAL COMMANDS ───────────────────────────────────────────────────────
  python3 wrap_update.py add-session --label "Mar 24\\nMeta CC" --project "Meta" --mins 60
  # --tokens is optional; auto-extracted from Claude Code JSONL logs if omitted
  python3 wrap_update.py add-efficiency --label "03-24 Meta CC" --po-mins 60 --equiv-mins 480
  python3 wrap_update.py add-shipped --date 2026-03-24 --project Meta --items "Item 1" "Item 2"
  python3 wrap_update.py update-last-session --date "2026-03-24" --project "Meta" --bullets "B1" "B2" --badge "v1.0 · 1h · 8x"
  python3 wrap_update.py add-meta-learning --date "2026-03-24" --text "Insight"
  python3 wrap_update.py bump-version
  python3 wrap_update.py sync
"""

import json
import re
import argparse
import subprocess
import sys
import glob
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

BASE = Path(__file__).parent
SESSIONS_JSON = BASE / "sessions.json"
INDEX_HTML = BASE / "index.html"
MOBILE_HTML = BASE / "mobile.html"


# ── Data helpers ──────────────────────────────────────────────────────────────

def load_data():
    with open(SESSIONS_JSON) as f:
        return json.load(f)


def save_data(data):
    data["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(SESSIONS_JSON, "w") as f:
        json.dump(data, f, indent=2)
    print("✓ sessions.json updated")


def today_label():
    """e.g. 'Mar 24'"""
    return datetime.now().strftime("%-d %b").replace(" ", " ")


def today_iso():
    return datetime.now().strftime("%Y-%m-%d")


def today_mmdd():
    return datetime.now().strftime("%m-%d")


# ── Token extraction from Claude Code JSONL logs ──────────────────────────────

def extract_tokens_by_date():
    """Read all Claude Code JSONL session files, sum input+output tokens per IST date."""
    project_dir = Path.home() / ".claude" / "projects" / "-Users-sunnyhayes"
    jsonl_files = glob.glob(str(project_dir / "*.jsonl"))
    by_date = defaultdict(int)
    for f in jsonl_files:
        total = 0
        first_ts = None
        try:
            with open(f) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    ts = obj.get("timestamp")
                    if ts and not first_ts:
                        first_ts = ts
                    usage = obj.get("message", {}).get("usage", {})
                    if usage:
                        total += usage.get("input_tokens", 0)
                        total += usage.get("output_tokens", 0)
        except Exception:
            continue
        if first_ts and total > 0:
            dt = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            ist = dt + timedelta(hours=5, minutes=30)
            date_key = ist.strftime("%-d %b")  # e.g. '23 Mar' — normalise below
            # Match sessions.json label format: 'Mar 23' → month first
            date_key = ist.strftime("%b %-d")  # e.g. 'Mar 23'
            by_date[date_key] += total
    return dict(by_date)


# ── Chart generation functions (auto-sync via wrap_update) ──────────────────

def generate_chart_canvases():
    """Generate chart canvas HTML blocks."""
    return """
        <div class="card" style="grid-column:1/-1">
          <div class="ct">Tokens Burned — Budget Tracking</div>
          <div class="cw" ondblclick="expandChart('tokensChart','Tokens Burned — Budget Tracking')"><canvas id="tokensChart"></canvas></div>
        </div>
        <div class="card">
          <div class="ct">Project Time Investment</div>
          <div class="cw" ondblclick="expandChart('projectPieChart','Project Time Investment')"><canvas id="projectPieChart"></canvas></div>
        </div>
        <div class="card">
          <div class="ct">What Shipped Timeline</div>
          <div class="cw" ondblclick="expandChart('shippedChart','What Shipped Timeline')"><canvas id="shippedChart"></canvas></div>
        </div>
    """


# ── HTML patch helpers ────────────────────────────────────────────────────────

def patch_version_badge(html, timestamp=None):
    ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")
    return re.sub(
        r'(<div class="ver-badge">)[^<]*(</div>)',
        lambda m: m.group(1) + ts + m.group(2),
        html, count=1
    )


def patch_last_session(html, date, project, bullets, badge):
    """Replace the Last Session card content."""
    li_html = "\n".join(f"            <li>{b}</li>" for b in bullets)
    new_card = f"""          <div class="ct">Last Session — {date}</div>
          <ul class="bl">
{li_html}
          </ul>
          <div style="margin-top:11px;padding-top:10px;border-top:1px solid var(--border);display:flex;gap:6px;flex-wrap:wrap">
            {badge}
          </div>"""
    return re.sub(
        r'<div class="ct">Last Session[^<]*</div>[\s\S]*?(?=</div>\s*</div>\s*<div class="card">)',
        new_card + "\n          ",
        html, count=1
    )


def patch_what_shipped(html, date, project, items):
    """Prepend a new date block at the top of What Shipped and update header date."""
    ri_html = "\n".join(
        f'          <div class="ri"><div class="rtag">{project}</div><div class="rdet">{item}</div></div>'
        for item in items
    )
    new_block = f"""        <div class="rb"><div class="rd">{date}</div>
{ri_html}
        </div>"""
    # Update header date
    dt = datetime.strptime(date, "%Y-%m-%d")
    label = dt.strftime("%b %-d, %Y")
    html = re.sub(
        r'(<div class="ct tog">What Shipped — Full Log · Updated )[^<]*(</div>)',
        lambda m: m.group(1) + label + m.group(2),
        html, count=1
    )
    # Insert new block after the tog title line
    return re.sub(
        r'(<div class="ct tog">What Shipped[^<]*</div>\s*)',
        lambda m: m.group(1) + new_block + "\n        ",
        html, count=1
    )


def patch_meta_learnings(html, date, bullets):
    """Prepend a new Meta Learnings entry and update header date."""
    mbi_html = "\n".join(f'            <div class="mbi">{b}</div>' for b in bullets)
    new_entry = f"""          <div class="mb"><div class="mbd">{date}</div>
{mbi_html}
          </div>"""
    # Update header date
    dt = datetime.strptime(date, "%Y-%m-%d")
    label = dt.strftime("%b %-d, %Y")
    html = re.sub(
        r'(<div class="ct">Meta Learnings — )[^<]*(</div>)',
        lambda m: m.group(1) + label + m.group(2),
        html, count=1
    )
    return re.sub(
        r'(<div class="ct">Meta Learnings[^<]*</div>\s*)',
        lambda m: m.group(1) + new_entry + "\n          ",
        html, count=1
    )


def patch_token_audit(html, date):
    """Update Token Audit header with audit date and next-due date (15 days later)."""
    dt = datetime.strptime(date, "%Y-%m-%d")
    next_due = dt + timedelta(days=15)
    label = dt.strftime("%b %-d, %Y")
    next_label = next_due.strftime("%b %-d, %Y")
    return re.sub(
        r'(<div class="ct tog">Token Audit — )[^·]*(· Next due )[^<]*(</div>)',
        lambda m: m.group(1) + label + " " + m.group(2) + next_label + m.group(3),
        html, count=1
    )


def patch_real_numbers(html, session_count, days_count, total_po_hrs):
    html = re.sub(
        r'(<div class="rk">Sessions logged</div><div class="rv">)\d+ sessions across \d+ days(</div>)',
        lambda m: m.group(1) + f"{session_count} sessions across {days_count} days" + m.group(2),
        html, count=1
    )
    html = re.sub(
        r'(<div class="rk">Total PO time</div><div class="rv">)~[\d.]+ hours[^<]*(</div>)',
        lambda m: m.group(1) + f"~{total_po_hrs} hours (est)" + m.group(2),
        html, count=1
    )
    return html


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_wrap(args):
    """Full wrap in one call — updates sessions.json and patches all HTML."""
    data = load_data()
    now = datetime.now()
    date_iso = now.strftime("%Y-%m-%d")
    date_label = now.strftime("%-d %b")  # e.g. "24 Mar"
    mmdd = now.strftime("%m-%d")
    ts = now.strftime("%Y-%m-%d %H:%M")

    # Derive label from date + project shortname if not provided
    proj_short = args.project.split()[0]  # "ARIA Advisor" → "ARIA"
    session_label = args.label if args.label else f"Mar {now.day}\n{proj_short}"
    eff_label = args.eff_label if args.eff_label else f"{mmdd} {proj_short}"

    # 1. Add session entry (auto-extract tokens from JSONL if not provided)
    tokens = args.tokens
    if tokens is None:
        date_key = now.strftime("%b %-d")
        tokens_by_date = extract_tokens_by_date()
        tokens = tokens_by_date.get(date_key)
        if tokens:
            print(f"✓ auto-extracted tokens for {date_key}: {tokens:,}")
    data["sessions"].append({
        "label": session_label,
        "project": args.project,
        "mins": args.mins,
        "tokens": tokens
    })

    # 2. Add efficiency entry
    data["efficiency"].append({
        "label": eff_label,
        "po_mins": args.po_mins,
        "equiv_mins": args.equiv_mins
    })

    # 3. Add what_shipped entry
    if args.shipped:
        data["what_shipped"].insert(0, {
            "date": date_iso,
            "project": args.project,
            "items": args.shipped
        })

    save_data(data)

    # 4. Patch HTML
    html = INDEX_HTML.read_text()

    # Version badge
    html = patch_version_badge(html, ts)

    # Last Session panel
    if args.last_session:
        po_hrs = round(args.po_mins / 60, 1)
        ratio = round(args.equiv_mins / args.po_mins) if args.po_mins else "?"
        badge = args.badge if args.badge else (
            f'<span class="b bp">{args.project}</span>'
            f'<span class="b bsl">~{po_hrs} hrs PO</span>'
            f'<span class="b bg">~{ratio}x compression</span>'
        )
        html = patch_last_session(html, date_iso, args.project, args.last_session, badge)

    # What Shipped
    if args.shipped:
        html = patch_what_shipped(html, date_iso, args.project, args.shipped)

    # Meta Learnings
    if args.meta_learning:
        html = patch_meta_learnings(html, date_iso, args.meta_learning)

    # Token Audit header — always update next-due to 15 days from today
    html = patch_token_audit(html, date_iso)

    # Real Numbers card
    total_po = sum(e["po_mins"] for e in data["efficiency"])
    session_count = len(data["sessions"])
    # Count unique days
    days = set()
    for s in data["sessions"]:
        day = s["label"].split("\\n")[0].strip()
        days.add(day)
    html = patch_real_numbers(html, session_count, len(days), round(total_po / 60, 1))

    INDEX_HTML.write_text(html)
    print(f"✓ index.html patched ({len(html):,} bytes)")

    # Rebuild project cards + pColor from sessions.json (single source of truth)
    cmd_rebuild_projects(type('A', (), {'command': 'rebuild-projects'})())

    print("\n🚀 Committing + deploying...")
    try:
        subprocess.run(["git", "add", "."], cwd=BASE, check=True)
        subprocess.run(["git", "commit", "-m", f"wrap: {args.project} — {ts}"], cwd=BASE, check=True)
        subprocess.run(["git", "push"], cwd=BASE, check=True)
        print("✓ Pushed to GitHub")
        # Auto-deploy to Vercel
        result = subprocess.run(["vercel", "--prod"], cwd=BASE, capture_output=True, text=True)
        output = result.stdout + result.stderr
        # Extract deployment URL
        import re as _re
        url_match = _re.search(r'https://command-centre-[a-z0-9]+-sunder-vasudevans-projects\.vercel\.app', output)
        if url_match:
            deploy_url = url_match.group(0)
            subprocess.run(["vercel", "alias", deploy_url, "claude-command-centre.vercel.app"], cwd=BASE, check=True)
            print(f"✓ Deployed → claude-command-centre.vercel.app")
        else:
            print("⚠️  Deploy succeeded but couldn't extract URL for alias — run manually:")
            print("   vercel alias <url> claude-command-centre.vercel.app")
    except subprocess.CalledProcessError as e:
        print(f"❌ Deploy step failed: {e}")

    # Mark wrap as verified for wrap-verify.py
    _mark_wrap_done()


def cmd_add_session(args):
    data = load_data()
    data["sessions"].append({
        "label": args.label,
        "project": args.project,
        "mins": args.mins,
        "tokens": args.tokens
    })
    save_data(data)
    print(f"  Added: {args.label} / {args.project} / {args.mins}m")


def cmd_add_efficiency(args):
    data = load_data()
    data["efficiency"].append({
        "label": args.label,
        "po_mins": args.po_mins,
        "equiv_mins": args.equiv_mins
    })
    save_data(data)
    print(f"  Added efficiency: {args.label}")


def cmd_add_shipped(args):
    data = load_data()
    data["what_shipped"].insert(0, {
        "date": args.date,
        "project": args.project,
        "items": args.items
    })
    save_data(data)
    print(f"  Added {len(args.items)} shipped items for {args.date}")


def cmd_update_last_session(args):
    html = INDEX_HTML.read_text()
    po_hrs = round(args.po_mins / 60, 1) if args.po_mins else ""
    badge = args.badge or f'<span class="b bp">{args.project}</span><span class="b bsl">~{po_hrs} hrs PO</span>'
    html = patch_last_session(html, args.date, args.project, args.bullets, badge)
    INDEX_HTML.write_text(html)
    print("✓ Last Session panel updated")

    # Mark wrap as verified for wrap-verify.py
    _mark_wrap_done()


def cmd_add_meta_learning(args):
    html = INDEX_HTML.read_text()
    html = patch_meta_learnings(html, args.date, [args.text])
    INDEX_HTML.write_text(html)
    print("✓ Meta Learnings updated")


def cmd_bump_version(args):
    ts = args.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")
    html = patch_version_badge(INDEX_HTML.read_text(), ts)
    INDEX_HTML.write_text(html)
    print(f"✓ Version badge → {ts}")


def _mark_wrap_done():
    """Call wrap-verify.py to mark wrap as executed."""
    try:
        script = BASE / "wrap-verify.py"
        if script.exists():
            subprocess.run([sys.executable, str(script), "--mark-done"], check=False)
    except Exception as e:
        # Don't fail wrap if verify script has issues
        pass


def _build_profile_tab_inner(cycles):
    """Build the entire inner HTML of tab-profile (everything between <div id="tab-profile"> and </div>)."""
    import json as _json
    cycle = cycles[0]

    # Dropdown
    opts = "\n".join(f'          <option value="{c["id"]}">{c["label"]}</option>' for c in cycles)
    dropdown = (
        f'<select id="cycle-select" class="b bsl" '
        f'style="cursor:pointer;font-size:12px;padding:2px 6px;border:1px solid var(--border);'
        f'border-radius:4px;background:var(--bg2);color:var(--text)" onchange="switchCycle(this.value)">\n'
        f'{opts}\n        </select>'
    )

    # Assessment
    assessment_html = cycle["assessment"].replace("\n\n", "<br><br>")

    # Traits
    trait_cards = "\n".join(
        f'          <div class="trcard {t["type"]}"><div class="trtype">{t["label"]}</div><div class="trname">{t["name"]}</div></div>'
        for t in cycle["traits"]
    )

    # Strengths
    strength_rows = "\n".join(
        f'          <div class="rr"><div class="rk">{s["icon"]} {s["title"]}</div><div class="rv">{s["desc"]}</div></div>'
        for s in cycle["strengths"]
    )

    # Gaps
    gap_rows = "\n".join(
        f'          <div class="gap-row"><div class="gap-row-icon">{g["icon"]}</div>'
        f'<div><div class="gap-row-title">{g["title"]}</div>'
        f'<div class="gap-row-desc">{g["desc"]}</div>'
        f'<span class="gap-row-fix">Fix: {g["fix"]}</span></div></div>'
        for g in cycle["gaps"]
    )

    return f"""
      <div class="ph">
        <div><div class="ph-title">Profile</div><div class="ph-sub">How Claude sees Sunny Hayes — evidence-based, no sugarcoating</div></div>
        {dropdown}
      </div>

      <div class="card">
        <div class="ct">Claude's Assessment — In Plain English</div>
        <div id="assessment-body" style="font-size:14px;color:var(--text2);line-height:1.8;max-width:720px">{assessment_html}</div>
        <div class="countdown-bar-wrap">
          <div class="countdown-label"><span id="cycle-range">Appraisal cycle: {cycle["label"]}</span><span class="countdown-val" id="countdown-days"></span></div>
          <div class="progress-bar-outer"><div class="progress-bar-inner" id="appraisal-progress" style="width:0%"></div></div>
        </div>
      </div>

      <div class="card">
        <div class="ct">Trait Profile</div>
        <div id="traits-body" class="trgrid">
{trait_cards}
        </div>
      </div>

      <div class="g2">
        <div class="card">
          <div class="ct">Observed Strengths</div>
          <div id="strengths-body">
{strength_rows}
          </div>
        </div>
        <div class="card">
          <div class="ct">Honest Gaps</div>
          <div id="gaps-body">
{gap_rows}
          </div>
        </div>
      </div>
    """


def patch_profile(html, cycles):
    """Inject appraisal cycle data + dropdown + JS renderer into profile tab."""
    import json as _json

    # 1. Replace/inject JS data block — sanitize assessment newlines first
    safe_cycles = []
    for c in cycles:
        sc = dict(c)
        sc["assessment"] = sc["assessment"].replace("\n", "\\n")
        safe_cycles.append(sc)
    cycles_js = "window._appraisal_cycles = " + _json.dumps(safe_cycles, ensure_ascii=False) + ";"
    if "window._appraisal_cycles" in html:
        html = re.sub(r"window\._appraisal_cycles = \[[\s\S]*?\];", cycles_js, html, count=1)
    else:
        html = html.replace("</script>\n</body>", f"{cycles_js}\n</script>\n</body>", 1)

    # 2. Replace entire profile tab inner content atomically
    new_inner = _build_profile_tab_inner(cycles)
    html = re.sub(
        r'(<div class="tab-panel[^"]*" id="tab-profile">)[\s\S]*?(<!-- ===== REFERENCE TAB)',
        lambda m: m.group(1) + new_inner + "\n    </div>\n\n    " + m.group(2),
        html, count=1
    )

    # 3. Inject switchCycle JS if not present
    switch_js = """
function switchCycle(id) {
  const c = (window._appraisal_cycles || []).find(x => x.id === id);
  if (!c) return;
  const ab = document.getElementById('assessment-body');
  if (ab) ab.innerHTML = c.assessment.replace(/\\n\\n/g,'<br><br>');
  const cr = document.getElementById('cycle-range');
  if (cr) cr.textContent = 'Appraisal cycle: ' + c.label;
  const tb = document.getElementById('traits-body');
  if (tb) tb.innerHTML = c.traits.map(t => `<div class="trcard ${t.type}"><div class="trtype">${t.label}</div><div class="trname">${t.name}</div></div>`).join('');
  const sb = document.getElementById('strengths-body');
  if (sb) sb.innerHTML = c.strengths.map(s => `<div class="rr"><div class="rk">${s.icon} ${s.title}</div><div class="rv">${s.desc}</div></div>`).join('');
  const gb = document.getElementById('gaps-body');
  if (gb) gb.innerHTML = c.gaps.map(g => `<div class="gap-row"><div class="gap-row-icon">${g.icon}</div><div><div class="gap-row-title">${g.title}</div><div class="gap-row-desc">${g.desc}</div><span class="gap-row-fix">Fix: ${g.fix}</span></div></div>`).join('');
  const start = new Date(c.start), end = new Date(c.end), now = new Date();
  const pct = Math.min(100,Math.max(0,Math.round((now-start)/(end-start)*100)));
  const el = document.getElementById('appraisal-progress');
  if (el) el.style.width = pct + '%';
  const cd = document.getElementById('countdown-days');
  if (cd) { const days = Math.max(0,Math.ceil((end-now)/86400000)); cd.textContent = days > 0 ? days+' days remaining' : 'Cycle complete'; }
}
"""
    if "function switchCycle" not in html:
        html = html.replace("function goHome()", switch_js + "\nfunction goHome()")

    return html


def cmd_update_profile(args):
    data = load_data()
    cycles = data.get("appraisal_cycles", [])
    if not cycles:
        print("✗ No appraisal_cycles in sessions.json")
        return
    html = INDEX_HTML.read_text()
    html = patch_profile(html, cycles)
    INDEX_HTML.write_text(html)
    print(f"✓ Profile tab updated ({len(cycles)} cycle(s))")


def cmd_sync(args):
    data = load_data()
    changed = 0
    if changed:
        save_data(data)
    print("✓ sessions.json is up to date. Charts fetch live from sessions.json.")


def cmd_check(args):
    """Pre-deploy sanity check. Run before every deploy."""
    data = load_data()
    html = INDEX_HTML.read_text()
    sessions = data.get("sessions", [])
    efficiency = data.get("efficiency", [])
    what_shipped = data.get("what_shipped", [])
    projects = data.get("projects", [])

    errors = []
    warnings = []

    # 1. Efficiency coverage — every unique session date should have an efficiency entry
    session_dates = set()
    for s in sessions:
        day = s["label"].split("\\n")[0].strip()
        session_dates.add(day)
    eff_labels = set(e["label"] for e in efficiency)
    # Extract date part from eff labels (format: MM-DD Project or similar)
    # Check count gap — efficiency should have roughly same count as unique session dates
    eff_count = len(efficiency)
    sess_date_count = len(session_dates)
    if eff_count < sess_date_count - 2:
        errors.append(f"Efficiency entries ({eff_count}) significantly fewer than session dates ({sess_date_count}) — run add-efficiency for missing sessions")

    # 2. what_shipped — check most recent session has a what_shipped entry
    if sessions and what_shipped:
        last_session_date = sessions[-1]["label"].split("\\n")[0]
        # Convert label like "May 11" to approximate ISO
        last_shipped_date = what_shipped[0]["date"]  # most recent
        if not last_shipped_date:
            warnings.append("Most recent what_shipped entry has no date")
    elif sessions and not what_shipped:
        errors.append("No what_shipped entries — run add-shipped")

    # 3. All session projects exist in pColor (index.html)
    pcolor_match = re.search(r'const pColor = \{([\s\S]*?)\};', html)
    if pcolor_match:
        pcolor_block = pcolor_match.group(1)
        session_projects = set(s["project"] for s in sessions)
        missing_colors = []
        pcolor_lower = pcolor_block.lower()
        for proj in session_projects:
            if f"'{proj.lower()}'" not in pcolor_lower and f'"{proj.lower()}"' not in pcolor_lower:
                missing_colors.append(proj)
        if missing_colors:
            errors.append(f"Projects missing from pColor (charts will be grey): {missing_colors}")
            errors.append(f"  Fix: python3 wrap_update.py rebuild-projects")

    # 4. Fetch callback resets _chartsBuilt
    if "window._chartsBuilt = false;" not in html:
        errors.append("fetch callback missing '_chartsBuilt = false' reset — charts may not rebuild after fetch")

    # 5. Sessions count vs Real Numbers card
    real_nums_match = re.search(r'(\d+)\s*</div>\s*<div class="psn2?">Sessions', html)
    if real_nums_match:
        html_count = int(real_nums_match.group(1))
        if html_count != len(sessions):
            warnings.append(f"Real Numbers card shows {html_count} sessions but sessions.json has {len(sessions)} — run wrap to sync")

    # 6. projects[] exists and has entries
    if not projects:
        errors.append("No projects[] in sessions.json — run rebuild-projects after adding projects")

    # 7. mobile.html pColor in sync with index.html
    if INDEX_HTML.exists() and MOBILE_HTML.exists():
        mobile_html = MOBILE_HTML.read_text()
        mobile_pcolor = re.search(r'const pColor = \{([\s\S]*?)\};', mobile_html)
        index_pcolor = re.search(r'const pColor = \{([\s\S]*?)\};', html)
        if mobile_pcolor and index_pcolor:
            # Count entries
            m_count = mobile_pcolor.group(1).count("'#")
            i_count = index_pcolor.group(1).count("'#")
            if m_count != i_count:
                errors.append(f"pColor out of sync: index.html has {i_count} entries, mobile.html has {m_count} — run rebuild-projects")

    # Report
    print("\n── Pre-deploy sanity check ─────────────────────────────")
    if not errors and not warnings:
        print("✅ All checks passed — safe to deploy")
    else:
        for e in errors:
            print(f"  ❌ {e}")
        for w in warnings:
            print(f"  ⚠️  {w}")
        if errors:
            print(f"\n  {len(errors)} error(s) must be fixed before deploy")
            return False
    print("────────────────────────────────────────────────────────\n")
    return True


def _build_pcolor_js(projects):
    """Build the pColor object literal from projects list."""
    entries = []
    seen = set()
    for p in projects:
        name = p["name"]
        color = p["color"]
        if name not in seen:
            entries.append(f"    '{name}':'{color}'")
            seen.add(name)
        # ARIA aliases
        if name == "ARIA Advisor":
            for alias in ["ARIA", "ARIA, Claude Memory, User Memory"]:
                if alias not in seen:
                    entries.append(f"    '{alias}':'{color}'")
                    seen.add(alias)
        if name == "As Gurudev Says" and "Gurudev" not in seen:
            entries.append(f"    'Gurudev':'{color}'")
            seen.add("Gurudev")
        # Add lowercase alias for felt
        if name == "Felt" and "felt" not in seen:
            entries.append(f"    'felt':'{color}'")
            seen.add("felt")
        if name == "Claude Command Module":
            for alias in ["Meta", "Ctx Sys", "Paperclip", "x-bookmarks-aggregator"]:
                colors = {"Meta": "#e10600", "Ctx Sys": "#64748b", "Paperclip": "#a855f7", "x-bookmarks-aggregator": "#0891b2"}
                if alias not in seen:
                    entries.append(f"    '{alias}':'{colors[alias]}'")
                    seen.add(alias)
    return "  const pColor = {\n" + ",\n".join(entries) + "\n  };"


def patch_pcolor(html, projects):
    """Replace pColor object in HTML with one built from sessions.json projects."""
    new_pcolor = _build_pcolor_js(projects)
    return re.sub(
        r'  const pColor = \{[\s\S]*?\};',
        new_pcolor,
        html, count=1
    )


def _build_project_card_html(p, idx=0):
    """Render a single project card as an accordion from a project dict."""
    color = p["color"]
    name = p["name"]
    tagline = p["tagline"]
    version = p.get("version", "")
    status = p.get("status", "Live")
    url = p.get("url", "")
    stack = p.get("stack", [])
    whats_next = p.get("whats_next", [])
    learnt = p.get("learnt", [])
    learnt_date = p.get("learnt_date", "")
    last_session = p.get("last_session", "")

    status_class = "bg" if status in ("Live", "Render Live") else ("bp" if status == "In Progress" else "bsl")
    url_html = f'<a href="{url}" class="purl" target="_blank" onclick="event.stopPropagation()">{url.replace("https://","")}</a>' if url else ""
    stack_html = "".join(f'<span class="pill">{s}</span>' for s in stack)
    next_html = "\n".join(f"              <li>{n}</li>" for n in whats_next)
    learnt_html = "\n".join(f"              <li>{l}</li>" for l in learnt)
    last_html = f'<span style="font-size:10px;color:var(--text2)">Last: {last_session}</span>' if last_session else ""
    card_id = f"pc_{idx}"

    return f"""      <div class="pc" style="border-left-color:{color};padding:0;overflow:hidden">
        <div onclick="(function(){{var b=document.getElementById('{card_id}');b.style.display=b.style.display==='none'?'block':'none'}})()" style="cursor:pointer;padding:12px 14px;display:flex;align-items:center;justify-content:space-between;gap:8px">
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
              <span class="pname" style="color:{color}">{name}</span>
              <span class="b bp">{version}</span>
              <span class="b {status_class}">{status}</span>
              {last_html}
            </div>
            <div class="ptag" style="margin-top:2px">{tagline}</div>
          </div>
          <span style="font-size:14px;color:var(--text2);flex-shrink:0">›</span>
        </div>
        <div id="{card_id}" style="display:none;padding:0 14px 12px 14px;border-top:1px solid var(--border)">
          {f'<div style="margin-top:8px">{url_html}</div>' if url_html else ""}
          <div class="pstack" style="margin-top:8px">{stack_html}</div>
          <div class="g2" style="gap:var(--gap);margin-top:8px">
            <div>
              <div class="pst">What's Next</div>
              <ul class="bl" style="font-size:12px">
{next_html}
              </ul>
            </div>
            <div>
              <div class="pst">What Was Learnt — {learnt_date}</div>
              <ul class="bl" style="font-size:12px">
{learnt_html}
              </ul>
            </div>
          </div>
        </div>
      </div>"""


def patch_project_cards(html, projects):
    """Replace all project cards (between stitle Projects and Parking Lot tab comment)."""
    # Sort: projects with last_session first (most recent), then others
    def sort_key(p):
        ls = p.get("last_session", "")
        if not ls:
            return "0000-00-00"
        # normalise "May 18" style to sortable
        import re as _re
        m = _re.match(r'(\w+ \d+)$', ls)
        if m:
            return ls  # keep as-is, will sort lexically
        return ls
    sorted_projects = sorted(projects, key=sort_key, reverse=True)
    cards_html = "\n\n".join(_build_project_card_html(p, idx=i) for i, p in enumerate(sorted_projects))
    count = len(projects)
    # Update project count in header
    html = re.sub(r'\d+ active \xb7 North star', f'{count} active \xb7 North star', html, count=1)
    # Replace block between stitle and Parking Lot tab
    return re.sub(
        r'(<div class="stitle">Projects</div>\s*\n)([\s\S]*?)(\s*</div>\s*\n\s*<!-- ===== PARKING LOT)',
        lambda m: m.group(1) + "\n" + cards_html + "\n\n    " + m.group(3),
        html, count=1
    )


def cmd_rebuild_projects(args):
    """Re-render all project cards and pColor from sessions.json projects[]."""
    data = load_data()
    projects = data.get("projects", [])
    if not projects:
        print("✗ No projects in sessions.json. Add via: wrap_update.py add-project")
        return
    html = INDEX_HTML.read_text()
    html = patch_project_cards(html, projects)
    html = patch_pcolor(html, projects)
    INDEX_HTML.write_text(html)
    # Also sync mobile.html pColor
    mobile_html = MOBILE_HTML.read_text()
    mobile_html = patch_pcolor(mobile_html, projects)
    MOBILE_HTML.write_text(mobile_html)
    print(f"✓ Project cards rebuilt ({len(projects)} projects)")
    print(f"✓ pColor synced in index.html + mobile.html")


def cmd_update_project(args):
    """Update a project's fields in sessions.json then rebuild cards."""
    data = load_data()
    projects = data.get("projects", [])
    proj = next((p for p in projects if p["name"].lower() == args.name.lower()), None)
    if not proj:
        print(f"✗ Project '{args.name}' not found. Use add-project to create it.")
        return
    if args.version: proj["version"] = args.version
    if args.status: proj["status"] = args.status
    if args.url: proj["url"] = args.url
    if args.tagline: proj["tagline"] = args.tagline
    if args.whats_next: proj["whats_next"] = args.whats_next
    if args.learnt: proj["learnt"] = args.learnt
    if args.learnt_date: proj["learnt_date"] = args.learnt_date
    save_data(data)
    # Rebuild HTML
    cmd_rebuild_projects(type('A', (), {'command': 'rebuild-projects'})())
    print(f"✓ Project '{args.name}' updated")


def cmd_add_project(args):
    """Add a new project to sessions.json and rebuild cards + pColor."""
    data = load_data()
    projects = data.setdefault("projects", [])
    if any(p["name"].lower() == args.name.lower() for p in projects):
        print(f"✗ Project '{args.name}' already exists. Use update-project.")
        return
    # Insert before Claude Command Module (always last)
    new_proj = {
        "name": args.name,
        "color": args.color,
        "url": args.url or "",
        "stack": args.stack or [],
        "status": args.status or "In Progress",
        "version": args.version or "v0.1.0",
        "tagline": args.tagline or "",
        "whats_next": args.whats_next or [],
        "learnt_date": today_iso(),
        "learnt": []
    }
    # Insert second-to-last (before Command Module)
    insert_pos = len(projects) - 1 if projects else 0
    projects.insert(insert_pos, new_proj)
    save_data(data)
    cmd_rebuild_projects(type('A', (), {'command': 'rebuild-projects'})())
    print(f"✓ Project '{args.name}' added with color {args.color}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Command Centre wrap updater")
    sub = p.add_subparsers(dest="command")

    # wrap — full one-call command
    pw = sub.add_parser("wrap", help="Full wrap in one call")
    pw.add_argument("--project", required=True)
    pw.add_argument("--mins", type=int, required=True, help="Session duration in minutes")
    pw.add_argument("--po-mins", type=int, required=True, help="PO active time in minutes")
    pw.add_argument("--equiv-mins", type=int, required=True, help="3-person equivalent in minutes")
    pw.add_argument("--tokens", type=int, default=None)
    pw.add_argument("--label", default=None, help='Override session label e.g. "Mar 24\\nMeta CC"')
    pw.add_argument("--eff-label", default=None, help='Override efficiency label e.g. "03-24 Meta CC"')
    pw.add_argument("--shipped", nargs="+", default=None, help="What shipped (one string per bullet)")
    pw.add_argument("--last-session", nargs="+", default=None, help="Last session bullets")
    pw.add_argument("--meta-learning", nargs="+", default=None, help="Meta/operational learning bullets")
    pw.add_argument("--badge", default=None, help="Override badge HTML in Last Session panel")

    # add-session
    ps = sub.add_parser("add-session")
    ps.add_argument("--label", required=True)
    ps.add_argument("--project", required=True)
    ps.add_argument("--mins", type=int, required=True)
    ps.add_argument("--tokens", type=int, default=None)

    # add-efficiency
    pe = sub.add_parser("add-efficiency")
    pe.add_argument("--label", required=True)
    pe.add_argument("--po-mins", type=int, required=True)
    pe.add_argument("--equiv-mins", type=int, required=True)

    # add-shipped
    psh = sub.add_parser("add-shipped")
    psh.add_argument("--date", required=True)
    psh.add_argument("--project", required=True)
    psh.add_argument("--items", nargs="+", required=True)

    # update-last-session
    pls = sub.add_parser("update-last-session")
    pls.add_argument("--date", required=True)
    pls.add_argument("--project", required=True)
    pls.add_argument("--bullets", nargs="+", required=True)
    pls.add_argument("--po-mins", type=int, default=None)
    pls.add_argument("--badge", default=None)

    # add-meta-learning
    pml = sub.add_parser("add-meta-learning")
    pml.add_argument("--date", required=True)
    pml.add_argument("--text", required=True)

    # bump-version
    pv = sub.add_parser("bump-version")
    pv.add_argument("--timestamp", default=None, help="Override timestamp e.g. '2026-03-25 14:30'")

    # update-profile
    sub.add_parser("update-profile", help="Patch profile tab with appraisal cycle data from sessions.json")

    # sync
    sub.add_parser("sync")

    # check — pre-deploy sanity check
    sub.add_parser("check", help="Pre-deploy sanity check — run before every deploy")

    # rebuild-projects — re-render project cards + pColor from sessions.json
    sub.add_parser("rebuild-projects", help="Re-render project cards + pColor in both HTML files from sessions.json")

    # update-project
    pup = sub.add_parser("update-project", help="Update a project's fields in sessions.json then rebuild")
    pup.add_argument("--name", required=True)
    pup.add_argument("--version", default=None)
    pup.add_argument("--status", default=None)
    pup.add_argument("--url", default=None)
    pup.add_argument("--tagline", default=None)
    pup.add_argument("--whats-next", nargs="+", default=None, dest="whats_next")
    pup.add_argument("--learnt", nargs="+", default=None)
    pup.add_argument("--learnt-date", default=None, dest="learnt_date")

    # add-project
    pap = sub.add_parser("add-project", help="Add a new project to sessions.json and rebuild cards + pColor")
    pap.add_argument("--name", required=True)
    pap.add_argument("--color", required=True, help="Hex color e.g. #f97316")
    pap.add_argument("--url", default=None)
    pap.add_argument("--tagline", default=None)
    pap.add_argument("--version", default="v0.1.0")
    pap.add_argument("--status", default="In Progress")
    pap.add_argument("--stack", nargs="+", default=None)
    pap.add_argument("--whats-next", nargs="+", default=None, dest="whats_next")

    args = p.parse_args()
    dispatch = {
        "wrap": cmd_wrap,
        "add-session": cmd_add_session,
        "add-efficiency": cmd_add_efficiency,
        "add-shipped": cmd_add_shipped,
        "update-last-session": cmd_update_last_session,
        "add-meta-learning": cmd_add_meta_learning,
        "bump-version": cmd_bump_version,
        "update-profile": cmd_update_profile,
        "sync": cmd_sync,
        "check": cmd_check,
        "rebuild-projects": cmd_rebuild_projects,
        "update-project": cmd_update_project,
        "add-project": cmd_add_project,
    }
    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
