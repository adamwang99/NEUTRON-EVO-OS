# SKILL: Checkpoint — Session State Persistence

> NEUTRON EVO OS v4.1.0 | CI tracking: skill router
> Context: Long-running agent sessions → context compression survival

## Purpose

Dump current session state to disk so that:
1. **Compaction survives**: After `/compact`, agent reads checkpoint → knows "I was doing X"
2. **Resume accurate**: Human or AI resuming knows exact context, blockers, next step
3. **Dream Cycle feeds**: Checkpoint becomes source for distillation

## Usage

```
/checkpoint [optional focus]
```

Examples:
```
/checkpoint                    → full state dump
/checkpoint trading module     → focus on trading module
/compact Continue the current task
```

## Checkpoint Format

Written to `memory/{date}.md` in structured YAML-frontmatter style:

```markdown
# Checkpoint — {timestamp}

> NEUTRON EVO OS v4.0.0 | Session: checkpoint

## State
- **Status**: in_progress | paused | blocked | complete
- **Task**: {what was being worked on}
- **Focus**: {optional focus area from agent}
- **Confidence**: {high|medium|low}

## Current Work
- Files modified: [list]
- Files created: [list]
- Last action: {description}
- Output: {summary of result}

## Blockers
- [ ] {blocker 1}
- [ ] {blocker 2}

## Next Steps (priority order)
1. {step 1}
2. {step 2}
3. {step 3}

## Decisions Made
- {decision 1} → reason
- {decision 2} → reason

## Notes
{Other relevant context}
```

## Trigger Points (when to call /checkpoint)

| Situation | Trigger |
|-----------|---------|
| Before `/compact` | REQUIRED |
| Before `/rewind` | REQUIRED |
| Every ~30 min in long sessions | RECOMMENDED |
| Before ending session | REQUIRED |
| When blocked for > 5 min | REQUIRED |
| When task completes | RECOMMENDED |

## Checkpoint Chain

```
Agent starts task
    ↓
Every N minutes: /checkpoint
    ↓
Context approaches 80%: /compact + /checkpoint
    ↓
After compaction: reads checkpoint → restores context
    ↓
Task continues with full awareness
```

## Auto-Checkpoint via Hook

The PreToolUse hook monitors for compaction commands and triggers auto-checkpoint.
See `engine/checkpoint_cli.py` for the CLI wrapper.

## CI Impact

| Event | CI Delta |
|-------|----------|
| Checkpoint saved before compaction | +5 (preservation) |
| Checkpoint found and used on resume | +3 (context recovery) |
| Resume without checkpoint (lost context) | -5 (context loss) |
| Stale checkpoint used (> 1hr) | +0 (unreliable) |

## Execution Contract (Phase 5)

This skill is fully executable via the plugin system.

- **Logic module**: `skills/core/checkpoint/logic/__init__.py`
- **Function**: `run_checkpoint(task, context)` → `{status, output, ci_delta}`
- **Validation**: `skills/core/checkpoint/validation/__init__.py`
- **Actions**: `write` (default), `read`, `handoff` — via `context["action"]`
- **Inputs**: `task`, `notes`, `confidence` — via context dict
- **Dependencies**: Python 3.8+, `engine/checkpoint_cli.py`
