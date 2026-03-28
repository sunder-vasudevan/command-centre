#!/usr/bin/env python3
"""
Wrap Verification Script
Validates that wrap_update.py automation was actually executed.
Blocks /wrap or /compact if:
  1. Command-centre index.html timestamp is stale (doesn't match today)
  2. Last Session card is outdated
  3. wrap_update.py was never called this session

Usage:
  python3 wrap-verify.py --check    # Verify wrap was done correctly
  python3 wrap-verify.py --reset    # Clear verified state (for testing)
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

WRAP_STATE_FILE = Path("/Users/sunnyhayes/.claude/wrap_state.json")
COMMAND_CENTRE_DIR = Path("/Users/sunnyhayes/Daytona/command-centre")
INDEX_HTML = COMMAND_CENTRE_DIR / "index.html"

def get_today_date():
    """Return today's date as YYYY-MM-DD"""
    return datetime.now().strftime("%Y-%m-%d")

def read_index_timestamp():
    """Extract timestamp from index.html header"""
    if not INDEX_HTML.exists():
        return None

    try:
        with open(INDEX_HTML, "r") as f:
            content = f.read()
            # Look for: <div class="ver-badge">2026-03-28 18:46</div>
            import re
            match = re.search(r'<div class="ver-badge">(\d{4}-\d{2}-\d{2})', content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"[WARN] Could not read index.html: {e}", file=sys.stderr)
    return None

def read_last_session_card():
    """Extract Last Session card data from index.html"""
    if not INDEX_HTML.exists():
        return None

    try:
        with open(INDEX_HTML, "r") as f:
            content = f.read()
            import re
            # Look for: <div class="ct">Last Session — 2026-03-28</div>
            match = re.search(r'<div class="ct">Last Session — (\d{4}-\d{2}-\d{2})', content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"[WARN] Could not read Last Session card: {e}", file=sys.stderr)
    return None

def load_wrap_state():
    """Load wrap execution state from disk"""
    if WRAP_STATE_FILE.exists():
        try:
            with open(WRAP_STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_wrap_state(state):
    """Save wrap execution state to disk"""
    WRAP_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WRAP_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def mark_wrap_done():
    """Record that wrap_update.py was executed"""
    state = load_wrap_state()
    state["last_wrap_date"] = get_today_date()
    state["last_wrap_time"] = datetime.now().isoformat()
    state["index_timestamp"] = read_index_timestamp()
    state["last_session_date"] = read_last_session_card()
    save_wrap_state(state)
    print(f"✅ Wrap marked as complete for {get_today_date()}")

def verify_wrap():
    """Check if wrap was done today and command-centre is current"""
    today = get_today_date()
    state = load_wrap_state()

    index_ts = read_index_timestamp()
    last_session = read_last_session_card()

    errors = []

    # Check 1: Has wrap been marked as done today?
    if state.get("last_wrap_date") != today:
        errors.append(f"wrap_update.py has not been executed today ({today})")

    # Check 2: Is index.html timestamp current?
    if index_ts != today:
        errors.append(f"Command-Centre timestamp is stale ({index_ts}, should be {today})")

    # Check 3: Is Last Session card current?
    if last_session != today:
        errors.append(f"Last Session card date is outdated ({last_session}, should be {today})")

    if errors:
        print("\n⛔  WRAP VERIFICATION FAILED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print("\nRun wrap_update.py before /wrap or /compact:", file=sys.stderr)
        print("  python3 wrap_update.py wrap --project 'X' --mins M --po-mins P --equiv-mins E --shipped 'bullets'", file=sys.stderr)
        print("  python3 wrap_update.py update-last-session --date '$(date +%Y-%m-%d)' --project 'X' --bullets 'B1' 'B2' 'B3' --badge 'Label · time'", file=sys.stderr)
        print("  vercel --prod && vercel alias set <URL> claude-command-centre.vercel.app", file=sys.stderr)
        print("  python3 wrap-verify.py --mark-done", file=sys.stderr)
        return False

    print(f"✅ Wrap verified complete for {today}")
    print(f"   Command-Centre: {index_ts} (current)")
    print(f"   Last Session: {last_session} (current)")
    return True

def reset_state():
    """Reset wrap state (for testing / recovery)"""
    if WRAP_STATE_FILE.exists():
        WRAP_STATE_FILE.unlink()
    print("🔄 Wrap state cleared")

def main():
    parser = argparse.ArgumentParser(
        description="Verify wrap_update.py automation was executed"
    )
    parser.add_argument("--check", action="store_true", help="Verify wrap completeness")
    parser.add_argument("--mark-done", action="store_true", help="Mark wrap as executed")
    parser.add_argument("--reset", action="store_true", help="Clear verified state")

    args = parser.parse_args()

    if args.mark_done:
        mark_wrap_done()
        sys.exit(0)

    if args.reset:
        reset_state()
        sys.exit(0)

    if args.check:
        if not verify_wrap():
            sys.exit(1)
        sys.exit(0)

    # Default: verify
    if not verify_wrap():
        sys.exit(1)

if __name__ == "__main__":
    main()
