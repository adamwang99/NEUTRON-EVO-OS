# NEUTRON EVO OS — Production Safety Rules

> **Source:** Distilled from `claude-code-ultimate-guide` + NEUTRON governance.
> These are non-negotiable rules for any project built with NEUTRON.

---

## The Verification Paradox

> At ~95% AI reliability, **human vigilance fatigue** causes missing the last 5% of errors.
> The solution: shift from manual review to automated guardrails.

**The problem:**
```
Human: "AI is 95% reliable, I can skip some checks"
→ AI makes 1 error in 20 tasks
→ Human has stopped checking every output
→ 1 error in 20 × no checks = 1 undetected error
→ With 20 tasks, that's ~1 undetected error per session
```

**The solution:**
```
Automated guardrails (NEUTRON gates) + human judgment on exceptions only
- SPEC gate: automated check, human approval
- Acceptance gate: automated test generation, human confirmation
- CI delta: automated quality signal
- NEVER: human reviews everything → gets fatigued → misses errors
```

---

## 8 Production Safety Rules

### Rule 1: Port Stability ⚡ [CRITICAL]

```python
# BEFORE shipping any feature that changes ports:
# 1. Check: port not used by another service
# 2. Document: port in memory/PROJECT_PORTS.md
# 3. Warn: if port < 1024 (requires root on Unix)
```

**NEUTRON gate:** Workflow `/build` requires `PORT_PLAN.md` if the feature uses ports.

### Rule 2: Database Safety ⚡ [CRITICAL]

```python
# BEFORE any database operation:
# 1. Backup first: neutron protect --target database
# 2. Check: this is not production
# 3. Test: run on synthetic data first
# 4. Rollback: have a rollback plan
```

**NEUTRON gate:** `acceptance_test` skill must pass before any DB change ships.

### Rule 3: Feature Completeness ✓ [HIGH]

```python
# BEFORE shipping:
# 1. All SPEC acceptance criteria met?
# 2. Error handling complete (not just happy path)?
# 3. Edge cases handled?
# 4. Docs updated?
```

**NEUTRON gate:** `acceptance_test` generates a checklist from SPEC acceptance criteria.

### Rule 4: Infrastructure Lock ✓ [HIGH]

```python
# AFTER shipping:
# 1. Don't change infrastructure without change management
# 2. Document all env vars (memory/.env_spec.md)
# 3. Commit infrastructure as code
```

**NEUTRON gate:** `neutron protect` must be run before `pip install`, `npm install`, `docker pull`.

### Rule 5: Dependency Safety ✓ [MEDIUM]

```python
# BEFORE adding a dependency:
# 1. npm audit / pip audit
# 2. Check: last commit < 6 months?
# 3. Check: >10 contributors?
# 4. Check: security policy exists?
# 5. Pin version: exact, not "^1.2.3"
```

**NEUTRON gate:** `workflow verify` runs `npm audit` / `pip audit` automatically.

### Rule 6: Pattern Following ✓ [LOW]

```python
# BEFORE inventing a new solution:
# 1. Check: memory/LEARNED.md for existing patterns
# 2. Check: memory/cookbooks/ for similar problems
# 3. Check: skills/core/feature_library/ for known patterns
# 4. Only then: invent new solution
```

**NEUTRON gate:** `workflow spec` checks LEARNED.md for existing solutions before designing.

### Rule 7: Autonomous Loop Safety ✓ [HIGH]

> Inspired by `claude-code-ultimate-guide` operational safety rules.

```python
# BEFORE starting autonomous loop:
# 1. Set a max turns limit: maxTurns=50 in Agent config
# 2. Set a timeout: < 5 minutes
# 3. Define stall detection: no new files created in 10 turns
# 4. Define exit criteria: test passes, or max turns reached
# 5. Budget: set LLM token budget, stop if exceeded
```

**NEUTRON gate:** Orchestration skill uses `maxTurns=50` + timeout enforcement.

### Rule 8: Error Budget Enforcement ✓ [MEDIUM]

```python
# Track error rate over time:
# 1. Shipments with rating 1-2 / 5 → error
# 2. If > 20% shipments have errors → pause new features
# 3. Focus on reliability until error rate < 10%
```

**NEUTRON gate:** `rating.py` tracks ratings, `audit()` shows health degradation.

---

## Implementation Checklist

Every project built with NEUTRON must have:

```
□ memory/PROJECT_PORTS.md        — documented ports
□ memory/.env_spec.md           — all env vars with descriptions
□ SPEC.md acceptance criteria    — measurable, testable
□ neutron protect run before     — any dependency install
□ acceptance_test pass           — before any ship
□ rating submitted              — after every delivery
```

---

## NEUTRON-Specific Rules

### Context Pressure Warning

```
NEUTRON CONTEXT ENGINEERING RULES:

- 0-50% context: normal operation
- 50-70%: precision starts degrading
- 70%+: high risk of errors — trigger proactive compaction
- 92%+: Claude Code auto-compacts — 50-70% information loss

NEUTRON RESPONSE:
- context skill tracks context usage
- neutron context audit → shows P0/P1/P2 priorities
- neutron snapshot save → checkpoint before large work blocks
- SessionStart → shows context snapshot if < 4h old
```

### Multi-Agent Coordination Safety

```
NEUTRON ORCHESTRATION RULES:

- Each agent has its own 1M token context (Claude Code limit)
- Max depth = 1 (no sub-sub-agents)
- Agents communicate via git-based coordination
- Lock files prevent double-write: .claude/tasks/<task>.lock
- Hard token budget per agent: 500K tokens max
- Stall detection: 10 turns without new output → stop
```

### Learned Entry Quality Gates

```
NEUTRON LEARNED.md RULES:

Entries MUST have:
- Bug: <descriptive title>
- Symptom: what went wrong (specific)
- Root cause: why it happened (not just "I fixed it")
- Fix: exact change (file:line if known)
- Tags: #boundary #gc #threading #mcp etc.

Entries MUST NOT have:
- Raw log excerpts
- "From project: N log excerpt(s)"
- Vague descriptions ("it broke sometimes")
```
