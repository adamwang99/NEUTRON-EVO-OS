"""
NEUTRON-EVO-OS: Dream Engine — Memory 2.0 Core
Implements Pruning (delete noise) and Distillation (compress logs into Cookbooks).
"""
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta

MEMORY_DIR = Path(__file__).parent.parent / "memory"
ARCHIVED_DIR = MEMORY_DIR / "archived"
COOKBOOKS_DIR = MEMORY_DIR / "cookbooks"
NOISE_THRESHOLD_DAYS = 3  # days old without reference


def dream_cycle() -> dict:
    """
    Execute a full Dream Cycle:
    1. Archive today's logs to /memory/archived/
    2. Prune noise (files not referenced in N days)
    3. Distill remaining logs into Cookbooks

    Returns: {status, timestamp, archived, pruned, distilled}
    """
    from engine.smart_observer import SilentObserver

    # Ensure dirs exist
    ARCHIVED_DIR.mkdir(exist_ok=True)
    COOKBOOKS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- Archive Phase ---
    archived_count = 0
    for log in MEMORY_DIR.glob("*.log"):
        dest = ARCHIVED_DIR / f"{log.stem}_{timestamp}.log"
        shutil.copy2(log, dest)
        archived_count += 1

    # Also archive daily log if it exists
    today_log = MEMORY_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    if today_log.exists():
        dest = ARCHIVED_DIR / f"{today_log.stem}_{timestamp}.md"
        shutil.copy2(today_log, dest)
        archived_count += 1

    # --- Prune Phase ---
    cutoff = datetime.now() - timedelta(days=NOISE_THRESHOLD_DAYS)
    pruned_files = []
    for item in list(MEMORY_DIR.iterdir()) + list(ARCHIVED_DIR.iterdir()):
        # Never prune user data or the archived dir itself
        if item.name == "archived" or item.name == "cookbooks":
            continue
        if item.is_file() and item.suffix in [".tmp", ".cache"]:
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            if mtime < cutoff:
                item.unlink()
                pruned_files.append(str(item))

    # --- Distill Phase ---
    distilled = []
    for log in MEMORY_DIR.glob("*.log"):
        result = distill_log(str(log))
        if result.get("status") == "distilled":
            distilled.append(result["cookbook"])

    # Stop observer during dream cycle (avoid re-trigger)
    try:
        SilentObserver.stop()
    except Exception:
        pass

    # Restart observer after cycle
    def _restart():
        from engine.smart_observer import SilentObserver
        from engine import expert_skill_router  # noqa: F401

        def _dream_wrapper(changes):
            dream_cycle()

        SilentObserver.start(".", _dream_wrapper, debounce_seconds=30)

    import threading
    threading.Thread(target=_restart, daemon=True).start()

    return {
        "status": "dream_complete",
        "timestamp": timestamp,
        "archived": archived_count,
        "pruned": len(pruned_files),
        "pruned_files": pruned_files,
        "distilled": len(distilled),
        "cookbooks": distilled,
    }


def distill_log(log_path: str) -> dict:
    """
    Compress a log into a Cookbook summary.
    Extracts key patterns and stores compressed version.

    Returns: {status, cookbook, entries_extracted}
    """
    path = Path(log_path)
    if not path.exists():
        return {"status": "error", "message": f"Log not found: {log_path}"}

    content = path.read_text()
    lines = [l.strip() for l in content.splitlines() if l.strip()]

    # Extract key event lines (lines with timestamps, action markers, decisions)
    key_lines = [
        l for l in lines
        if any(kw in l.lower() for kw in ["action:", "outcome:", "decision:", "##", "|", "ci delta"])
    ]

    if not key_lines:
        return {"status": "skipped", "message": "No distillable content found"}

    # Build cookbook
    cookbook_name = f"{path.stem}_cookbook.md"
    cookbook_path = COOKBOOKS_DIR / cookbook_name

    cookbook_content = [
        f"# Cookbook: {path.stem}",
        f"",
        f"> Distilled from {path.name} on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> ∫f(t)dt — Functional Credibility Over Institutional Inertia",
        f"",
        f"## Key Events ({len(key_lines)} entries)",
        f"",
    ]
    for line in key_lines[:100]:  # cap at 100 lines
        cookbook_content.append(line)

    cookbook_path.write_text("\n".join(cookbook_content))

    return {
        "status": "distilled",
        "cookbook": str(cookbook_path),
        "entries_extracted": len(key_lines),
    }


def archive_user_data(file_path: str) -> dict:
    """
    Safely archive user data to /memory/archived/.
    Returns: {status, archived_to}
    """
    path = Path(file_path)
    if not path.exists():
        return {"status": "error", "message": f"File not found: {file_path}"}

    ARCHIVED_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archived_name = f"{path.stem}_{timestamp}{path.suffix}"
    archived_path = ARCHIVED_DIR / archived_name

    shutil.copy2(path, archived_path)

    return {
        "status": "archived",
        "archived_to": str(archived_path),
        "original": str(path),
    }
