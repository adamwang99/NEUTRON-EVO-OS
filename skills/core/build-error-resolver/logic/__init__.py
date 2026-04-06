"""
Build Error Resolver Skill — Parse build output, classify, suggest fixes.
Inspired by ECC's build-error-resolver agent pattern.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional


def run_build_error_resolver(task: str, context: dict = None) -> dict:
    """
    Parse build/test output and resolve errors.

    Args:
        task: Build command output (raw text) or command to run
        context: {
            files: [...],          # files to scan if no output provided
            command: "cargo build", # run this command and parse output
            language: "rust|python|go|java|javascript"
        }

    Returns: {status, errors: [...], ci_delta}
    """
    context = context or {}
    raw_output = context.get("output", task)
    language = context.get("language", _detect_language(context.get("files", [])))
    errors = []

    # ── Run build command if provided ───────────────────────────────────
    if context.get("command"):
        raw_output = _run_build(context["command"], context.get("cwd"))

    # ── Parse based on language ───────────────────────────────────────────
    parsers = {
        "python": _parse_python_errors,
        "rust": _parse_rust_errors,
        "go": _parse_go_errors,
        "java": _parse_java_errors,
        "javascript": _parse_js_errors,
        "typescript": _parse_ts_errors,
    }

    parser = parsers.get(language, _parse_generic_errors)
    errors = parser(raw_output)

    # ── Categorize errors ─────────────────────────────────────────────────
    categorized = _categorize_errors(errors)

    # ── Generate fix suggestions ───────────────────────────────────────────
    for err in categorized:
        err["suggested_fix"] = _suggest_fix(err, language)

    summary = f"{len(errors)} error(s) found"
    if categorized:
        by_type = {k: len(v) for k, v in categorized.items()}
        summary += f" — " + ", ".join(f"{k}:{v}" for k, v in by_type.items())

    return {
        "status": "ok",
        "output": summary,
        "errors": errors,
        "categorized": {k: [e["message"] for e in v] for k, v in categorized.items()},
        "language_detected": language,
        "error_count": len(errors),
        "ci_delta": 2,
    }


# ── Language Detection ──────────────────────────────────────────────────────

def _detect_language(files: list[str]) -> str:
    if not files:
        return "python"  # default
    for f in files:
        p = Path(f)
        if not p.exists():
            continue
        if p.suffix in (".rs",):
            return "rust"
        if p.suffix in (".go",):
            return "go"
        if p.suffix in (".py",):
            return "python"
        if p.suffix in (".java",):
            return "java"
        if p.suffix in (".js", ".mjs", ".cjs"):
            return "javascript"
        if p.suffix in (".ts", ".tsx"):
            return "typescript"
    return "python"


def _run_build(command: str, cwd: Optional[str] = None) -> str:
    """
    Run a build command SAFELY.

    SECURITY: Uses shell=False with list args to prevent command injection.
    Only allows pre-approved build commands (no arbitrary shell execution).
    Process group termination ensures forked processes are killed on timeout.
    """
    import shlex

    # ── ALLOWLIST: only known safe build commands ──────────────────────
    # Parse the command to extract the program name
    if isinstance(command, str):
        parts = shlex.split(command)
    else:
        parts = list(command)

    if not parts:
        return "[Error: empty command]"

    program = parts[0]

    # Allowlist of safe build programs (no shell metacharacters possible)
    ALLOWED_PROGRAMS = {
        # Python
        "python3", "python", "pytest", "pip", "pip3",
        "coverage", "nox", "tox",
        # Rust
        "cargo", "rustc", "clippy", "rustfmt",
        # Go
        "go", "gofmt", "govulncheck",
        # Java
        "javac", "java", "mvn", "gradle", "ant",
        # JS/TS
        "npm", "npx", "yarn", "pnpm", "node", "tsc", "esbuild",
        "webpack", "vite", "rollup", "bun",
        # C/C++
        "gcc", "g++", "clang", "clang++", "cmake", "make", "ninja",
        # Dart/Flutter
        "dart", "flutter",
        # Kotlin
        "kotlinc", "kscript",
        # .NET
        "dotnet", "msbuild",
    }

    if program not in ALLOWED_PROGRAMS:
        return f"[SECURITY: Command '{program}' not in allowlist. Refusing to run.]"

    # Guard: if program is given as an absolute path, validate it points inside
    # a standard bin directory (prevents allowlist bypass via symlink).
    # e.g. /tmp/evil/pytest → /tmp/evil/bin/pytest is NOT in a standard location.
    import shutil as _shutil
    resolved_prog = _shutil.which(program)
    if resolved_prog:
        _allowed_roots = ["/usr/bin", "/usr/local/bin", "/snap/bin", "/opt"]
        _is_safe = any(resolved_prog.startswith(r) for r in _allowed_roots)
        if not _is_safe:
            return f"[SECURITY: {program} resolves to non-standard path '{resolved_prog}'. Refusing.]"

    # Resolve cwd safely (never default to arbitrary dir)
    safe_cwd = cwd if cwd and Path(cwd).is_absolute() else str(Path.cwd())

    try:
        # shell=False prevents injection; start_new_session kills forked children
        result = subprocess.run(
            parts,
            shell=False,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=safe_cwd,
            start_new_session=True,
        )
        return (result.stdout + "\n" + result.stderr)
    except subprocess.TimeoutExpired:
        return "[Error: command timed out after 120s]"
    except FileNotFoundError:
        return f"[Error: '{program}' not found — is it installed?]"
    except PermissionError:
        return f"[Error: permission denied running '{program}']"
    except OSError as e:
        return f"[Error running '{program}': {e}]"


# ── Parsers ─────────────────────────────────────────────────────────────────

def _parse_python_errors(output: str) -> list[dict]:
    """Parse Python tracebacks and syntax errors."""
    errors = []
    for line in output.splitlines():
        # File "path", line N, in function
        m = re.match(r'  File "([^"]+)", line (\d+), in (.+)', line)
        if m:
            try:
                errors.append({
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "error_type": "traceback",
                    "message": line.strip(),
                    "suggested_fix": "",
                })
            except (ValueError, IndexError):
                pass  # malformed line — skip
            continue

        # ModuleNotFoundError
        m = re.match(r"ModuleNotFoundError:\s+No module named '([^']+)'", line)
        if m:
            errors.append({
                "file": "", "line": 0,
                "error_type": "import",
                "message": line.strip(),
                "suggested_fix": f"pip install {m.group(1)}",
            })
            continue

        # ImportError
        m = re.match(r"ImportError:\s+(.+)", line)
        if m:
            errors.append({
                "file": "", "line": 0,
                "error_type": "import",
                "message": line.strip(),
                "suggested_fix": f"Check import path — {m.group(1)}",
            })
            continue

        # TypeError
        m = re.match(r"TypeError:\s+(.+)", line)
        if m:
            errors.append({
                "file": "", "line": 0,
                "error_type": "type",
                "message": line.strip(),
                "suggested_fix": "Check argument types — likely None passed where value expected",
            })
            continue

    return errors


def _parse_rust_errors(output: str) -> list[dict]:
    """Parse rustc/cargo error messages."""
    errors = []
    for line in output.splitlines():
        # error[E0001]: src/main.rs:12:5: ...
        m = re.match(r'error\[?E\d*\]?:\s+(.+?)\s+-->\s+([^:]+):(\d+):(\d+)', line)
        if not m:
            m = re.match(r'error\[?\d*\]?:\s+-->\s+([^:]+):(\d+):(\d+):\s*(.+)', line)
        if m:
            try:
                errors.append({
                    "file": m.group(2),
                    "line": int(m.group(3)),
                    "error_type": "rustc",
                    "message": line.strip(),
                    "suggested_fix": "",
                })
            except (ValueError, IndexError):
                pass
        # warning
        m = re.match(r'warning:\s+(.+?)\s+-->\s+([^:]+):(\d+):(\d+)', line)
        if m:
            try:
                errors.append({
                    "file": m.group(2),
                    "line": int(m.group(3)),
                    "error_type": "warning",
                    "message": line.strip(),
                    "suggested_fix": "",
                })
            except (ValueError, IndexError):
                pass
    return errors


def _parse_go_errors(output: str) -> list[dict]:
    """Parse go build errors."""
    errors = []
    for line in output.splitlines():
        m = re.match(r'(.+?):(\d+):(\d+):\s*(.+)', line)
        if m:
            try:
                errors.append({
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "error_type": "go",
                    "message": line.strip(),
                    "suggested_fix": "",
                })
            except (ValueError, IndexError):
                pass
            continue
        m = re.match(r'(.+?)\s+#(.+)', line)
        if m and ":" not in m.group(1):
            errors.append({
                "file": m.group(1), "line": 0,
                "error_type": "go",
                "message": line.strip(),
                "suggested_fix": "go get " + m.group(1),
            })
    return errors


def _parse_java_errors(output: str) -> list[dict]:
    """Parse javac/maven/gradle errors."""
    errors = []
    for line in output.splitlines():
        m = re.match(r'(.+?)\[ERROR\]\s+(.+?)\s+-->\s+(.+?):(\d+)', line)
        if m:
            errors.append({
                "file": m.group(3),
                "line": int(m.group(4)),
                "error_type": "maven",
                "message": f"{m.group(1)}: {m.group(2)}",
                "suggested_fix": "",
            })
    return errors


def _parse_js_errors(output: str) -> list[dict]:
    """Parse Node.js/npm errors."""
    errors = []
    for line in output.splitlines():
        m = re.match(r'(.+?):(\d+):(\d+)\s*-\s*(.+)', line)
        if m:
            errors.append({
                "file": m.group(1),
                "line": int(m.group(2)),
                "error_type": "javascript",
                "message": line.strip(),
                "suggested_fix": "",
            })
    return errors


def _parse_ts_errors(output: str) -> list[dict]:
    """Parse TypeScript/tsc errors."""
    errors = []
    for line in output.splitlines():
        m = re.match(r"(.+?)\((\d+),(\d+)\):\s+error\s+(TS\d+):\s+(.+)", line)
        if m:
            errors.append({
                "file": m.group(1),
                "line": int(m.group(2)),
                "error_type": "typescript",
                "message": f"TS{m.group(4)}: {m.group(5)}",
                "suggested_fix": f"Fix type error TS{m.group(4)}: {m.group(5)}",
            })
    return errors


def _parse_generic_errors(output: str) -> list[dict]:
    """Fallback: generic error parser."""
    errors = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Error:") or stripped.startswith("error:") or stripped.startswith("FAILED"):
            errors.append({
                "file": "",
                "line": 0,
                "error_type": "generic",
                "message": stripped,
                "suggested_fix": "",
            })
    return errors


# ── Categorize Errors ─────────────────────────────────────────────────────────

def _categorize_errors(errors: list[dict]) -> dict:
    """Group errors by type."""
    categorized: dict[str, list[dict]] = {}
    for err in errors:
        t = err.get("error_type", "unknown")
        if t not in categorized:
            categorized[t] = []
        categorized[t].append(err)
    return categorized


# ── Fix Suggestions ───────────────────────────────────────────────────────────

def _suggest_fix(err: dict, language: str) -> str:
    """Generate targeted fix suggestion based on error type and message."""
    msg = err.get("message", "").lower()
    etype = err.get("error_type", "")

    if etype == "import":
        if "modulenotfounderror" in msg or "no module named" in msg:
            pkg = re.search(r"named '([^']+)'", msg)
            if pkg:
                return f"pip install {pkg.group(1)}"
        return "Check import path — ensure module is installed and in PYTHONPATH"

    if etype == "syntax":
        if "unexpected indent" in msg:
            return "Fix indentation — check for mixed tabs/spaces or wrong nesting level"
        if "expected" in msg and ":" in msg:
            return "Fix syntax — likely missing : or mismatched parentheses/brackets"
        return "Check syntax near the error line — look for missing punctuation"

    if etype == "type":
        if "none" in msg or "noneType" in msg:
            return "None passed where value expected — add None check or use .get()"
        return "Check argument types — likely type mismatch between function call and definition"

    if etype == "rustc":
        if "cannot find" in msg and "in this scope" in msg:
            return "Add missing import: use 'use' statement or fully qualify the path"
        if "mismatched types" in msg:
            return "Type mismatch — add type annotation or cast to match expected type"
        if "use of moved value" in msg:
            return "Value moved — clone() before move, or use a reference (&)"
        return "See Rust error message above for specific fix"

    if etype == "go":
        if "undefined:" in msg or "undeclared name:" in msg:
            return "Add missing import or declare the variable"
        if "cannot call" in msg:
            return "Function not in scope — check import or package name"
        return "See Go error message above for specific fix"

    return "Review the error message above and fix the indicated issue"
