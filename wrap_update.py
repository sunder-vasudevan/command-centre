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
  python3 wrap_update.py add-session --label "Mar 24\\nMeta CC" --project "Meta" --mins 60 --tokens 45000
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
from pathlib import Path
from datetime import datetime

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


# ── JS array builders ─────────────────────────────────────────────────────────

def sessions_to_js(sessions):
    lines = ["  const sessions = ["]
    for s in sessions:
        tokens = s["tokens"] if s["tokens"] is not None else "null"
        # JSON has \\n which becomes backslash-n string in Python (not actual newline)
        # When written to JS, we need it as \\n so it renders as newline in browser
        # The label already has \n (backslash-n), we just need to escape the backslash once more
        # Actually: label is 'Mar 27\nTM' with backslash-n, write it directly and Python will preserve it
        label = s["label"]  # Keep as-is; Python repr() will add escaping
        # Build the line carefully to avoid Python interpreting escape sequences
        line = f'    {{label:\'{repr(label)[1:-1]}\',project:\'{s["project"]}\',mins:{s["mins"]},tokens:{tokens}}},'
        lines.append(line)
    lines[-1] = lines[-1].rstrip(",")
    lines.append("  ];")
    return "\n".join(lines)


def efficiency_to_js(efficiency):
    labels = [e["label"] for e in efficiency]
    po = [round(e["po_mins"] / 60, 2) for e in efficiency]
    equiv = [round(e["equiv_mins"] / 60, 2) for e in efficiency]
    return labels, po, equiv


# ── HTML patch helpers ────────────────────────────────────────────────────────

def patch_sessions_array(html, sessions):
    js = sessions_to_js(sessions)
    return re.sub(r"  const sessions = \[[\s\S]*?\];", js, html, count=1)


def patch_efficiency_chart(html, efficiency):
    labels, po, equiv = efficiency_to_js(efficiency)
    # labels array
    html = re.sub(
        r"(efficiencyChart[\s\S]{0,200}?labels:\s*)\[[\s\S]*?\]",
        lambda m: m.group(1) + json.dumps(labels),
        html, count=1
    )
    # PO data — first data array after efficiencyChart label section
    html = re.sub(
        r"(label:'PO Time[^']*'[\s\S]{0,100}?data:\s*)\[[\d.,\s]+\]",
        lambda m: m.group(1) + json.dumps(po),
        html, count=1
    )
    # Equiv data
    html = re.sub(
        r"(label:'3-Person[^']*'[\s\S]{0,100}?data:\s*)\[[\d.,\s]+\]",
        lambda m: m.group(1) + json.dumps(equiv),
        html, count=1
    )
    return html


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
    """Prepend a new date block at the top of What Shipped."""
    ri_html = "\n".join(
        f'          <div class="ri"><div class="rtag">{project}</div><div class="rdet">{item}</div></div>'
        for item in items
    )
    new_block = f"""        <div class="rb"><div class="rd">{date}</div>
{ri_html}
        </div>"""
    # Insert after the tog title line
    return re.sub(
        r'(<div class="ct tog">What Shipped[^<]*</div>\s*)',
        lambda m: m.group(1) + new_block + "\n        ",
        html, count=1
    )


