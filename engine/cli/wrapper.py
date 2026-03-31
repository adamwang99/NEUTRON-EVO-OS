#!/usr/bin/env python3
"""
NEUTRON CLI — Wrapper
Finds NEUTRON_ROOT by looking up from this file's location.
Does NOT hardcode any path.
"""
import os
import sys
from pathlib import Path

# This file: engine/cli/wrapper.py
# NEUTRON_ROOT: grandparent of engine/cli/
_NEUTRON_ROOT = Path(__file__).resolve().parent.parent.parent
os.environ["NEUTRON_ROOT"] = str(_NEUTRON_ROOT)

if str(_NEUTRON_ROOT) not in sys.path:
    sys.path.insert(0, str(_NEUTRON_ROOT))

from engine.cli.main import main
if __name__ == "__main__":
    main()
