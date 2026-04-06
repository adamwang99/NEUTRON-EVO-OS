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
    echo "NEUTRON BLOCKED: $1"
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

# ── IMMEDIATE BLOCK: catastrophic commands ───────────────────────────────
# These are blocked regardless of path (too dangerous to allow).

# Parse the command into whitespace-separated words.
# Word-based detection avoids whitespace bypass: "rm -rf./path" has no space
# between -rf and ./path, but the first two words are "rm" and "-rf./path".
_word1=""
_word2=""
_word3=""
_set -- $_cmd
if [ "$#" -ge 1 ]; then _word1="$1"; fi
if [ "$#" -ge 2 ]; then _word2="$2"; fi
if [ "$#" -ge 3 ]; then _word3="$3"; fi

# Pattern 1: "rm" with dangerous flags (word1=rm, word2 contains -r and -f)
if [ "$_word1" = "rm" ]; then
    # -rf, -r, -f, -fr, -rf./, -r ./, etc.
    case "$_word2" in
        *r*|*f*|*R*|*F*)
            # Additional check: does it contain 'r' AND 'f'? (recursive + force)
            _has_r=$(echo "$_word2" | grep -c 'r\|R' || true)
            _has_f=$(echo "$_word2" | grep -c 'f\|F' || true)
            if [ "$_has_r" -gt 0 ] && [ "$_has_f" -gt 0 ]; then
                _immediately_block "rm recursive+force: catastrophic data loss risk"
            fi
            ;;
    esac
    # Also catch: "sudo rm -rf /" (word2=-rf, word3=/)
    if [ "$_word2" = "-rf" ] && [ "$_word3" = "/" ]; then
        _immediately_block "rm -rf / — catastrophic data loss"
    fi
fi

# Pattern 2: "sudo rm -rf /" (word1=sudo, word2=rm, word3 contains -rf, word4=/)
if [ "$_word1" = "sudo" ] && [ "$_word2" = "rm" ]; then
    case "$_word3" in
        *r*|*f*|*R*|*F*)
            _has_r=$(echo "$_word3" | grep -c 'r\|R' || true)
            _has_f=$(echo "$_word3" | grep -c 'f\|F' || true)
            if [ "$_has_r" -gt 0 ] && [ "$_has_f" -gt 0 ]; then
                _immediately_block "sudo rm recursive+force — catastrophic data loss"
            fi
            ;;
    esac
fi

# dd to raw disk — blocked regardless of options
if echo " $_cmd " | grep -qE '\s+dd\s+' && echo " $_cmd " | grep -qE '\s+of=/dev/'; then
    _immediately_block "dd writing to raw block device — catastrophic"
fi

# fdisk / mkfs on system disks
for _w in $_cmd; do
    case "$_w" in
        /dev/sd*|/dev/nvme*)
            echo " $_cmd " | grep -qE '\s+(fdisk|mkfs|mke2fs)\s+' && \
                _immediately_block "Disk partitioning/formatting on system disk $_w"
            ;;
    esac
done

# Overwriting /usr, /bin, /etc — word-based check (each word checked individually)
for _w in $_cmd; do
    case "$_w" in
        /usr//*|/bin//*|/etc//*)
            echo " $_cmd " | grep -qE '\s+(cp|mv)\s+' && \
                _immediately_block "Direct write to system directory: $_w"
            ;;
    esac
done

# Piping to shell (echo X | bash, curl | bash)
if echo " $_cmd " | grep -qE '\|\s*(bash|sh|zsh|fish)\s' || \
   echo " $_cmd " | grep -qE '^\s*curl.*\|\s*(bash|sh|zsh)'; then
    _immediately_block "Pipe to shell — potential command injection risk"
fi

# ── CONDITIONAL BLOCK: dangerous but maybe intentional ───────────────────

# rm -rf on project directories (may be intentional cleanup — warn heavily)
# Check word pairs: "rm" then something starting with $SAFE_ROOTS
_rm_words=""
for _w in $_cmd; do
    case "$_w" in
        rm) _rm_words="${_rm_words}rm " ;;
        -r*|-f*) _rm_words="${_rm_words}${_w} " ;;
    esac
done
_has_rf=$(echo "$_rm_words" | grep -c 'r\|R' || true)
_has_f=$(echo "$_rm_words" | grep -c 'f\|F' || true)
if [ "$_has_rf" -gt 0 ] && [ "$_has_f" -gt 0 ]; then
    for _root in $SAFE_ROOTS; do
        case " $_cmd " in
            *" $_root "*|*" $_root/"*)
                _immediately_block "rm -rf on NEUTRON project root — data loss risk. Use 'neutron gc' instead."
                ;;
        esac
    done
fi

# git push --force (warn about --force-with-lease)
if echo " $_cmd " | grep -qE '\sgit\s+push\s' && \
   ! echo " $_cmd " | grep -qE '\s--force-with-lease\b'; then
    _immediately_block "git push --force — use --force-with-lease to preserve remote history"
fi

# SSH direct to unknown hosts (IP addresses or suspicious hostnames)
if echo " $_cmd " | grep -qE '\s(ssh|scp|rsync)\s' && echo " $_cmd " | grep -qE '@'; then
    _ssh_host="$(echo "$_cmd" | grep -oE '@[a-zA-Z0-9._:-]+' | head -1 | tr -d '@')"
    case "$_ssh_host" in
        ""|localhost|127.0.0.1|localhost.localdomain) ;;
        *)
            _known_hosts_file="$HOME/.ssh/known_hosts"
            if [ -f "$_known_hosts_file" ] && ! grep -q "$_ssh_host" "$_known_hosts_file" 2>/dev/null; then
                echo "WARNING: SSH to unknown host: $_ssh_host"
                echo "   Press Enter to allow once, or Ctrl+C to block."
                read -r _confirm < /dev/tty || true
            fi
            ;;
    esac
fi

# Install from untrusted pip/npm sources
if echo " $_cmd " | grep -qE '\spip\s+install\s' && \
   echo " $_cmd " | grep -qE '\s--(index-url|extra-index-url)\s'; then
    _idx_url="$(echo "$_cmd" | grep -oE '--(index-url|extra-index-url)=[^[:space:]]+' | head -1 | cut -d= -f2)"
    : "${_idx_url:=""}"
    case "$_idx_url" in
        *pypi.org*|*python.org*) ;;
        *) _immediately_block "pip install from untrusted index: $_idx_url — may contain malware"
           ;;
    esac
fi

# npm/yarn install from untrusted URLs
if echo " $_cmd " | grep -qE '\s(npm|yarn)\s+(install|add)\s' && \
   echo " $_cmd " | grep -qE '\shttps?://'; then
    echo "WARNING: Installing package from URL — may be untrusted"
    echo "   Press Enter to allow once, or Ctrl+C to block."
    read -r _confirm < /dev/tty || true
fi

# find with -delete on large scopes
if echo " $_cmd " | grep -qE '\sfind\s+[/~]\s' && \
   echo " $_cmd " | grep -qE '\s-delete\b' && \
   ! echo " $_cmd " | grep -qE "\s${NEUTRON_ROOT}"; then
    _immediately_block "find / or ~/ with -delete — too broad. Use 'neutron gc' for cleanup."
fi

exit 0
