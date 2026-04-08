"""
NEUTRON-EVO-OS: Dream Engine — Memory 2.0 Core with AI Gatekeeper
Implements an AI-driven 5-phase pipeline:
  1. AI_ANALYZE  — Claude Opus classifies session events
  2. FILTER      — pre-filter noise before sending to AI
  3. SYNTHESIZE  — build decision-tree cookbooks
  4. SUGGEST     — write LEARNED_pending.md drafts (human approval gate)
  5. ARCHIVE/PRUNE — standard log compression + retention
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
import threading
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger("neutron-evo-os")

from engine.smart_observer import SilentObserver

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"
ARCHIVED_DIR = MEMORY_DIR / "archived"
COOKBOOKS_DIR = MEMORY_DIR / "cookbooks"
PENDING_DIR = MEMORY_DIR / "pending"          # LEARNED_pending.md drafts
NOISE_THRESHOLD_DAYS = 3   # days old before archiving
ARCHIVED_RETENTION_DAYS = 7  # max age for archived files
MAX_ARCHIVED_COUNT = 500    # hard cap: delete oldest beyond this count
MAX_SESSION_LOG_LINES = 500  # hard cap on active session log size
MAX_COOKBOOKS = 30          # keep only N most recent cookbooks

# Test guard: when True, dream_cycle skips archiving to avoid polluting
# the real system archived/ directory during pytest runs.
# Tests set this via monkeypatch before calling dream_cycle().
_IS_TEST_MODE = os.environ.get("NEUTRON_DREAM_TEST", "") == "1"


def _atomic_write(path: Path, content: str) -> None:
    """
    Write content to path atomically: write to temp file → fsync → rename.
    Prevents partial-write corruption on crash. Thread-safe.
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, delete=False, encoding="utf-8"
    )
    try:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, str(path))
    except Exception:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        raise
MAX_PENDING_AGE_DAYS = 7    # auto-archive pending entries older than this

# Re-entrancy guard: prevents concurrent dream cycles.
# Uses a filelock file instead of threading.Event so it works ACROSS PROCESSES.
# FileLock instance is created ONCE so is_locked accurately reflects lock state.
# Path is resolved once at module level — override MEMORY_DIR before import in tests.
_DREAM_LOCK_CACHE: filelock.FileLock | None = None


def _get_dream_lock() -> "filelock.FileLock":
    """Get or create the dream cycle filelock (process-safe, respects MEMORY_DIR at call time)."""
    global _DREAM_LOCK_CACHE
    if _DREAM_LOCK_CACHE is None:
        import filelock as _filelock
        lock_path = str(MEMORY_DIR / ".dream.lock")
        _DREAM_LOCK_CACHE = _filelock.FileLock(lock_path, timeout=5)
    return _DREAM_LOCK_CACHE

# Sentinel file — if this file exists, observer should NOT restart dream cycle
_DREAM_SENTINEL = MEMORY_DIR / ".dream_active"


# ── Noise pre-filter patterns ────────────────────────────────────────────────

# Absolute noise: ALWAYS filtered, regardless of keywords.
# These represent structural/logging artifacts, not actual events.
_ABSOLUTE_NOISE_PATTERNS = [
    # Skill checkpoint format (fixed, repeated every skill call)
    re.compile(r"^\s*##\s+\[\d{2}:\d{2}\]\s+—\s+Skill:\s+\w+\s+\|\s+Task:"),
    # Test passes
    re.compile(r"(?:PASSED|passed|ok|✓|✔)\s*(?:test|Test|pytest|Pytest)", re.IGNORECASE),
    re.compile(r"(?:test|pytest).*(?:pass|ok)", re.IGNORECASE),
    # Read-only commands (grep, ls, cat, pwd, find, echo, head, tail)
    # ALWAYS noise: grepping "error" ≠ having an error
    re.compile(r"^\s*(?:grep|ls|cat|pwd|find|head|tail|echo|which|whoami|id)[\s\-(@]", re.IGNORECASE),
    # Empty/no-op lines
    re.compile(r"^\s*(?:-|–|-|\*)\s*$"),
    re.compile(r"^\s*(?:Outcome:|Action:|Notes:)\s*$"),
    # MCP tool invocations
    re.compile(r"^.*(?:mcp__|MCP\s).*$"),
]

