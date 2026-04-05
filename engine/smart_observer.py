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

    # Instance state — each instance has its own observer thread
    _lock: threading.Lock
    _thread: Optional[threading.Thread]
    _observer: Optional["Observer"]
    _running: bool
    _root: Optional[str]

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._observer: Optional["Observer"] = None
        self._running = False
        self._root: Optional[str] = None

    def start(
        self,
        root_path: str,
        callback: Callable,
        debounce_seconds: int = 30,
    ):
        """Start observer in a background daemon thread. Thread-safe."""
        with self._lock:
            if self._running:
                logger.warning("Observer already running. Call .stop() first.")
                return

            def run():
                try:
                    observer = start_observer(root_path, callback, debounce_seconds)
                    # Set _running=True BEFORE starting the observer (inside the lock)
                    # so that stop() will correctly see it and stop the observer.
                    with self._lock:
                        self._observer = observer
                        self._running = True
                        self._root = root_path
                    observer.start()
                    logger.info(f"[NEUTRON-EVO-OS] Observer started on {root_path}")
                    while True:
                        with self._lock:
                            if not self._running:
                                break
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"Observer error: {e}")
                finally:
                    with self._lock:
                        self._running = False
                        self._root = None
                        if self._observer:
                            try:
                                self._observer.stop()
                            except Exception:
                                pass
                            self._observer = None

            self._thread = threading.Thread(target=run, daemon=True)
            self._thread.start()

    def stop(self, root: str = None):
        """
        Stop the observer gracefully. Thread-safe and scope-safe.

        Args:
            root: If provided, only stops the observer if it was started on this exact
                  root path. Prevents stopping observers belonging to sibling projects.
                  If None, stops any running observer (legacy compatibility).
        """
        with self._lock:
            if not self._running:
                return
            # Scope guard: reject stopping if a different root is running
            if root is not None and self._root is not None and self._root != root:
                logger.warning(
                    f"[NEUTRON-EVO-OS] Refused stop(): observer is watching '{self._root}', "
                    f"not '{root}'. Use the same root to stop."
                )
                return
            self._running = False
            obs = self._observer
        # Stop outside lock to avoid deadlock
        if obs:
            try:
                obs.stop()
            except Exception:
                pass
        with self._lock:
            self._thread = None
            self._observer = None
            self._root = None
        logger.info("[NEUTRON-EVO-OS] Observer stopped")


# ─── Backward-compatible module-level singleton ─────────────────────────────────
# Old code calls: SilentObserver.start(root, callback)
# We provide a proxy that delegates to the single _impl instance.
# This preserves the class-method calling convention.
_impl = SilentObserver()


class _SilentObserverCompat:
    """Proxy class — delegates all .start()/.stop() calls to the global _impl singleton."""
    def start(self, *args, **kwargs):
        return _impl.start(*args, **kwargs)

    def stop(self, *args, **kwargs):
        return _impl.stop(*args, **kwargs)


SilentObserver = _SilentObserverCompat()
