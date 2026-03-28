#!/bin/bash
# wrap-protocol.sh — Enforces session wrap protocol before allowing /wrap execution
# This script is called by the /wrap skill and validates:
#   1. session_wrap.md has been read (protocol verification)
#   2. wrap_update.py was actually executed (automation trust)
#   3. command-centre is current (timestamp + card check)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VERIFY_SCRIPT="$SCRIPT_DIR/wrap-verify.py"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🏁 Wrap Protocol Verification${NC}"
echo "================================================"

# Check 1: Verify wrap_update.py was executed
echo ""
echo "Step 1: Checking command-centre automation..."
if [ -x "$VERIFY_SCRIPT" ]; then
    if python3 "$VERIFY_SCRIPT" --check 2>/dev/null; then
        echo -e "${GREEN}✅ Wrap automation verified${NC}"
    else
        echo -e "${RED}❌ Wrap verification failed${NC}"
        echo ""
        echo "This means wrap_update.py was not executed or command-centre is stale."
        echo ""
        echo "Run these commands in order:"
        echo "  cd ~/Daytona/command-centre"
        echo ""
        echo "  1. Wrap everything:"
        echo "     python3 wrap_update.py wrap --project 'X' --mins M --po-mins P --equiv-mins E --shipped 'bullets'"
        echo ""
        echo "  2. Update Last Session card:"
        echo "     python3 wrap_update.py update-last-session --date \"\$(date +%Y-%m-%d)\" --project 'X' --bullets 'B1' 'B2' --badge 'Label · time'"
        echo ""
        echo "  3. Deploy:"
        echo "     vercel --prod && vercel alias set <URL> claude-command-centre.vercel.app"
        echo ""
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  wrap-verify.py not found, skipping automation check${NC}"
fi

echo ""
echo -e "${GREEN}✅ Wrap protocol complete${NC}"
echo "================================================"
echo ""
echo "Ready to execute remaining session wrap steps."
echo "Run: /wrap (to complete full session wrap)"
echo ""
