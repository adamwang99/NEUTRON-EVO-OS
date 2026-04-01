#!/usr/bin/env python3
"""NEUTRON EVO OS — First run setup script (called by session-start.sh)."""
import json
import os
import sys

root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NEUTRON_ROOT", ".")
memory_dir = os.path.join(root, "memory")
os.makedirs(memory_dir, exist_ok=True)

# Enable auto-confirm full
auto_file = os.path.join(memory_dir, ".auto_confirm.json")
config = {"enabled": True, "mode": "full", "notes": "auto-confirm enabled on first session"}
with open(auto_file, "w") as f:
    json.dump(config, f, indent=2)

# Create first-run marker
marker = os.path.join(memory_dir, ".first_session_done")
with open(marker, "w") as f:
    f.write("first_session_done\n")

print("AUTO-CONFIRM: enabled (first session — full mode)")
