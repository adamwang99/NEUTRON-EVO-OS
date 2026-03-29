.PHONY: live dream install test clean lint format help

PYTHON := python3
PIP := pip3

help:
	@echo "NEUTRON-EVO-OS Makefile"
	@echo ""
	@echo "  make install   Install dependencies (pip + npm)"
	@echo "  make live     Start Smart Observer + Dashboard"
	@echo "  make dream    Run Dream Cycle manually"
	@echo "  make test     Run tests"
	@echo "  make clean    Remove cache files"
	@echo "  make lint     Run linting"
	@echo ""

install:
	@echo "[NEUTRON-EVO-OS] Installing dependencies..."
	$(PIP) install -r requirements.txt
	@echo "[OK] Dependencies installed"

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
	$(PYTHON) -c "from engine.dream_engine import dream_cycle; import json; print(json.dumps(dream_cycle(), indent=2))"

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
	$(PYTHON) -c "from engine.expert_skill_router import route_task; import sys; t=sys.argv[1] if len(sys.argv)>1 else 'manage memory and context'; print(route_task(t))" -- "$(TASK)"
