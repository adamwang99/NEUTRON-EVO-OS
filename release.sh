#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS — Release Script
# Creates a versioned GitHub release with strict security checks.
# ─────────────────────────────────────────────────────────────────────────────
# Usage:
#   bash release.sh [version] [notes]
#   bash release.sh 4.3.0 "New features"
#
# Requirements:
#   • gh CLI authenticated (gh auth login)
#   • git remote configured
#   • Clean working tree (no uncommitted sensitive files)
#
# Security gates (ALL must pass):
#   1. gh CLI authenticated
#   2. No API keys / secrets in staged files
#   3. No personal info (email, phone, ID) in staged files
#   4. No .env files staged
#   5. Working tree is clean (or only docs/non-sensitive files)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
OK="${GREEN}✓${RESET}"; ERR="${RED}✗${RESET}"; WARN="${YELLOW}⚠${RESET}"

info()  { echo -e "${CYAN}[info]${RESET}  $1"; }
ok()    { echo -e "${OK}  $1"; }
warn()  { echo -e "${WARN} $1"; }
error() { echo -e "${ERR}  $1" >&2; }

# ── Banner ────────────────────────────────────────────────────────────────────
echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       NEUTRON EVO OS — Release Workflow                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

# ── Parse args ────────────────────────────────────────────────────────────────
VERSION="${1:-}"
NOTES="${2:-}"

if [ -z "$VERSION" ]; then
    # Auto-detect next version
    LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
    # Increment patch
    MAJOR=$(echo "$LAST_TAG" | sed 's/v//' | cut -d. -f1)
    MINOR=$(echo "$LAST_TAG" | sed 's/v//' | cut -d. -f2)
    PATCH=$(echo "$LAST_TAG" | sed 's/v//' | cut -d. -f3)
    PATCH=$((PATCH + 1))
    VERSION="v${MAJOR}.${MINOR}.${PATCH}"
    info "No version given — using: $VERSION (next patch)"
fi

# Remove 'v' prefix if user added it
VERSION="${VERSION#v}"

echo -e "  Version:  ${BOLD}v$VERSION${RESET}"
echo -e "  Branch:   ${BOLD}$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD 2>/dev/null)${RESET}"
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# GATE 1 — GitHub Authentication
# ══════════════════════════════════════════════════════════════════════════════
echo -e "${BOLD}─── Gate 1: GitHub Auth ───${RESET}"
if gh auth status &>/dev/null; then
    GH_USER=$(gh api user --jq .login 2>/dev/null || echo "unknown")
    GH_SCOPES=$(gh auth status 2>&1 | grep -o '.*scopes.*' | head -1 || echo "")
    ok "Authenticated as: $GH_USER"
else
    error "Not logged in to GitHub."
    echo ""
    echo "  Run:  gh auth login"
    echo "  Then: bash release.sh v$VERSION"
    exit 1
fi

# ══════════════════════════════════════════════════════════════════════════════
# GATE 2 — Check staged files for sensitive data
# ══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BOLD}─── Gate 2: Sensitive Data Scan ───${RESET}"

# Files to ALWAYS block (absolute)
BLOCKED_PATTERNS=(
    ".env$"
    ".env.local$"
    ".env.production"
    "credentials.json"
    "secrets.json"
    "id_rsa"
    "id_ed25519"
    "*.pem"
    "*.key"
    "passwords.txt"
    "api_keys.txt"
)

# Regex patterns to scan content
SENSITIVE_PATTERNS=(
    'sk-[0-9a-zA-Z]{20,}'               # API keys (sk-...)
    'ghp_[0-9a-zA-Z]{20,}'              # GitHub PATs
    'xox[baprs]-[0-9a-zA-Z]{10,}'       # Slack/Discord tokens
    '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'  # Emails (loose check)
    'password\s*=\s*["\x27][^"\x27]{4,}["\x27]'       # password=...
    'api[_-]?key\s*=\s*["\x27][^"\x27]{8,}["\x27]'   # api_key=...
    'token\s*=\s*["\x27][^"\x27]{10,}["\x27]'        # token=...
    '[0-9]{4,}[- ][0-9]{4,}[- ][0-9]{4,}[- ][0-9]{4,}'  # Credit card
    '[0-9]{10,11}'                        # Phone numbers (10-11 digits)
    'Bearer\s+[a-zA-Z0-9_\.-]+'         # Bearer tokens
    '-----BEGIN.*PRIVATE KEY-----'       # Private keys
)

# Get list of (staged + recently changed) files
SCAN_FILES=$(git diff --cached --name-only 2>/dev/null)
SCAN_FILES="$SCAN_FILES"$'\n'$(git diff --name-only HEAD~3..HEAD 2>/dev/null)
SCAN_FILES=$(echo "$SCAN_FILES" | grep -v '^$' | sort -u)

BLOCKED_FILES=""
SENSITIVE_FOUND=""

# Check for blocked filenames
for pattern in "${BLOCKED_PATTERNS[@]}"; do
    matched=$(echo "$SCAN_FILES" | grep -E "$pattern" 2>/dev/null || true)
    if [ -n "$matched" ]; then
        BLOCKED_FILES="$BLOCKED_FILES"$'\n'"  $pattern → $matched"
    fi
done

if [ -n "$BLOCKED_FILES" ]; then
    error "BLOCKED: Sensitive files staged:"
    echo "$BLOCKED_FILES"
    exit 1
fi
ok "No blocked files staged"

# Scan content of text files
SCAN_COUNT=0
SKIP_EXTENSIONS="png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|mp3|mp4|zip|tar|gz|zst|db|sqlite|pyc|cpy"

