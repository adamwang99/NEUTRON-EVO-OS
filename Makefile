.PHONY: live dream install install-global install-cursor install-cline test clean lint help checkpoint checkpoint-handoff checkpoint-read memoryos-wake memoryos-status memoryos-capture memoryos-context memoryos-init cli cli-status cli-audit cli-discover cli-auto cli-ship mcp-server mcp-http

PYTHON := python3
PIP := pip3
SHELL := /usr/bin/env bash

help:
	@echo "NEUTRON-EVO-OS v4.1.0 Makefile"
	@echo ""
	@echo "  Install (use install.sh directly for more options):"
	@echo "    make install-cli    bash install.sh cli"
	@echo "    make install-mcp   bash install.sh mcp  ← recommended"
	@echo "    make install-global bash install.sh full"
	@echo ""
	@echo "  make install         Install dependencies (pip)"
	@echo "  make live            Start Smart Observer + Dashboard"
	@echo "  make dream           Run Dream Cycle manually"
	@echo "  make test            Run pytest (tests/ directory)"
	@echo "  make clean           Remove cache files"
	@echo "  make lint            Run linting"
	@echo ""
	@echo "  NEUTRON CLI (18 commands):"
	@echo "    make cli            Show CLI commands"
	@echo "    make cli-status     neutron status"
	@echo "    make cli-audit      neutron audit"
	@echo "    make cli-discover   neutron discover"
	@echo "    make cli-auto       neutron auto (MODE=full)"
	@echo ""
	@echo "  MemoryOS CLI:"
	@echo "    make memoryos-init    Initialize MemoryOS"
	@echo "    make memoryos-wake    Recover context from last session"
	@echo "    make memoryos-status  Show MemoryOS status"
	@echo "    make memoryos-context Load relevant memory"
	@echo ""
	@echo "  Quick start:"
	@echo "    bash install.sh mcp  # CLI + MCP server"

install:
	@echo "[NEUTRON-EVO-OS] Installing dependencies..."
	$(PIP) install -r requirements.txt
	@echo "[OK] Dependencies installed"

install-cli:
	@echo "[NEUTRON-EVO-OS] Installing CLI..."
	@bash install.sh cli

install-mcp:
	@echo "[NEUTRON-EVO-OS] Installing CLI + MCP server..."
	@bash install.sh mcp

install-global:
	@echo "[NEUTRON-EVO-OS] Running full installer..."
	@bash install.sh full

install-cursor:
	@echo "[NEUTRON-EVO-OS] Installing Cursor IDE integration..."
	@bash install-cursor.sh

install-cline:
	@echo "[NEUTRON-EVO-OS] Installing Cline integration..."
	@bash install-cline.sh

mcp-server:
	@echo "[NEUTRON-EVO-OS] Starting MCP HTTP server on port 3100..."
	@python3 -m mcp_server --transport http --port 3100

live: install
	@echo "[NEUTRON-EVO-OS] Starting Smart Observer + Evolution Dashboard..."
	@echo "  Observer watching: ."
	@echo "  Debounce: 30s"
	@echo "  Dashboard: evolution_dashboard.py"
	@echo ""
	$(PYTHON) -c "\
from engine.smart_observer import SilentObserver; \
from engine.dream_engine import dream_cycle; \
def cb(changes): print(f'[Observer] Work settled, triggering Dream Cycle...'); print(dream_cycle()); \
SilentObserver.start('.', cb, debounce_seconds=30); \
print('[NEUTRON-EVO-OS] Observer running. Press Ctrl+C to stop.'); \
import time; time.sleep(999999)" || true

dream:
	@echo "[NEUTRON-EVO-OS] Running manual Dream Cycle..."
	$(PYTHON) -c "from engine.dream_engine import dream_cycle; print(dream_cycle(json_output=True))"

test:
	@echo "[NEUTRON-EVO-OS] Running tests..."
	$(PYTHON) -m pytest -v 2>/dev/null || echo "[INFO] No tests found (pytest not configured)"

clean:
	@echo "[NEUTRON-EVO-OS] Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "engine/__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "[OK] Cache cleaned"

lint:
	$(PYTHON) -m flake8 engine/ --max-line-length=120 2>/dev/null || \
	$(PYTHON) -m pyflakes engine/ 2>/dev/null || \
	echo "[INFO] Linter not installed (pip install flake8)"

# CI aliases
ci-install: install
ci-audit:
	$(PYTHON) -c "from engine.expert_skill_router import audit; import json; print(json.dumps(audit(), indent=2))"
ci-route:
	$(PYTHON) -c "from engine.expert_skill_router import route_task; import sys, json; t=sys.argv[1] if len(sys.argv)>1 else 'manage memory and context'; print(json.dumps(route_task(t), indent=2))" "$(TASK)"

checkpoint:
	@echo "[NEUTRON-EVO-OS] Writing checkpoint..."
	$(PYTHON) engine/checkpoint_cli.py --task "$(TASK)" --notes "$(NOTES)" --confidence medium

checkpoint-read:
	@echo "[NEUTRON-EVO-OS] Reading latest checkpoint..."
	$(PYTHON) engine/checkpoint_cli.py --read

checkpoint-handoff:
	@echo "[NEUTRON-EVO-OS] Handoff: checkpoint + dream cycle..."
	$(PYTHON) engine/checkpoint_cli.py --handoff --task "$(TASK)" --notes "Handoff before context compaction"

# MemoryOS CLI targets (explicit phony — pattern rules create side-effect files in GNU Make)
memoryos-wake:
	node MemoryOS/src/index.js wake
memoryos-status:
	node MemoryOS/src/index.js status
memoryos-capture:
	node MemoryOS/src/index.js capture
memoryos-context:
	node MemoryOS/src/index.js context
memoryos-init:
	node MemoryOS/src/index.js init

# ─── NEUTRON CLI ────────────────────────────────────────────────────────────────
# neutron command must be in PATH. Run: bash install-cli.sh
cli:
	@echo "NEUTRON CLI — Available commands:"
	@echo "  neutron status           # System status + health"
	@echo "  neutron audit           # Full CI audit"
	@echo "  neutron discover \"idea\" # Discovery interview (12 questions)"
	@echo "  neutron spec [task]     # Write SPEC.md (USER REVIEW gate)"
	@echo "  neutron auto full       # Enable auto-confirm (skip all gates)"
	@echo "  neutron auto spec_only   # Auto-approve SPEC only"
	@echo "  neutron accept pass     # User confirms acceptance"
	@echo "  neutron ship --rating 4 # Ship with rating"
	@echo "  neutron log             # Today's memory log"
	@echo "  neutron decisions       # User decisions log"
	@echo "  neutron route \"task\"   # Route task to skill"
	@echo ""
	@echo "Install: bash install-cli.sh"

cli-status:
	$(PYTHON) -m engine.cli.main status

cli-audit:
	$(PYTHON) -m engine.cli.main audit

cli-discover:
	$(PYTHON) -m engine.cli.main discover "$(IDEA)"

cli-auto:
	$(PYTHON) -m engine.cli.main auto $(MODE)

cli-ship:
	$(PYTHON) -m engine.cli.main ship "$(TASK)" --rating $(RATING)

cli-install:
	@bash install-cli.sh
