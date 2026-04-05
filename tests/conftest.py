"""
conftest.py — Pytest configuration for NEUTRON EVO OS tests.
Sets up environment to prevent test pollution of system directories.
"""
import os
import sys

# CRITICAL: Set test mode BEFORE any NEUTRON modules are imported.
# This prevents dream_cycle() from writing to the real memory/archived/ directory
# when tests call dream_cycle() with real global paths.
os.environ["NEUTRON_DREAM_TEST"] = "1"

# Ensure project root in path
sys.path.insert(0, str(__file__.rsplit("/tests", 1)[0]))
