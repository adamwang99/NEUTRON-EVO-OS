#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS — Prompt Injection Detector
# PreToolUse Hook: Detect prompt injection in user input.
# ─────────────────────────────────────────────────────────────────────────────
# Attack patterns:
#   - Direct override: "ignore all previous instructions"
#   - Role playing jailbreak: "you are now DAN/GPT4"
#   - Context injection: "system: ..." in user input
#   - Unicode homograph attack (Cyrillic 'а' vs Latin 'a')
#   - Markdown/image trick: embedded instructions in data URLs
#   - Delayed injection: base64 encoded commands
# ─────────────────────────────────────────────────────────────────────────────

_injection_detected=0
_block_reason=""

# ── Direct override patterns ─────────────────────────────────────────────
_override_patterns=(
    "ignore (all )?previous (instructions|commands|context)"
    "disregard (all )?prior (instructions|commands)"
    "forget (all )?previous"
    "new (system )?instructions"
    "overwrite (your |this )?(system |model )?(prompt|instruct)"
    "you (are|were|can act as) (now |a )?(different |another )?(AI |model |bot |DAN)"
    "jailbreak"
    "pretend (you |to be) (without |not bound by)"
    "your actual (behavior |nature |restrictions)"
    "bypass (your |the )?(safety|content|restriction)"
    "do((es)?n'?t?)? (adhere|follow|stick|stick to) (to )?(your |the )?(system |the )?(prompt|instruction|guideline|restriction)"
    "\\[SYSTEM\\]|{SYSTEM}|<SYSTEM>|system:\\s*"
)

for _pat in "${_override_patterns[@]}"; do
    if echo "$1" | grep -Ei "$_pat" > /dev/null 2>&1; then
        _injection_detected=1
        _block_reason="Direct override/injection pattern: $_pat"
        break
    fi
done

# ── Unicode homograph attack detection ──────────────────────────────────
# Common Cyrillic look-alikes that can confuse parsers
_cirillic_chars="$(echo "$1" | grep -o '[[:punct:][:alpha:][:digit:]]' | grep -P '[^\x00-\x7F]' | head -20)"
if [ -n "$_cirillic_chars" ]; then
    # Check for Cyrillic look-alikes of key ASCII chars
    _suspicious="$(echo "$_cirillic_chars" | grep -P '[\x{0430}\x{0435}\x{043E}\x{0440}\x{0441}\x{0443}\x{0432}\x{0445}]' | wc -l)"
    if [ "$_suspicious" -gt 3 ]; then
        _injection_detected=1
        _block_reason="Unicode homograph characters detected — possible injection"
    fi
fi

# ── Base64 encoded command detection ────────────────────────────────────
if echo "$1" | grep -qE "[A-Za-z0-9+/]{40,}={0,2}$"; then
    _possible_b64="$(echo "$1" | grep -oE '[A-Za-z0-9+/]{60,}={0,2}' | head -3)"
    for _b64 in $_possible_b64; do
        _decoded="$(echo "$_b64" | base64 -d 2>/dev/null)"
        if [ -n "$_decoded" ] && echo "$_decoded" | grep -qE "(bash|sh|curl|wget|python|eval|exec)"; then
            _injection_detected=1
            _block_reason="Base64 encoded shell command detected: $(echo "$_decoded" | head -c 60)"
            break
        fi
    done
fi

# ── Markdown image/data URL injection ───────────────────────────────────────
if echo "$1" | grep -qE "!\[.*\]\(data:text/html|" && echo "$1" | grep -qE "(system|ignore|prompt)"; then
    _injection_detected=1
    _block_reason="Markdown image injection — embedded instructions in data URL"
fi

# ── Context escape: newlines with system-level keywords ───────────────────
if echo "$1" | grep -qE "^system:|^{\"system\":|<\s*system\s*>" && echo "$1" | grep -qE "(ignore|forget|bypass|pretend)"; then
    _injection_detected=1
    _block_reason="Context escape via system: prefix + override keyword"
fi

# ── Block if detected ────────────────────────────────────────────────────
if [ "$_injection_detected" -eq 1 ]; then
    echo ""
    echo "⛔ NEUTRON INJECTION BLOCK — Prompt injection detected"
    echo "   Reason: $_block_reason"
    echo ""
    echo "   Your input contained a pattern that matches known injection attacks."
    echo "   If this is legitimate text (e.g., you are describing an attack),"
    echo "   rephrase without using 'ignore previous' or 'system:' keywords."
    echo ""
    echo "   To override this warning (use with caution):"
    echo "   neutron auto disable"
    exit 1
fi

exit 0
