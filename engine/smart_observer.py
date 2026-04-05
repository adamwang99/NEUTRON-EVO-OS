"""
NEUTRON-EVO-OS: Smart Observer
Uses watchdog to monitor source file changes.
Debounce Logic: triggers Dream Cycle only after work settles.
"""
from __future__ import annotations

import time
import logging
import threading
from pathlib import Path
from typing import Callable, Optional

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    Observer = None
    FileSystemEventHandler = object

logger = logging.getLogger("neutron-evo-os")


class DebounceHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable, debounce_seconds: int = 30):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.last_trigger = 0.0
        self.pending_changes: list[tuple[float, str]] = []
        self._lock = threading.Lock()

    def on_modified(self, event):
        if event.is_directory:
            return
        with self._lock:
            self.pending_changes.append((time.time(), event.src_path))
            self._check_debounce()

    def on_created(self, event):
        if event.is_directory:
            return
        with self._lock:
            self.pending_changes.append((time.time(), event.src_path))
            self._check_debounce()

    def on_deleted(self, event):
        if event.is_directory:
            return
        with self._lock:
            self.pending_changes.append((time.time(), event.src_path))
            self._check_debounce()

    def _check_debounce(self):
        now = time.time()
        # Only fire if the oldest pending change is older than debounce window
        if self.pending_changes:
            oldest = min(t for t, _ in self.pending_changes)
            if now - oldest >= self.debounce_seconds:
                changes = list(self.pending_changes)
                self.pending_changes = []
                try:
                    self.callback(changes)
                except Exception as e:
                    logger.error(f"Dream Cycle callback failed: {e}")


def start_observer(
    root_path: str,
    callback: Callable,
    debounce_seconds: int = 30,
    recursive: bool = True,
) -> Optional["Observer"]:
    """
    Start watching root_path for changes.
    Debounces: only fires callback after debounce_seconds of silence.
    Returns the Observer instance (caller should .start() it).
    """
    if Observer is None:
        raise ImportError("watchdog is required: pip install watchdog>=3.0.0")

    observer = Observer()
    handler = DebounceHandler(callback, debounce_seconds)
    observer.schedule(handler, str(root_path), recursive=recursive)
    return observer


class SilentObserver:
    """
    Non-blocking observer runner for use in background threads.
    Start with: SilentObserver.start(root_path, callback) — returns immediately.
    Stop with:  SilentObserver.stop(root_path)           — only stops matching root.

    Scope-safe: stop() requires the exact root_path that was used to start.
    Calling stop() from project A will NOT affect an observer started by project B.
    """

    _lock = threading.Lock()
    _thread: Optional[threading.Thread] = None
    _observer: Optional["Observer"] = None
    _running = False
    _root: Optional[str] = None   # track which root this observer watches

    @classmethod
    def start(
        cls,
        root_path: str,
        callback: Callable,
        debounce_seconds: int = 30,
    ):
        """Start observer in a background daemon thread. Thread-safe."""
        with cls._lock:
            if cls._running:
                logger.warning("Observer already running. Call .stop() first.")
                return

            def run():
                try:
                    observer = start_observer(root_path, callback, debounce_seconds)
                    # Set _running=True BEFORE starting the observer (inside the lock)
                    # so that stop() will correctly see it and stop the observer.
                    # Without this, there's a race window between observer.start() and
                    # _running=True where stop() returns without doing anything.
                    with cls._lock:
                        cls._observer = observer
                        cls._running = True
                        cls._root = root_path
                    observer.start()
                    logger.info(f"[NEUTRON-EVO-OS] Observer started on {root_path}")
                    while True:
                        with cls._lock:
                            if not cls._running:
                                break
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"Observer error: {e}")
                finally:
                    with cls._lock:
                        cls._running = False
                        cls._root = None
                        if cls._observer:
                            try:
                                cls._observer.stop()
                            except Exception:
                                pass
                            cls._observer = None

            cls._thread = threading.Thread(target=run, daemon=True)
            cls._thread.start()

    @classmethod
    def stop(cls, root: str = None):
        """
        Stop the observer gracefully. Thread-safe and scope-safe.

        Args:
            root: If provided, only stops the observer if it was started on this exact
                  root path. Prevents stopping observers belonging to sibling projects.
                  If None, stops any running observer (legacy compatibility).
        """
        with cls._lock:
            if not cls._running:
                return
            # Scope guard: reject stopping if a different root is running
            if root is not None and cls._root is not None and cls._root != root:
                logger.warning(
                    f"[NEUTRON-EVO-OS] Refused stop(): observer is watching '{cls._root}', "
                    f"not '{root}'. Use the same root to stop."
                )
                return
            cls._running = False
            obs = cls._observer
        # Stop outside lock to avoid deadlock
        if obs:
            try:
                obs.stop()
            except Exception:
                pass
        with cls._lock:
            cls._thread = None
            cls._observer = None
            cls._root = None
        logger.info("[NEUTRON-EVO-OS] Observer stopped")