# Keyword-dependent noise: filtered if no stack trace / file:line context.
# Generic errors without context → filtered. Real errors with context → keep.
_STACKTRACE_PATTERN = re.compile(
    r"(?:File\s+\"|'[^']+\.py'|\.py\",?\s+line|traceback|at\s+\w+\.|"
    r"raise\s+\w+|Error:|Exception:)"
)

# Keywords that indicate a line is SIGNIFICANT even if it matches keyword-noise.
# Only applies when the line also has stack trace / file context.
_SIGNIFICANT_KEYWORDS = [
    "error", "exception", "fail", "traceback", "stderr",
    "decision:", "approved", "chose", "rejected", "selected",
    "root cause", "bug:", "fix:", "symptom",
    "unexpected", "should not", "but got", "expected",
]


def _is_noise(line: str) -> bool:
    """
    Classify a single log line as noise.
    Returns True = skip (don't send to AI).
    - Absolute patterns: always noise
    - Keyword patterns: only noise if no significant keywords + context
    """
    for pat in _ABSOLUTE_NOISE_PATTERNS:
        if pat.search(line):
            return True
    # Generic execution_error without context → always noise
    if re.search(r"^\s*(?:-|–|-|\*)\s*Outcome:\s*execution_error\s*$", line, re.IGNORECASE):
        return True
    return False


def _normalize_event(line: str) -> str:
    """Normalize a line for duplicate detection."""
    # Strip timestamps, paths, hashes
    result = re.sub(r"\d{4}-\d{2}-\d{2}", "[DATE]", line)
    result = re.sub(r"/[\w/\.-]+", "[PATH]", result)
    result = re.sub(r"[a-f0-9]{6,}", "[HASH]", result)
    result = re.sub(r"\d{2}:\d{2}:\d{2}", "[TIME]", result)
    return result.strip()


def _pre_filter(content: str) -> tuple[str, dict]:
    """
    Pre-filter raw log content before sending to AI.
    Returns (filtered_content, stats_dict).
    Stats: lines_removed, duplicates_removed, lines_kept.
    """
    lines = content.splitlines()
    kept = []
    dup_count: dict[str, int] = {}

    for line in lines:
        if _is_noise(line.strip()):
            continue
        kept.append(line)

    # Deduplicate: count normalized lines, remove if ≥3 occurrences
    filtered = []
    for line in kept:
        norm = _normalize_event(line)
        dup_count[norm] = dup_count.get(norm, 0) + 1

    for line in kept:
        norm = _normalize_event(line)
        if dup_count[norm] >= 3:
            continue  # skip duplicate ≥3x
        filtered.append(line)

    stats = {
        "lines_removed_noise": sum(1 for l in lines if _is_noise(l.strip())),
        "duplicates_removed": sum(c - 1 for c in dup_count.values() if c >= 3),
        "lines_kept": len(filtered),
    }
    return "\n".join(filtered), stats


# ── Rule-Based Distill (AI-free fallback) ───────────────────────────────────