def patch_meta_learnings(html, date, bullets):
    """Prepend a new Meta Learnings entry."""
    mbi_html = "\n".join(f'            <div class="mbi">{b}</div>' for b in bullets)
    new_entry = f"""          <div class="mb"><div class="mbd">{date}</div>
{mbi_html}
          </div>"""
    return re.sub(
        r'(<div class="ct tog">Meta Learnings[^<]*</div>\s*)',
        lambda m: m.group(1) + new_entry + "\n          ",
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


def sync_mobile(sessions_js):
    if not MOBILE_HTML.exists():
        return
    mob = MOBILE_HTML.read_text()
    mob = re.sub(r"  const sessions = \[[\s\S]*?\];", sessions_js, mob, count=1)
    MOBILE_HTML.write_text(mob)
    print("✓ mobile.html synced")


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

    # 1. Add session entry
    data["sessions"].append({
        "label": session_label,
        "project": args.project,
        "mins": args.mins,
        "tokens": args.tokens
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

    # Data arrays
    html = patch_sessions_array(html, data["sessions"])
    html = patch_efficiency_chart(html, data["efficiency"])

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

    sync_mobile(sessions_to_js(data["sessions"]))

    print(f"\n✅ Wrap complete. Run: cd ~/Daytona/command-centre && vercel --prod")
    print(f"   Then: vercel alias <url> claude-command-centre.vercel.app")


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
    if args.sync:
        html = patch_sessions_array(INDEX_HTML.read_text(), data["sessions"])
        INDEX_HTML.write_text(html)
        sync_mobile(sessions_to_js(data["sessions"]))
        print("✓ index.html synced")


def cmd_add_efficiency(args):
    data = load_data()
    data["efficiency"].append({
        "label": args.label,
        "po_mins": args.po_mins,
        "equiv_mins": args.equiv_mins
    })
    save_data(data)
    print(f"  Added efficiency: {args.label}")
    if args.sync:
        html = patch_efficiency_chart(INDEX_HTML.read_text(), data["efficiency"])
        INDEX_HTML.write_text(html)
        print("✓ index.html synced")


def cmd_add_shipped(args):
    data = load_data()
    data["what_shipped"].insert(0, {
        "date": args.date,
        "project": args.project,
        "items": args.items
    })
    save_data(data)
    print(f"  Added {len(args.items)} shipped items for {args.date}")
    if args.sync:
        html = patch_what_shipped(INDEX_HTML.read_text(), args.date, args.project, args.items)
        INDEX_HTML.write_text(html)
        print("✓ index.html synced")


def cmd_update_last_session(args):
    html = INDEX_HTML.read_text()
    po_hrs = round(args.po_mins / 60, 1) if args.po_mins else ""
    badge = args.badge or f'<span class="b bp">{args.project}</span><span class="b bsl">~{po_hrs} hrs PO</span>'
    html = patch_last_session(html, args.date, args.project, args.bullets, badge)
    INDEX_HTML.write_text(html)
    print("✓ Last Session panel updated")


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


def validate_js_syntax(sessions_js):
    """Validate JS array doesn't have unescaped newlines in string literals."""
    # Split by the array lines and check each object
    lines = sessions_js.split('\n')
    in_string = False
    for i, line in enumerate(lines[1:-1], start=2):  # Skip "const sessions = [" and "];"
        line = line.strip()
        if not line or line.startswith('//'):
            continue

        # Count quotes to detect unterminated strings
        # If line ends before closing }, we have an unclosed string
        if line.endswith(',') or line.endswith('};'):
            # Normal case — object completes on one line
            continue
        elif '{' in line and '}' not in line:
            # Object started, should end with } or },
            print(f"❌ Syntax error: object not closed on line {i}: {line[:60]}...")
            return False

    return True


def cmd_sync(args):
    data = load_data()
    html = INDEX_HTML.read_text()
    sessions_js = sessions_to_js(data["sessions"])

    # Validate JS syntax before patching
    if not validate_js_syntax(sessions_js):
        print("⚠️  JS validation failed — aborting sync")
        return

    html = patch_sessions_array(html, data["sessions"])
    html = patch_efficiency_chart(html, data["efficiency"])
    INDEX_HTML.write_text(html)
    print(f"✓ index.html synced ({len(html):,} bytes)")
    sync_mobile(sessions_js)


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
    ps.add_argument("--sync", action="store_true")

    # add-efficiency
    pe = sub.add_parser("add-efficiency")
    pe.add_argument("--label", required=True)
    pe.add_argument("--po-mins", type=int, required=True)
    pe.add_argument("--equiv-mins", type=int, required=True)
    pe.add_argument("--sync", action="store_true")

    # add-shipped
    psh = sub.add_parser("add-shipped")
    psh.add_argument("--date", required=True)
    psh.add_argument("--project", required=True)
    psh.add_argument("--items", nargs="+", required=True)
    psh.add_argument("--sync", action="store_true")

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

    # sync
    sub.add_parser("sync")

    args = p.parse_args()
    dispatch = {
        "wrap": cmd_wrap,
        "add-session": cmd_add_session,
        "add-efficiency": cmd_add_efficiency,
        "add-shipped": cmd_add_shipped,
        "update-last-session": cmd_update_last_session,
        "add-meta-learning": cmd_add_meta_learning,
        "bump-version": cmd_bump_version,
        "sync": cmd_sync,
    }
    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