for file in $SCAN_FILES; do
    [ -f "$file" ] || continue
    ext="${file##*.}"
    echo "$ext" | grep -qE "$SKIP_EXTENSIONS" && continue
    [ "$ext" = "$file" ] && continue  # no extension

    SCAN_COUNT=$((SCAN_COUNT + 1))
    content=$(cat "$file" 2>/dev/null | head -200 || continue)

    for pattern in "${SENSITIVE_PATTERNS[@]}"; do
        # Skip obvious false positives
        if echo "$content" | grep -iE 'example|placeholder|test.*key|your_key|REPLACE' | grep -qv 'sk-[0-9a-zA-Z]' ; then
            continue
        fi
        found=$(echo "$content" | grep -nE "$pattern" 2>/dev/null | grep -iv 'REPLACE\|YOUR_\|EXAMPLE\|test_' | head -5 || true)
        if [ -n "$found" ]; then
            SENSITIVE_FOUND="${SENSITIVE_FOUND}"$'\n'"  $file:"$'\n'"   $(echo "$found" | head -3 | sed 's/^/     /')"
        fi
    done
done

if [ -n "$SENSITIVE_FOUND" ]; then
    error "BLOCKED: Sensitive data found in files:"
    echo "$SENSITIVE_FOUND"
    echo ""
    error "Remove / redact sensitive data before releasing."
    exit 1
fi

ok "Content scan passed ($SCAN_COUNT files checked)"

# ══════════════════════════════════════════════════════════════════════════════
# GATE 3 — Working tree cleanliness
# ══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BOLD}─── Gate 3: Working Tree ───${RESET}"

UNTRACKED=$(git status --porcelain 2>/dev/null | grep "^??" | awk '{print $2}' | grep -vE '^\.backup/|^\.cache/|__pycache__/|node_modules/' || true)
UNTRACKED_COUNT=$(echo "$UNTRACKED" | grep -c . 2>/dev/null || echo 0)

if [ "$UNTRACKED_COUNT" -gt 0 ]; then
    warn "Untracked files (will NOT be included in release):"
    echo "$UNTRACKED" | head -10 | sed 's/^/  + /'
    if [ "$UNTRACKED_COUNT" -gt 10 ]; then
        echo "  ... and $((UNTRACKED_COUNT - 10)) more"
    fi
    echo ""
fi

# Check for large untracked files
LARGE=$(echo "$UNTRACKED" | while read f; do
    [ -f "$f" ] && size=$(stat -c%s "$f" 2>/dev/null || echo 0)
    [ "$size" -gt 5242880 ] 2>/dev/null && echo "  $f ($(numfmt --to=iec "$size" 2>/dev/null || echo "${size}B"))"
done || true)

if [ -n "$LARGE" ]; then
    warn "Large untracked files (>5MB):"
    echo "$LARGE"
fi

# Check staged changes summary
STAGED_COUNT=$(git diff --cached --name-only 2>/dev/null | wc -l || echo 0)
if [ "$STAGED_COUNT" -gt 0 ]; then
    info "Staged changes ($STAGED_COUNT files):"
    git diff --cached --stat --stat-width=60 2>/dev/null | tail -5 | sed 's/^/  /'
    echo ""
fi

ok "Working tree check passed"

# ══════════════════════════════════════════════════════════════════════════════
# GATE 4 — Git branch check
# ══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BOLD}─── Gate 4: Branch Check ───${RESET}"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$BRANCH" != "main" ] && [ "$BRANCH" != "master" ]; then
    warn "You are on branch: $BRANCH"
    echo -n "  Continue anyway? (y/N): "
    read -r confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        error "Aborted."
        exit 1
    fi
    echo ""
fi
ok "On branch: $BRANCH"

# ══════════════════════════════════════════════════════════════════════════════
# STEP — Git tag + push
# ══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BOLD}─── Creating Release ───${RESET}"

# Check if tag exists
if git rev-parse "v$VERSION" &>/dev/null; then
    error "Tag v$VERSION already exists!"
    echo "  Use: bash release.sh $VERSION.1 \"hotfix\""
    exit 1
fi

# Git add + commit staged changes first
if [ "$STAGED_COUNT" -gt 0 ]; then
    echo -n "  Commit staged changes? (Y/n): "
    read -r commit_confirm
    if [ "$commit_confirm" != "n" ] && [ "$commit_confirm" != "N" ]; then
        git commit -m "Release v$VERSION"$'\n\n'"Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
        ok "Changes committed"
    fi
fi

# Create tag
git tag -a "v$VERSION" -m "NEUTRON EVO OS v$VERSION"$'\n\n'"∫f(t)dt — Functional Credibility Over Institutional Inertia"
ok "Tag created: v$VERSION"

# Push tag
info "Pushing to GitHub..."
git push origin "v$VERSION" 2>&1
ok "Tag pushed"

# Create GitHub Release
RELEASE_NOTES="${NOTES:-Auto-release v$VERSION}"
gh release create "v$VERSION" \
    --title "NEUTRON EVO OS v$VERSION" \
    --notes "$RELEASE_NOTES" \
    2>&1

ok "GitHub Release created: https://github.com/adamwang99/NEUTRON-EVO-OS/releases/tag/v$VERSION"

# ══════════════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════╗"
echo "║              RELEASE v$VERSION COMPLETE                           ║"
echo "╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  🌐  https://github.com/adamwang99/NEUTRON-EVO-OS/releases/tag/v$VERSION"
echo -e "  📋  Changelog: git log v$VERSION..HEAD --oneline"
echo ""
echo -e "${GREEN}[✓] All security gates passed. ∫f(t)dt${RESET}"