def _rule_based_distill(filtered_by_date: dict[str, tuple[str, dict]]) -> dict:
    """
    Extract patterns from session logs WITHOUT AI.

    This is the AI-free fallback when ANTHROPIC_API_KEY is not set.
    Uses heuristics to find:
    - Error patterns (tracebacks, exceptions, crashes)
    - Decision patterns (chose, decided, approved, rejected)
    - First-time patterns (new files, new imports, new patterns)
    - Quality patterns (test failures, regressions)

    Returns the same structure as _call_claude_analysis() so the rest
    of the pipeline (cookbook writing, LEARNED pending) works identically.
    """
    sig_events: list[dict] = []
    cookbook_sections: list[dict] = []
    learned_drafts: list[dict] = []

    ERROR_PATTERNS = [
        (re.compile(r"(?i)error:|exception:|traceback|failed:|crash|panic", re.M), "error"),
        (re.compile(r"(?i)timeout|deadlock|race condition", re.M), "concurrency"),
        (re.compile(r"(?i)memory leak|leak", re.M), "memory"),
        (re.compile(r"(?i)import.*error|modulenotfound|no module|nomodule", re.M), "import"),
        (re.compile(r"(?i)syntaxerror|parse error|jsondecodeerror", re.M), "parse"),
        (re.compile(r"(?i)filelock|lock.*timeout|deadlock", re.M), "concurrency"),
    ]

    DECISION_PATTERNS = [
        (re.compile(r"(?i)chose|selected|decided|approved|rejected|picked|preferred", re.M), "decision"),
        (re.compile(r"(?i)instead of|rather than|switched from|replaced with", re.M), "decision"),
        (re.compile(r"(?i)because|reason: rationale:", re.M), "reasoning"),
    ]

    FIRST_TIME_PATTERNS = [
        re.compile(r"(?i)first time|initial|new file|new module|new skill|new hook"),
        re.compile(r"(?i)created|wrote|added.*new"),
    ]

    FILES_TOUCHED: set[str] = set()

    for date, (content, _stats) in filtered_by_date.items():
        lines = content.splitlines()

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip absolute noise
            if _is_noise(stripped):
                continue

            # Skip generic info / short lines
            if len(stripped) < 15:
                continue

            # Track files mentioned
            for m in re.finditer(r"(?:engine|skills|mcp_server|hooks)/[\w/]+\.(?:py|sh|md|json)", stripped):
                FILES_TOUCHED.add(m.group())

            # Error events — must have specific context
            matched = False
            for pat, err_type in ERROR_PATTERNS:
                if pat.search(stripped):
                    # Must have file:line context OR specific error indicators
                    has_context = (
                        re.search(r"[\w/]+\.(?:py|sh|md|json)[:\s]+(?:line\s+)?\d+", stripped) or
                        re.search(r"(?:Error|Exception|Failed|Crash|Timeout|Traceback)", stripped, re.IGNORECASE)
                    )
                    if has_context:
                        ctx_m = re.search(r"([\w/]+\.(?:py|sh|md|json))[:,\s]+(?:line\s+)?(\d+)", stripped)
                        ctx = f"{ctx_m.group(1)}:{ctx_m.group(2)}" if ctx_m else stripped[:80]
                        severity = "high" if any(k in stripped.lower() for k in ["crash", "fatal", "deadlock"]) else "medium"
                        sig_events.append({
                            "type": "error",
                            "summary": f"{err_type.upper()}: {stripped[:80]}",
                            "context": ctx,
                            "severity": severity,
                            "raw_snippets": [stripped[:120]],
                            "_date": date,
                        })
                        # Draft LEARNED entry
                        learned_drafts.append({
                            "title": f"{err_type} in session {date}",
                            "symptom": stripped[:200],
                            "root_cause": "See context in session log",
                            "fix": "Review session log for details",
                            "tags": f"#{err_type}",
                            "_date": date,
                        })
                        matched = True
                        break

            if matched:
                continue

            # Decision events — must have meaningful rationale
            for pat, dec_type in DECISION_PATTERNS:
                if pat.search(stripped) and len(stripped) > 25:
                    sig_events.append({
                        "type": "decision",
                        "summary": stripped[:100],
                        "context": stripped[:200],
                        "severity": "medium",
                        "raw_snippets": [stripped[:120]],
                        "_date": date,
                    })
                    cookbook_sections.append({
                        "title": f"Decision: {stripped[:60]}",
                        "trigger": f"Occurred during {date} session",
                        "recognition": stripped[:200],
                        "resolution": "Recorded in session log",
                        "prevention": "Document decision rationale in user_decisions.json",
                        "related_events": [],
                    })
                    break

    # Deduplicate: same error type + similar text → merge
    deduped_events = {}
    for event in sig_events:
        key = (event["type"], event["summary"][:40])
        if key not in deduped_events:
            deduped_events[key] = event

    deduped_cookbooks = {}
    for section in cookbook_sections:
        key = section["title"][:40]
        if key not in deduped_cookbooks:
            deduped_cookbooks[key] = section

    # Deduplicate drafts
    deduped_drafts = {}
    for draft in learned_drafts:
        key = (draft["title"][:40], draft.get("tags", ""))
        if key not in deduped_drafts:
            deduped_drafts[key] = draft

    return {
        "status": "rule_based",
        "source": "rule_based_distill (AI-free)",
        "significant_events": list(deduped_events.values())[:10],
        "cookbook_sections": list(deduped_cookbooks.values())[:5],
        "learned_drafts": list(deduped_drafts.values())[:5],
        "files_touched": sorted(FILES_TOUCHED)[:20],
    }


