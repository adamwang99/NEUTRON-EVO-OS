# Release Notes — NEUTRON-EVO-OS v4.0.0

**∫f(t)dt — Functional Credibility Over Institutional Inertia**

📅 **Date:** March 29, 2026
🏷️ **Tag:** v4.0.0
🔖 **Previous:** v0.2.0 (ai-context-master)

---

## What's New

### 🚀 Identity Overhaul
- **Global Rebrand:** `ai-context-master` → **NEUTRON-EVO-OS**
- **New Manifesto:** [MANIFESTO.md](./MANIFESTO.md) — formalizes the ∫f(t)dt philosophy
- **New Soul:** [SOUL.md](./SOUL.md) — Sovereignty & Meritocracy as core values
- **New Rules:** [RULES.md](./RULES.md) — 5-step workflow: `/explore` → `/spec` → `/build` → `/verify` → `/ship`

### 🧠 Memory 2.0 — Self-Dreaming OS
- **Dream Engine:** Automatic memory distillation via `engine/dream_engine.py`
  - **Pruning:** Removes noise and stale temporary files
  - **Distillation:** Compresses logs into structured Cookbooks
  - **Safety First:** All existing user data archived to `/memory/archived/` — **never deleted**
- **Smart Observer:** `engine/smart_observer.py` monitors source changes with debounce logic — triggers Dream Cycle only after work settles

### ⚙️ Skill Architecture (Anthropic Folder Style)
```
skills/
├── core/
│   ├── context/   — Context loading, injection, anti-hallucination
│   ├── memory/    — Dream Cycle, archive, daily log management
│   ├── workflow/  — 5-step workflow execution engine
│   └── engine/    — Skill router + core system components
└── learned/       — Future learned skills (empty, ready)
```
Every skill follows a **Layer 1 (YAML Metadata + CI)** + **Layer 2 (Execution Logic)** structure.

### 📊 Credibility Index System
- **PERFORMANCE_LEDGER.md:** Tracks CI (Credibility Index) for every agent and skill
- **evolution_dashboard.py:** Rich Terminal UI — real-time CI visualization with `[STATUS: DREAMING]`
- **expert_skill_router.py:** CI-gated skill routing — tasks only routed to skills that pass credibility audit

### 🛠️ Developer Experience
- **Makefile shortcuts:**
  - `make live` — Start observer + dashboard
  - `make dream` — Manual Dream Cycle
  - `make test` — Run tests
  - `make clean` — Clean cache
- **requirements.txt:** `watchdog>=3.0.0`, `rich>=13.0.0`
- **VS Code Extension:** Fully updated with NEUTRON-EVO-OS branding

---

## Breaking Changes

| Before | After |
|--------|-------|
| `ai-context-master` | `NEUTRON-EVO-OS` |
| Flat `.md` skills | Folder-based `SKILL.md` structure |
| No performance tracking | `PERFORMANCE_LEDGER.md` + CI system |
| Manual memory cleanup | Automated Dream Cycle |

---

## Migration Guide

```bash
# Pull the latest
git pull origin main

# Install dependencies
pip install -r requirements.txt
npm install

# First Dream Cycle (archives existing logs safely)
make dream

# Start live mode
make live
```

---

## Stats

| Metric | Value |
|--------|-------|
| Files Changed | 41 |
| Lines Added | +1,925 |
| Lines Removed | -842 |
| New Features | 8 major |
| Breaking Changes | 4 |

---

## What's Next

- v4.1.0: CLI integration (neutron-evo command)
- v4.2.0: Web dashboard with WebSocket live updates
- v4.3.0: Multi-agent coordination protocol

---

*Built with ∫f(t)dt — every commit is a function of time, accumulated.*
