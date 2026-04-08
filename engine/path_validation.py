"""
NEUTRON EVO OS — Path Validation Utility
Provides project-boundary enforcement for all file operations.

Usage:
    from engine.path_validation import enforce_boundary

    # In any skill that reads/writes files:
    enforce_boundary("Read", filepath)

    # In checkpoint, memory, context skills:
    enforce_boundary("Write", filepath)

    # For MCP tools that spawn agents:
    enforce_boundary("spawn_cwd", cwd)

Boundary rule:
    All file operations MUST stay within the active project root (CWD).
    Cross-project reads must use NEUTRON MCP tools (neutron_memory, neutron_checkpoint).
"""

from pathlib import Path
import os
import re

# ── Config ────────────────────────────────────────────────────────────────────

def get_project_root() -> Path:
    """
    Returns the active project root.
    Prefers CWD if it exists and is accessible, else NEUTRON_ROOT.
    """
    cwd = os.getcwd()
    if cwd and os.path.isdir(cwd):
        return Path(cwd).resolve()
    neutron_root = os.environ.get("NEUTRON_ROOT", "")
    if neutron_root and os.path.isdir(neutron_root):
        return Path(neutron_root).resolve()
    # Fallback to this file's grandparent (engine/ → project root)
    return Path(__file__).parent.parent.resolve()


def get_neutron_root() -> Path:
    """Returns NEUTRON_ROOT (the NEUTRON EVO OS installation path)."""
    root = os.environ.get("NEUTRON_ROOT", "")
    if root and os.path.isdir(root):
        return Path(root).resolve()
    # Fallback to parent of engine/
    return Path(__file__).parent.parent.resolve()


# ── Core validation ───────────────────────────────────────────────────────────

def validate_path(path: str) -> Path:
    """
    Resolves path safely. Returns a resolved Path object.
    Raises ValueError on injection attempts (path starting with -, etc.).
    """
    if not path:
        return Path.cwd().resolve()

    p = Path(path)

    # Block paths that start with dash (shell option injection)
    if path.strip().startswith("-"):
        raise ValueError(f"Path injection blocked: '{path}'")

    return p.resolve()


def is_within(root: Path, target: Path) -> bool:
    """
    Returns True if `target` is inside `root` (or equal to it).
    Both paths must be resolved/absolute.
    """
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def is_glob_pattern(path: str) -> bool:
    """
    Returns True if path looks like a glob pattern rather than a file path.
    Glob indicators: *, ?, [ (except in escape sequences \\[, and GitHub URLs [...]).
    """
    # Strip escaped glob chars (e.g. \\[ in bash)
    cleaned = re.sub(r'\\(\[|\])', r'\1', path)
    # GitHub-style URLs have [sha], not glob patterns
    if re.search(r'https?://', cleaned):
        return False
    return bool(re.search(r'[\*\?\[]', cleaned))


def is_under_neutron_root(path: str) -> bool:
    """
    Returns True if path is inside NEUTRON_ROOT (not the project root).
    NEUTRON's own files (engine/, skills/, hooks/) are always readable.
    """
    nr = get_neutron_root()
    try:
        p = Path(path).resolve()
        p.relative_to(nr)
        return True
    except ValueError:
        return False


# ── Enforcement ──────────────────────────────────────────────────────────────

class BoundaryViolation(Exception):
    """Raised when a file operation escapes the project directory."""

    def __init__(self, operation: str, path: str, project_root: Path, reason: str = ""):
        self.operation = operation
        self.path = path
        self.project_root = project_root
        self.reason = reason
        super().__init__(
            f"SECURITY: {operation} blocked — path '{path}' is outside "
            f"project root '{project_root}'"
            + (f" ({reason})" if reason else "")
        )


def enforce_boundary(
    operation: str,
    path: str,
    *,
    project_root: Path | None = None,
    allow_neutron_root: bool = True,
    allow_relative: bool = True,
) -> Path:
    """
    Validates that `path` is inside the project root.

    Args:
        operation:    Name of the operation (e.g. "Read", "Write", "Glob", "spawn_cwd")
        path:         Path to validate
        project_root: Override project root. Defaults to get_project_root().
        allow_neutron_root: Also allow paths inside NEUTRON_ROOT (NEUTRON's own files).
        allow_relative: Pass True to allow relative paths (resolved against CWD).

    Returns:
        Resolved Path if valid.

    Raises:
        BoundaryViolation: If path escapes the project boundary.

    Example:
        >>> p = enforce_boundary("Read", "/mnt/data/projects/octa/memory/LEARNED.md")
        # Raises: BoundaryViolation: SECURITY: Read blocked —
        #         path '/mnt/data/projects/octa/memory/LEARNED.md'
        #         is outside project root '/mnt/data/projects/ant-downloader'
    """
    root = project_root or get_project_root()

    if not path:
        raise BoundaryViolation(operation, "(empty)", root, "no path provided")

    # ── Glob patterns are always allowed (resolved by Claude Code against CWD) ──
    if is_glob_pattern(path):
        return Path(path)

    # ── Resolve path ───────────────────────────────────────────────────────────
    try:
        if allow_relative and not Path(path).is_absolute():
            # Relative path: resolve against project root
            resolved = (root / path).resolve()
        else:
            resolved = validate_path(path)
    except ValueError as e:
        raise BoundaryViolation(operation, path, root, str(e)) from e

    # ── Allow: inside project root ────────────────────────────────────────────
    if is_within(root, resolved):
        return resolved

    # ── Allow: inside NEUTRON_ROOT (NEUTRON's own files) ───────────────────────
    if allow_neutron_root and is_under_neutron_root(resolved):
        return resolved

    # ── BLOCK ───────────────────────────────────────────────────────────────────
    raise BoundaryViolation(operation, str(resolved), root)


def check_boundary(operation: str, path: str) -> tuple[bool, str]:
    """
    Non-throwing boundary check. Returns (allowed, reason).

    Example:
        >>> allowed, reason = check_boundary("Read", "/some/path/file.py")
        >>> if not allowed:
        ...     print(f"Blocked: {reason}")
    """
    try:
        enforce_boundary(operation, path)
        return True, "ok"
    except BoundaryViolation as e:
        return False, str(e)


# ── CLI utility ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: path_validation.py <operation> <path>")
        sys.exit(1)

    op, path = sys.argv[1], sys.argv[2]

    try:
        resolved = enforce_boundary(op, path)
        print(f"OK: {resolved}")
        sys.exit(0)
    except BoundaryViolation as e:
        print(f"BLOCKED: {e}")
        sys.exit(1)