# ── AI Analysis via Claude API ──────────────────────────────────────────────

def _call_claude_analysis(filtered_log: str, learned_content: str = "") -> dict:
    """
    Call Claude Opus API to analyze session logs and produce structured output.
    Returns dict with keys: significant_events, cookbook_sections, learned_drafts.
    """
    try:
        import anthropic
    except ImportError:
        return {
            "status": "error",
            "message": "anthropic package not installed: pip install anthropic",
            "significant_events": [],
            "cookbook_sections": [],
            "learned_drafts": [],
        }

    model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-20250514")
    # Support both ANTHROPIC_API_KEY (standard) and ANTHROPIC_AUTH_TOKEN (legacy)
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")

    if not api_key:
        return {
            "status": "error",
            "message": "ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN) not set — cannot run AI analysis",
            "significant_events": [],
            "cookbook_sections": [],
            "learned_drafts": [],
        }

    # Search LEARNED.md for existing patterns (don't re-feed into prompt)
    existing_bugs = []
    if learned_content:
        # Extract bug titles for dedup
        for line in learned_content.splitlines():
            if re.match(r"^\s*##?\s+\[.*?\]\s+Bug:", line, re.IGNORECASE):
                existing_bugs.append(line.strip()[:100])

    system_prompt = """You are a senior software engineer reviewing a coding session log.
Your job: identify SIGNIFICANT events and synthesize actionable patterns.

**Output format: valid JSON only, no markdown, no explanation outside JSON.**

{
  "significant_events": [
    {
      "type": "error|decision|unexpected|novel",
      "summary": "one-line summary",
      "context": "relevant context lines",
      "severity": "high|medium|low",
      "raw_snippets": ["relevant line 1", "relevant line 2"]
    }
  ],
  "cookbook_sections": [
    {
      "title": "Bug: <descriptive title>",
      "trigger": "When does this happen?",
      "recognition": "How to recognize this pattern?",
      "resolution": "Step-by-step fix (use code blocks if helpful)",
      "prevention": "How to prevent recurrence?",
      "related_events": [index in significant_events array]
    }
  ],
  "learned_drafts": [
    {
      "title": "<bug title>",
      "symptom": "What went wrong?",
      "root_cause": "Why did it happen?",
      "fix": "Exact fix (file:line if known)",
      "tags": "#tag1 #tag2"
    }
  ]
}

**Classification rules:**
- SIGNIFICANT: real errors with stack traces, decisions with WHY, unexpected outcomes, first-time patterns
- NOISE (skip): skill checkpoints, test passes, read-only commands, duplicates ≥3x, generic errors without context

**Cookbook style:** Write for a developer encountering this problem fresh.
Be specific. Use code examples where helpful. Resolution steps must be actionable.

If no significant events found, return empty arrays. Never fabricate events."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        # Truncate if too long (AI token budget)
        truncated = filtered_log[-80_000:] if len(filtered_log) > 80_000 else filtered_log

        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Session logs:\n{truncated}"}],
            timeout=60.0,
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"Dream Cycle: AI response not valid JSON: {e}")
        return {"status": "error", "message": f"AI response parse error: {e}",
                "significant_events": [], "cookbook_sections": [], "learned_drafts": []}
    except Exception as e:
        logger.warning(f"Dream Cycle: AI call failed: {e}")
        return {"status": "error", "message": str(e),
                "significant_events": [], "cookbook_sections": [], "learned_drafts": []}


# ── Cookbook writing ────────────────────────────────────────────────────────

def _write_cookbook(log_name: str, ai_result: dict, timestamp: str) -> list[str]:
    """Write a decision-tree cookbook from AI result."""
    COOKBOOKS_DIR.mkdir(exist_ok=True)
    path = COOKBOOKS_DIR / f"{log_name}_cookbook.md"

    lines = [
        f"# Cookbook: {log_name}",
        "",
        f"> Distilled on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> ∫f(t)dt — Functional Credibility Over Institutional Inertia",
        "",
    ]

    sig_events = ai_result.get("significant_events", [])
    if sig_events:
        high = [e for e in sig_events if e.get("severity") == "high"]
        med = [e for e in sig_events if e.get("severity") == "medium"]
        lines.append(f"## Significant Events ({len(sig_events)} total)")
        lines.append(f"- High severity: {len(high)} | Medium: {len(med)}")
        lines.append("")
        for e in sig_events[:10]:
            lines.append(f"- **{e['type'].upper()}** ({e['severity']}): {e['summary']}")
        lines.append("")

    sections = ai_result.get("cookbook_sections", [])
    if sections:
        lines.append(f"## Actionable Patterns ({len(sections)} discovered)")
        lines.append("")
        for s in sections:
            lines.append(f"### {s['title']}")
            for field in ["trigger", "recognition", "resolution", "prevention"]:
                if s.get(field):
                    lines.append(f"**{field.title()}:**")
                    # Indent code blocks
                    for ln in s[field].split("\n"):
                        lines.append(f"    {ln}" if ln.strip().startswith("```") else f"  {ln}")
                    lines.append("")
        lines.append("")

    if not sections and not sig_events:
        lines.extend([
            "## Summary",
            "No significant events detected in this session.",
            "The session was clean — all events were noise or expected.",
            "",
        ])

    lines.extend([
        "---",
        "*Auto-generated by NEUTRON Dream Cycle (AI analysis). Do not edit — archive instead.*",
    ])

    _atomic_write(path, "\n".join(lines))
    return [str(path)]


# ── LEARNED pending drafts ──────────────────────────────────────────────────

def _write_learned_pending(drafts: list[dict]) -> int:
    """
    Write AI-generated LEARNED drafts to memory/pending/LEARNED_pending.md.
    Thread-safe: uses filelock + atomic write.
    Auto-expire: entries older than 7 days → archived/.
    """
    if not drafts:
        return 0
    PENDING_DIR.mkdir(exist_ok=True)
    pending_path = PENDING_DIR / "LEARNED_pending.md"
    lock_path = PENDING_DIR / "LEARNED_pending.lock"
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    draft_id_base = today.strftime("%Y%m%d")

    entries = []
    for i, draft in enumerate(drafts, 1):
        draft_id = f"pending-{draft_id_base}-{i}"
        entry = (
            f"\n## [{today_str}] [PENDING] Bug: {draft['title']}\n"
            f"- **Symptom:** {draft['symptom']}\n"
            f"- **Root cause:** {draft['root_cause']}\n"
            f"- **Fix:** {draft['fix']}\n"
            f"- **Tags:** {draft.get('tags', '#bug')}\n"
            f"- **Draft ID:** {draft_id}\n"
            f"- **Suggested by:** AI (Dream Cycle)\n"
            f"- **Status:** awaiting approval\n"
        )
        entries.append(entry)

    import filelock
    lock = filelock.FileLock(str(lock_path), timeout=10)
    with lock:
        existing = pending_path.read_text() if pending_path.exists() else ""
        _atomic_write(pending_path, existing + "\n".join(entries))
    return len(drafts)


def _prune_expired_pending() -> int:
    """
    Remove pending entries older than MAX_PENDING_AGE_DAYS (auto-archive, not delete).
    Thread-safe: uses filelock + atomic write.
    Returns count of entries pruned.
    """
    if not PENDING_DIR.exists():
        return 0
    pending_path = PENDING_DIR / "LEARNED_pending.md"
    lock_path = PENDING_DIR / "LEARNED_pending.lock"
    if not pending_path.exists():
        return 0

    ARCHIVED_DIR.mkdir(exist_ok=True)
    import filelock
    lock = filelock.FileLock(str(lock_path), timeout=10)
    with lock:
        content = pending_path.read_text()
        lines = content.splitlines()
        cutoff = datetime.now() - timedelta(days=MAX_PENDING_AGE_DAYS)
        kept = []
        expired = []

        for i, line in enumerate(lines):
            if line.startswith("## ["):
                # Extract date from "## [YYYY-MM-DD]"
                m = re.search(r"\[(\d{4}-\d{2}-\d{2})\]", line)
                if m:
                    try:
                        entry_date = datetime.strptime(m.group(1), "%Y-%m-%d")
                        if entry_date < cutoff:
                            # Collect all lines of this entry
                            j = i
                            while j < len(lines) and not (j > i and lines[j].startswith("## [")):
                                j += 1
                            expired.append("\n".join(lines[i:j]))
                            continue
                    except ValueError:
                        pass
            kept.append(line)

        if expired:
            # Archive expired entries (not critical — no filelock needed)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = ARCHIVED_DIR / f"LEARNED_pending_expired_{ts}.md"
            _atomic_write(archive_path, "\n".join(expired))
            _atomic_write(pending_path, "\n".join(kept))
            logger.info(f"Dream Cycle: archived {len(expired)} expired LEARNED pending entries")

    return len(expired)


# ── Main Dream Cycle ────────────────────────────────────────────────────────

def dream_cycle(json_output: bool = True) -> dict | str:
    """
    Execute a full Dream Cycle with AI-powered analysis.

    5-phase pipeline:
      1. AI_ANALYZE  — call Claude Opus API on pre-filtered session logs
      2. FILTER      — pre-filter noise before sending to AI
      3. SYNTHESIZE  — write decision-tree cookbooks
      4. SUGGEST     — write LEARNED_pending.md drafts for human approval
      5. ARCHIVE/PRUNE — compress logs + standard retention cleanup

    Args:
        json_output: if True (default), returns a JSON string (for CLI output).
                     if False, returns a dict (for programmatic use).
    """
    import filelock as _filelock
    lock = _get_dream_lock()
    acquired = False
    try:
        acquired = lock.acquire(timeout=0)  # non-blocking — fail fast if already running
        if not acquired:
            result = {"status": "skipped", "reason": "dream cycle already running in another process"}
            return json.dumps(result) if json_output else result

        _DREAM_SENTINEL.write_text(datetime.now().isoformat())
        result = _dream_cycle_inner()
        return json.dumps(result) if json_output else result
    finally:
        if acquired:
            try:
                _DREAM_SENTINEL.unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"Dream Cycle: failed to remove sentinel — {e}")
            try:
                lock.release()
            except Exception:
                pass


def _dream_cycle_inner() -> dict:
    """
    Inner dream cycle logic (called within re-entrancy guard).

    3-tier memory management:
      SHORT  (active log): today's YYYY-MM-DD.md — kept live, never auto-deleted
      MID   (cookbooks):   AI-synthesized decision-tree cookbooks in cookbooks/
      LONG  (archived):   Old YYYY-MM-DD.md → archived/ with 7-day retention
    """
    ARCHIVED_DIR.mkdir(exist_ok=True)
    COOKBOOKS_DIR.mkdir(exist_ok=True)
    PENDING_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    cookbooks_written = []

    # ── Phase 1 & 2: Pre-filter + AI Analyze ────────────────────────────────
    # Read logs from last 3 days
    logs_by_date: dict[str, str] = {}
    for n_days in range(3):
        log_date = (now - timedelta(days=n_days)).strftime("%Y-%m-%d")
        log_file = MEMORY_DIR / f"{log_date}.md"
        if log_file.exists():
            try:
                logs_by_date[log_date] = log_file.read_text()
            except Exception:
                pass

    # Pre-filter each log
    filtered_by_date: dict[str, tuple[str, dict]] = {}
    for date, content in logs_by_date.items():
        filtered, stats = _pre_filter(content)
        filtered_by_date[date] = (filtered, stats)

    # Read existing LEARNED.md for dedup (search only, not in prompt)
    learned_path = MEMORY_DIR / "LEARNED.md"
    existing_learned = learned_path.read_text() if learned_path.exists() else ""

    # Call AI on each day's filtered log (falls back to rule-based if AI unavailable)
    all_sig_events: list[dict] = []
    all_cookbook_sections: list[dict] = []
    all_learned_drafts: list[dict] = []
    ai_errors: list[str] = []
    used_ai = False

    for date, (filtered, stats) in filtered_by_date.items():
        if not filtered.strip():
            continue

        ai_result = _call_claude_analysis(filtered, learned_content=existing_learned)

        if ai_result.get("status") == "error":
            # ── AI fallback: use rule-based distill ───────────────────────────
            # This runs WITHOUT ANTHROPIC_API_KEY. Extracts error/decision/pattern
            # signals using regex heuristics. Cookbooks still get written.
            ai_errors.append(f"{date}: {ai_result.get('message', 'unknown')} — using rule-based distill")
            fallback = _rule_based_distill({date: (filtered, stats)})
            ai_result = fallback
            used_ai = False
        else:
            used_ai = True

        # Write cookbook for this day
        log_name = date
        written = _write_cookbook(log_name, ai_result, timestamp)
        cookbooks_written.extend(written)

        # Collect for global pending entries
        for draft in ai_result.get("learned_drafts", []):
            draft["_date"] = date
            all_learned_drafts.append(draft)
        for section in ai_result.get("cookbook_sections", []):
            section["_date"] = date
            all_cookbook_sections.append(section)
        for event in ai_result.get("significant_events", []):
            event["_date"] = date
            all_sig_events.append(event)

    # ── Phase 3: Write LEARNED pending drafts ──────────────────────────────
    pending_count = _write_learned_pending(all_learned_drafts)

    # ── Phase 4: Prune expired pending entries ────────────────────────────
    expired_count = _prune_expired_pending()

    # ── Phase 5: Archive old logs + multi-layer retention ─────────────────
    archived_count = 0
    archived_files = []
    pruned_files = []   # initialized outside guard for return statement access

    # Test guard: skip all disk writes during pytest to avoid polluting
    # the real system archived/ directory. Tests set NEUTRON_DREAM_TEST=1.
    if _IS_TEST_MODE:
        logger.info("Dream Cycle: TEST MODE — skipping archive/prune writes")
        retention_deleted = 0
        cookbook_count_deleted = 0
    else:
        for log in MEMORY_DIR.iterdir():
            if not (log.is_file() and log.suffix == ".md"):
                continue
            if log.name.startswith(".dream_active"):
                continue
            if log.name.startswith("LEARNED"):  # permanent file — never archive
                continue
            if log.name.startswith(today_str):
                # Today's log — enforce hard cap on size
                try:
                    line_count = sum(1 for _ in log.open())
                    if line_count > MAX_SESSION_LOG_LINES:
                        dest = ARCHIVED_DIR / f"{log.stem}_{timestamp}{log.suffix}"
                        shutil.copy2(log, dest)
                        archived_files.append(f"{log.name} ({line_count} lines → capped)")
                        archived_count += 1
                        lines = log.read_text().splitlines()
                        trimmed = "\n".join(lines[-MAX_SESSION_LOG_LINES:]) + "\n"
                        # Atomic write: temp file + fsync + rename (prevents crash corruption)
                        _atomic_write(log, trimmed)
                        archived_files.append(f"  -> {log.name} truncated to {MAX_SESSION_LOG_LINES} lines")
                except Exception as e:
                    logger.warning(f"Dream Cycle: could not process oversized log {log}: {e}")
                continue
            # Archive old logs (past days)
            dest = ARCHIVED_DIR / f"{log.stem}_{timestamp}{log.suffix}"
            shutil.copy2(log, dest)
            archived_files.append(log.name)
            archived_count += 1

        # Prune old .tmp/.cache noise files
        cutoff = now - timedelta(days=NOISE_THRESHOLD_DAYS)
        pruned_files = []
        for item in list(MEMORY_DIR.iterdir()) + list(ARCHIVED_DIR.iterdir()):
            if item.name in ("archived", "cookbooks", "pending", ".dream_active"):
                continue
            if item.is_file() and item.suffix in (".tmp", ".cache"):
                try:
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    if mtime < cutoff:
                        item.unlink()
                        pruned_files.append(item.name)
                except Exception:
                    pass

        # Layer 1: Time-based retention (age cap)
        archived_cutoff = now - timedelta(days=ARCHIVED_RETENTION_DAYS)
        retention_deleted = 0
        for archived_file in sorted(ARCHIVED_DIR.iterdir(), key=lambda f: f.stat().st_mtime):
            try:
                mtime = datetime.fromtimestamp(archived_file.stat().st_mtime)
                if mtime < archived_cutoff:
                    archived_file.unlink()
                    retention_deleted += 1
            except Exception:
                pass

        # Layer 2: Count-based retention (hard cap — delete oldest)
        all_archived = sorted(ARCHIVED_DIR.iterdir(), key=lambda f: f.stat().st_mtime)
        count_deleted = 0
        while len(all_archived) > MAX_ARCHIVED_COUNT:
            oldest = all_archived.pop(0)
            try:
                oldest.unlink()
                count_deleted += 1
            except Exception:
                pass
        retention_deleted += count_deleted

        # Layer 3: Cap cookbooks/ (keep only N most recent)
        cookbook_count_deleted = 0
        if COOKBOOKS_DIR.exists():
            cookbooks = sorted(COOKBOOKS_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
            for old_cbk in cookbooks[MAX_COOKBOOKS:]:
                try:
                    old_cbk.unlink()
                    cookbook_count_deleted += 1
                except Exception:
                    pass

    # Stop observer during dream cycle
    try:
        SilentObserver.stop(str(NEUTRON_ROOT))
    except Exception:
        pass

    # Update last_dream timestamp in skill metadata (best-effort)
    try:
        _update_last_dream_timestamp()
    except Exception:
        pass

    return {
        "status": "dream_complete",
        "timestamp": timestamp,
        "archived": archived_count,
        "archived_files": archived_files,
        "pruned": len(pruned_files),
        "pruned_files": pruned_files,
        "cookbooks_written": len(cookbooks_written),
        "cookbooks": cookbooks_written,
        "pending_entries": pending_count,
        "expired_pending": expired_count,
        "retention_deleted": retention_deleted,
        "cookbooks_pruned": cookbook_count_deleted,
        "significant_events": len(all_sig_events),
        "cookbook_patterns": len(all_cookbook_sections),
        "ai_errors": ai_errors,
        "used_ai": used_ai,
    }


def _update_last_dream_timestamp() -> None:
    """
    Write today's date as last_dream in all core skill SKILL.md frontmatters.
    This makes last_dream observable so agents can see when Dream Cycle last ran.
    """
    from engine._atomic import atomic_write
    today = datetime.now().date().isoformat()
    skills_dir = NEUTRON_ROOT / "skills"

    for skill_md in skills_dir.glob("core/*/SKILL.md"):
        try:
            content = skill_md.read_text()
            if "last_dream:" in content:
                # Replace "last_dream: null" with actual date, or append if missing
                if "last_dream: null" in content:
                    new_content = content.replace("last_dream: null",
                        f"last_dream: {today}")
                elif re.search(r"^last_dream:\s*\d{4}-\d{2}-\d{2}", content, re.MULTILINE):
                    new_content = re.sub(
                        r"^last_dream:\s*\d{4}-\d{2}-\d{2}",
                        f"last_dream: {today}",
                        content, count=1, flags=re.MULTILINE)
                else:
                    continue  # No last_dream field at all
                atomic_write(skill_md, new_content)
        except Exception:
            pass  # Best-effort: never crash Dream Cycle on metadata update
