#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS — Output Secrets Scanner
# PostToolUse Hook: Scan tool output for API keys, tokens, credentials.
# ─────────────────────────────────────────────────────────────────────────────
# Scans tool output for leaked secrets:
#   - API keys (AWS, GCP, OpenAI, Anthropic, GitHub, Stripe, etc.)
#   - Bearer tokens, JWTs
#   - Private keys (RSA, ECDSA, SSH)
#   - Database connection strings with passwords
#   - .env files being read (warn about secrets inside)
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEUTRON_ROOT="${NEUTRON_ROOT:-$HOME/.neutron-evo-os}"
SCAN_LOG="$NEUTRON_ROOT/memory/.secrets_audit.json"

# ── Patterns for secrets ─────────────────────────────────────────────────
_secrets=(
    # AWS
    "AKIA[0-9A-Z]{16}"
    "aws_access_key_id|aws_secret_access_key"
    # GCP
    "\"type\":\s*\"service_account\""
    # OpenAI / Anthropic
    "sk-[0-9a-zA-Z]{32,}"
    "sk-ant-[0-9a-zA-Z]{32,}"
    # GitHub
    "ghp_[0-9a-zA-Z]{36}"
    "gho_[0-9a-zA-Z]{36}"
    "github_pat_[0-9a-zA-Z_]{22,}"
    # Stripe
    "sk_live_[0-9a-zA-Z]{24}"
    "sk_test_[0-9a-zA-Z]{24}"
    # Database
    "postgres://[a-zA-Z0-9_-]+:[^@]+@"
    "mysql://[a-zA-Z0-9_-]+:[^@]+@"
    "mongodb://[a-zA-Z0-9_-]+:[^@]+@"
    "redis://[a-zA-Z0-9_-]+:[^@]+@"
    # SSH / Private Keys
    "-----BEGIN (RSA |EC |DSA |OPENSSH )PRIVATE KEY-----"
    "ssh-rsa AAAA[0-9a-zA-Z+/]"
    # JWT
    "eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*"
    # Bearer tokens
    "Bearer\s+[a-zA-Z0-9_-]{20,}"
    # Generic high-entropy secrets
    "api[_-]?key['\":\s=]+[a-zA-Z0-9]{20,}"
    "secret['\":\s=]+['\"][^'\"]{8,}['\"]"
    "password['\":\s=]+['\"][^'\"]{8,}['\"]"
    "token['\":\s=]+['\"][^'\"]{12,}['\"]"
)

# ── Tool + output input ────────────────────────────────────────────────────
_tool="$1"
_output="$2"

_scan_result="clean"
_matched=()

for _pattern in "${_secrets[@]}"; do
    _match="$(echo "$_output" | grep -oE "$_pattern" | head -3)"
    if [ -n "$_match" ]; then
        _scan_result="suspicious"
        _matched+=("pattern=$_pattern found=$(echo "$_match" | head -1 | cut -c1-40)")
    fi
done

# ── .env file read warning ────────────────────────────────────────────────
if echo "$_output" | grep -qE "CAT|grep.*\.env" && [ "$_scan_result" = "clean" ]; then
    echo "🔒 NEUTRON NOTICE: Reading .env file — ensure you are grepping for variable names, not values."
    echo "   If you see actual secret values in output, treat them as leaked."
fi

# ── If suspicious, log and warn ──────────────────────────────────────────
if [ "$_scan_result" = "suspicious" ]; then
    echo ""
    echo "🔒 NEUTRON SECURITY SCAN — Secret detected in output"
    echo "   Tool: $_tool"
    echo "   Patterns matched:"
    for _m in "${_matched[@]}"; do
        echo "   • $_m"
    done
    echo ""
    echo "   ⚠️  ACTION REQUIRED:"
    echo "   1. Rotate the leaked credential IMMEDIATELY"
    echo "   2. Run: neutron secrets audit"
    echo "   3. Check git history: git log --grep='leak' --oneline"
    echo ""

    # Log to audit file
    if [ -d "$NEUTRON_ROOT/memory" ]; then
        _ts="$(date +%Y-%m-%dT%H:%M:%S)"
        echo "{\"timestamp\":\"$_ts\",\"tool\":\"$_tool\",\"patterns\":$(printf '%s\n' "${_matched[@]}" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip().splitlines()))')}" >> "$SCAN_LOG"
    fi
fi

exit 0
