#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS — Auto-Sync Hook
# Runs at every Claude Code session start.
# Reads NEUTRON_AUTO_CONFIRM from auto_confirm.json and syncs Claude settings.
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEUTRON_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AUTO_CONFIRM_FILE="$NEUTRON_ROOT/memory/.auto_confirm.json"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"

# Exit early if no auto_confirm.json
[ -f "$AUTO_CONFIRM_FILE" ] || exit 0

# Check if auto-confirm is enabled
ENABLED=$(python3 -c "import json,sys; d=json.load(open('$AUTO_CONFIRM_FILE')); print('1' if d.get('enabled') else '0')" 2>/dev/null)

if [ "$ENABLED" = "1" ]; then
    # Auto-confirm is ON — ensure Claude Code settings match
    python3 - "$CLAUDE_SETTINGS" "$AUTO_CONFIRM_FILE" << 'PYEOF'
import json, sys, os
settings_path, auto_confirm_path = sys.argv[1], sys.argv[2]

# Read auto-confirm state
with open(auto_confirm_path) as f:
    auto_cfg = json.load(f)
enabled = auto_cfg.get("enabled", False)

# Read settings once (avoid double-open TOCTOU race)
data = {}
if os.path.exists(settings_path):
    content = open(settings_path).read()
    if content.strip():
        try:
            data = json.loads(content)
        except Exception:
            pass

if enabled:
    data["permissionPromptsEnabled"] = False
    data["autoApprove"] = True
    data["skipDangerousModePermissionPrompt"] = True
    data.setdefault("allow", {})
    for k in ["edit","multiEdit","bash","browser","mcp","fetch","glob","grep","read","write"]:
        data["allow"][k] = True
    data.setdefault("permissions", {})
    data["permissions"]["defaultMode"] = "acceptEdits"
    data["permissions"]["allow"] = ["Bash","Read","Edit","Write","Glob","Grep","WebFetch","WebSearch","mcp__*"]
    data.setdefault("env", {})
    data["env"]["NEUTRON_AUTO_CONFIRM"] = "1"
else:
    data["permissionPromptsEnabled"] = True
    data["autoApprove"] = False
    data["skipDangerousModePermissionPrompt"] = False
    if "env" in data:
        data["env"]["NEUTRON_AUTO_CONFIRM"] = "0"

# Atomic write to settings
import tempfile
fd = tempfile.NamedTemporaryFile(mode="w", dir=os.path.dirname(settings_path) or ".", delete=False)
try:
    fd.write(json.dumps(data, indent=2))
    fd.flush()
    os.fsync(fd.fileno())
    fd.close()
    os.replace(fd.name, settings_path)
except Exception:
    try:
        os.unlink(fd.name)
    except Exception:
        pass
PYEOF
fi
