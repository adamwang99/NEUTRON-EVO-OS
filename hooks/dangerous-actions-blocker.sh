#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS — Dangerous Actions Blocker
# PreToolUse Hook: Block destructive commands before execution.
# ─────────────────────────────────────────────────────────────────────────────
# Blocks:
#   - Recursive delete (rm -rf /, find ... -delete on root dirs)
#   - Force git push (--force-with-lease preferred over --force)
#   - Direct SSH/Rsync to unknown hosts
#   - Destructive disk commands (dd, fdisk, mkfs)
#   - Overwriting /etc, /usr, /bin
#   - Installing untrusted packages
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEUTRON_ROOT="${NEUTRON_ROOT:-$HOME/.neutron-evo-os}"

# ── Known safe paths (NEUTRON projects only) ───────────────────────────────
SAFE_ROOTS="${NEUTRON_ROOT} $HOME/projects $HOME/code /mnt/data/projects"

# ── Dangerous patterns — block regardless of path ────────────────────────────
_immediately_block() {
    echo "⛔ NEUTRON BLOCKED: $1"
    echo ""
    echo "If this is a false positive, use neutron protect to whitelist."
    echo "Or run: neutron auto disable (removes all NEUTRON guards temporarily)"
    exit 1
}

# ── Parse the tool being run ─────────────────────────────────────────────
_action="$1"        # Bash, Edit, Write, etc.
if [ "$#" -ge 2 ]; then
    shift; _cmd="$1"
    _flags="${2:-}"
else
    _cmd=""
    _flags=""
fi

if [ "$_action" != "Bash" ]; then
    exit 0  # Only block Bash commands
fi

# ── IMMEDIATE BLOCK: catastrophic commands ────────────────────────────────
# These are blocked regardless of path (too dangerous to allow)

# rm -rf / or rm -rf /* or rm -rf /
if echo "$_cmd" | grep -Eq "^[[:space:]]*(sudo[[:space:]]+)?rm[[:space:]]+(-[rf]+\s+)?(/|/[a-z]+)"; then
    _immediately_block "rm -rf on root directories — catastrophic data loss"
fi

# dd to raw disk
if echo "$_cmd" | grep -qE "dd\s+if=\s*[^|]+\s+of=\s*(/dev/[a-z][a-z0-9]*)"; then
    _immediately_block "dd writing to raw block device — catastrophic"
fi

# fdisk / mkfs on system disks
if echo "$_cmd" | grep -qE "(fdisk|mkfs|mke2fs)\s+/dev/(sd|nvme)"; then
    _immediately_block "Disk partitioning/formatting on system disk"
fi

# Overwriting /usr, /bin, /etc directly
if echo "$_cmd" | grep -qE "(cp|mv)\s+.*\s+(/usr/|/bin/|/etc/)\s"; then
    _immediately_block "Direct write to system directory /usr, /bin, or /etc"
fi

# Piping to shell (echo X | bash, curl | bash)
if echo "$_cmd" | grep -qE "\|\s*(bash|sh|zsh|fish)\s*(<&|>&)?\s*\$"; then
    _immediately_block "Pipe to shell — potential command injection risk"
fi

# ── CONDITIONAL BLOCK: dangerous but maybe intentional ───────────────────

# rm -rf on project directories (may be intentional cleanup — warn heavily)
if echo "$_cmd" | grep -qE "rm[[:space:]]+-[rf]+\s"; then
    _warned_path=""
    for _root in $SAFE_ROOTS; do
        if echo "$_cmd" | grep -qE "rm\s+-[rf]+\s+${_root}"; then
            _immediately_block "rm -rf on NEUTRON project root — data loss risk. Use 'neutron gc' instead."
        fi
    done
    # rm -rf without a clear path — block
    if echo "$_cmd" | grep -qE "rm\s+-[rf]+\s+\$[a-zA-Z_]"; then
        _immediately_block "rm -rf with variable — may expand to root path. Use absolute path."
    fi
fi

# git push --force (warn about --force-with-lease)
# Note: grep -E does NOT support negative lookahead (?!). Use separate patterns.
if echo "$_cmd" | grep -qE "git\s+push\s+.*\s--force\b" && \
   ! echo "$_cmd" | grep -qE "git\s+push\s+.*\s--force-with-lease"; then
    _immediately_block "git push --force — use --force-with-lease to preserve remote history. Blocked by NEUTRON safety rules."
fi

# SSH direct to unknown hosts (IP addresses or suspicious hostnames)
# Extract host after @, then check against known_hosts
if echo "$_cmd" | grep -qE "(ssh|scp|rsync)\s+.*@"; then
    _ssh_host="$(echo "$_cmd" | grep -oE '@[a-zA-Z0-9._:-]+' | head -1 | tr -d '@')"
    # Allow localhost variants, block unknown hosts
    case "$_ssh_host" in
        ""|localhost|127.0.0.1|localhost.localdomain) ;;
        *)
            _known_hosts_file="$HOME/.ssh/known_hosts"
            if [ -f "$_known_hosts_file" ] && ! grep -q "$_ssh_host" "$_known_hosts_file" 2>/dev/null; then
                echo "⚠️  NEUTRON WARNING: SSH to unknown host: $_ssh_host"
                echo "   Known hosts: $(grep -c . "$_known_hosts_file" 2>/dev/null || echo 0) entries"
                echo "   Press Enter to allow once, or Ctrl+C to block."
                read -r _confirm < /dev/tty
            fi
            ;;
    esac
fi

# Install from untrusted pip/npm sources
if echo "$_cmd" | grep -qE "pip\s+install\s+(--index-url|--extra-index-url)"; then
    _idx_url="$(echo "$_cmd" | grep -oE '--(index-url|extra-index-url)\s+[^[:space:]]+' | awk '{print $2}')"
    case "$_idx_url" in
        *pypi.org*|*python.org*) ;;
        *) _immediately_block "pip install from untrusted index: $_idx_url — may contain malware. Use pypi.org or your company's private index."
            ;;
    esac
fi

# npm/yarn install from untrusted URLs
if echo "$_cmd" | grep -qE "(npm|yarn)\s+(install|add)\s+https?://"; then
    _npm_url="$(echo "$_cmd" | grep -oE 'https?://[^[:space:]]+' | head -1)"
    echo "⚠️  NEUTRON WARNING: Installing package from URL: $_npm_url"
    echo "   Prefer npm install from package.json or a trusted registry."
    echo "   Press Enter to allow once, or Ctrl+C to block."
    read -r _confirm < /dev/tty
fi

# find with -delete on large scopes
if echo "$_cmd" | grep -qE "find\s+[/~]\s+.*-delete" && ! echo "$_cmd" | grep -qE "find\s+${NEUTRON_ROOT}"; then
    _immediately_block "find / or ~/ with -delete — too broad. Use 'neutron gc' for cleanup."
fi

exit 0
