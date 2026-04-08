"""
Build Error Resolver Skill — Parse build output, classify, suggest + apply fixes.
Inspired by ECC's build-error-resolver agent pattern.

Auto-fix confidence tiers:
  HIGH (>=0.9)  : pip install, undefined function → stub, missing import → add
  MEDIUM (0.6-0.9): syntax errors, type errors (dry-run preview)
  LOW  (<0.6)   : complex errors → suggest only

Auto-apply: Only when context["auto_fix"]=True AND confidence>=0.9.
All other cases return structured "ready_to_apply" status for orchestrator.
"""
from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from typing import Optional


def run_build_error_resolver(task: str, context: dict = None) -> dict:
    """
    Parse build/test output and resolve errors.

    Args:
        task: Build command output (raw text) or command to run
        context: {
            output: "...",       # raw build output (if task is not output)
            files: [...],        # files to scan if no output provided
            command: "...",      # run this command and parse output
            language: "rust|python|go|java|javascript|typescript"
            auto_fix: bool,     # apply high-confidence fixes automatically
            orchestrator: bool, # return orchestrator-ready structured format
        }

    Returns: {
        status: "ok"|"fixed"|"blocked",
        errors: [...],
        auto_applied: [...],
        ready_to_apply: [...],
        ci_delta: int,
        orchestrator_plan: [...],  # if orchestrator=True
    }
    """
    context = context or {}
    raw_output = context.get("output", task)
    language = context.get("language", _detect_language(context.get("files", [])))
    auto_fix = context.get("auto_fix", False)
    as_orchestrator = context.get("orchestrator", False)

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

    # ── Score confidence + generate fix for each error ───────────────────
    categorized = _categorize_errors(errors)
    auto_applied = []
    ready_to_apply = []
    suggested_only = []

    for err in errors:
        fix = _generate_fix(err, language)
        err["confidence"] = fix["confidence"]
        err["fix_category"] = fix["category"]
        err["suggested_fix"] = fix["text"]

        if auto_fix and fix["confidence"] >= 0.9:
            result = _apply_fix(err, fix, language)
            if result["applied"]:
                auto_applied.append(result)
                err["status"] = "applied"
            else:
                ready_to_apply.append({"err": err, "fix": fix, "reason": result.get("reason", "")})
                err["status"] = "ready"
        elif fix["confidence"] >= 0.9:
            ready_to_apply.append({"err": err, "fix": fix})
            err["status"] = "ready"
        else:
            suggested_only.append(err)
            err["status"] = "suggested"

    # ── Build orchestrator plan if requested ─────────────────────────────
    orchestrator_plan = None
    if as_orchestrator and errors:
        units = []
        # Group by error category for parallel resolution
        categories = {}
        for err in errors:
            cat = err.get("fix_category", "unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(err)

        for cat, cat_errors in categories.items():
            unit = {
                "id": f"fix-{cat}",
                "name": f"Fix {len(cat_errors)} × {cat} error(s)",
                "scope": "fix",
                "responsibilities": [
                    f"Fix {len(cat_errors)} {cat} error(s)",
                    f"Run build to verify fix",
                ],
                "errors": cat_errors,
                "skills": ["build-error-resolver"],
            }
            units.append(unit)

        orchestrator_plan = {
            "units": units,
            "summary": f"{len(errors)} error(s) across {len(categories)} category(ies)",
            "auto_applied": len(auto_applied),
            "needs_agents": len(ready_to_apply) + len(suggested_only),
        }

    summary_parts = [f"{len(errors)} error(s) found"]
    if auto_applied:
        summary_parts.append(f"{len(auto_applied)} auto-fixed")
    if ready_to_apply:
        summary_parts.append(f"{len(ready_to_apply)} ready to apply")
    if suggested_only:
        summary_parts.append(f"{len(suggested_only)} need review")

    return {
        "status": "fixed" if auto_applied else "ok",
        "output": " — ".join(summary_parts),
        "errors": errors,
        "auto_applied": auto_applied,
        "ready_to_apply": [
            {"file": r["err"]["file"], "line": r["err"]["line"],
             "fix": r["fix"]["text"], "confidence": r["fix"]["confidence"]}
            for r in ready_to_apply
        ],
        "suggested": [{"message": e["message"], "fix": e["suggested_fix"]} for e in suggested_only],
        "categorized": {k: [e["message"] for e in v] for k, v in categorized.items()},
        "language_detected": language,
        "error_count": len(errors),
        "orchestrator_plan": orchestrator_plan,
        "ci_delta": 2 if not auto_applied else 5,
    }


# ── Confidence Scoring + Fix Generation ───────────────────────────────────────

def _generate_fix(err: dict, language: str) -> dict:
    """
    Score confidence and generate fix text.
    Returns: {confidence: float, text: str, category: str, editable: bool}
    """
    msg = err.get("message", "").lower()
    etype = err.get("error_type", "").lower()
    file = err.get("file", "")
    line = err.get("line", 0)

    # ── HIGH CONFIDENCE ──────────────────────────────────────────────────
    # ModuleNotFoundError → pip install
    if ("modulenotfounderror" in etype) or ("modulenotfounderror" in msg):
        pkg = re.search(r"named '([^']+)'", msg)
        if pkg:
            return {
                "confidence": 0.98,
                "text": f"pip install {pkg.group(1)}",
                "category": "missing-package",
                "editable": True,
                "action": "bash",
            }

    # Python: undefined name → stub function
    if language == "python" and ("nameerror" in msg or "undefined name" in msg):
        name = re.search(r"name '(\w+)' is not defined", msg)
        if name and not name.group(1).startswith("_"):
            return {
                "confidence": 0.92,
                "text": f"def {name.group(1)}(*args, **kwargs):\n    raise NotImplementedError('{name.group(1)} not yet implemented')",
                "category": "undefined-name",
                "editable": True,
                "action": "edit",
                "target": file,
                "line": line,
            }

    # Python: undefined name → class stub
    if language == "python" and re.search(r"name '\w+' is not defined", msg):
        name = re.search(r"name '(\w+)' is not defined", msg)
        if name:
            return {
                "confidence": 0.90,
                "text": f"class {name.group(1)}:\n    pass",
                "category": "undefined-name",
                "editable": True,
                "action": "edit",
                "target": file,
                "line": line,
            }

    # Missing __init__.py
    if "no attribute" in msg or "has no attribute" in msg:
        if "has no attribute '__init__'" in msg or "module has no attribute" in msg:
            return {
                "confidence": 0.88,
                "text": f"# Add __all__ to control exports\n__all__ = []",
                "category": "missing-attribute",
                "editable": True,
                "action": "edit",
                "target": file,
                "line": line,
            }

    # Go: undefined → go get
    if etype == "go" and ("undefined:" in msg or "undeclared name:" in msg):
        pkg = re.search(r'(?:undefined|undeclared):\s*(\w+)', msg)
        return {
            "confidence": 0.85,
            "text": f"go get {pkg.group(1) if pkg else '<package>'}",
            "category": "undefined-name",
            "editable": True,
            "action": "bash",
        }

    # ── MEDIUM CONFIDENCE ───────────────────────────────────────────────
    # Python syntax errors
    if etype == "syntax" or "syntaxerror" in msg:
        return {
            "confidence": 0.65,
            "text": _suggest_fix(err, language),
            "category": "syntax",
            "editable": False,
            "action": "suggest",
        }

    # Python type errors
    if etype == "type" or "typeerror" in msg:
        return {
            "confidence": 0.60,
            "text": _suggest_fix(err, language),
            "category": "type-error",
            "editable": False,
            "action": "suggest",
        }

    # Rust mismatched types
    if language == "rust" and "mismatched types" in msg:
        expected = re.search(r'expected `([^`]+)`', msg)
        found = re.search(r'found `([^`]+)`', msg)
        return {
            "confidence": 0.70,
            "text": f"Type mismatch: expected {expected.group(1) if expected else '?'}, found {found.group(1) if found else '?'}. Add type annotation or cast.",
            "category": "type-mismatch",
            "editable": False,
            "action": "suggest",
        }

    # Rust use of moved value
    if language == "rust" and "use of moved value" in msg:
        return {
            "confidence": 0.75,
            "text": "Value moved — clone() before move, or use &reference, or implement Copy trait",
            "category": "ownership",
            "editable": False,
            "action": "suggest",
        }

    # TypeScript type errors
    if etype == "typescript" and "error TS" in err.get("message", ""):
        return {
            "confidence": 0.65,
            "text": _suggest_fix(err, language),
            "category": "type-error",
            "editable": False,
            "action": "suggest",
        }

    # ── LOW CONFIDENCE ──────────────────────────────────────────────────
    return {
        "confidence": 0.30,
        "text": _suggest_fix(err, language),
        "category": etype or "unknown",
        "editable": False,
        "action": "suggest",
    }


def _apply_fix(err: dict, fix: dict, language: str) -> dict:
    """
    Apply a high-confidence fix automatically.
    Returns: {applied: bool, reason?: str, output?: str}
    """
    action = fix.get("action", "suggest")
    target = fix.get("target", "")
    text = fix.get("text", "")

    if action == "bash":
        cmd = shlex.split(text)
        if not cmd:
            return {"applied": False, "reason": "empty command"}
        try:
            result = subprocess.run(
                cmd, shell=False, capture_output=True, text=True,
                timeout=60, start_new_session=True,
            )
            success = result.returncode == 0
            output = result.stdout.strip() or result.stderr.strip()
            return {
                "applied": success,
                "reason": "ok" if success else output,
                "output": output,
                "command": text,
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"applied": False, "reason": str(e)}

    if action == "edit" and target and text:
        # Only apply Python stubs for undefined names
        if "def " in text or "class " in text:
            path = Path(target)
            if not path.exists():
                return {"applied": False, "reason": f"file not found: {target}"}
            try:
                content = path.read_text()
                lines = content.splitlines()
                insert_line = max(0, err.get("line", 1) - 1)
                # Insert after imports (last import line)
                last_import = insert_line
                for i, l in enumerate(lines):
                    stripped = l.strip()
                    if i > insert_line:
                        break
                    if stripped.startswith(("import ", "from ")):
                        last_import = i
                insert_at = last_import + 1
                lines.insert(insert_at, "")
                lines.insert(insert_at + 1, text)
                path.write_text("\n".join(lines) + "\n")
                return {
                    "applied": True,
                    "reason": "stub inserted",
                    "output": f"Inserted {text.split(chr(10))[0]} at {target}:{insert_at}",
                    "target": target,
                }
            except Exception as e:
                return {"applied": False, "reason": str(e)}

    return {"applied": False, "reason": f"action '{action}' not auto-applyable"}


# ── Original helpers (unchanged) ──────────────────────────────────────────────

def _detect_language(files: list[str]) -> str:
    if not files:
        return "python"
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
    import shutil as _shutil
    if isinstance(command, str):
        parts = shlex.split(command)
    else:
        parts = list(command)
    if not parts:
        return "[Error: empty command]"
    program = parts[0]
    ALLOWED_PROGRAMS = {
        "python3", "python", "pytest", "pip", "coverage",
        "cargo", "rustc", "clippy", "rustfmt",
        "go", "gofmt", "govulncheck",
        "javac", "java", "mvn", "gradle",
        "npm", "npx", "yarn", "pnpm", "node", "tsc", "esbuild",
        "webpack", "vite", "rollup", "bun",
        "gcc", "g++", "clang", "clang++", "cmake", "make", "ninja",
        "dart", "flutter",
        "kotlinc", "kscript",
        "dotnet", "msbuild",
    }
    if program not in ALLOWED_PROGRAMS:
        return f"[SECURITY: Command '{program}' not in allowlist. Refusing to run.]"
    resolved_prog = _shutil.which(program)
    if resolved_prog:
        _allowed_roots = ["/usr/bin", "/usr/local/bin", "/snap/bin", "/opt"]
        _is_safe = any(resolved_prog.startswith(r) for r in _allowed_roots)
        if not _is_safe:
            return f"[SECURITY: {program} resolves to non-standard path '{resolved_prog}'. Refusing.]"
    safe_cwd = cwd if cwd and Path(cwd).is_absolute() else str(Path.cwd())
    try:
        result = subprocess.run(parts, shell=False, capture_output=True, text=True,
                                timeout=120, cwd=safe_cwd, start_new_session=True)
        return (result.stdout + "\n" + result.stderr)
    except subprocess.TimeoutExpired:
        return "[Error: command timed out after 120s]"
    except FileNotFoundError:
        return f"[Error: '{program}' not found — is it installed?]"
    except PermissionError:
        return f"[Error: permission denied running '{program}']"
    except OSError as e:
        return f"[Error running '{program}': {e}]"


def _parse_python_errors(output: str) -> list[dict]:
    errors = []
    for line in output.splitlines():
        m = re.match(r'  File "([^"]+)", line (\d+), in (.+)', line)
        if m:
            try:
                errors.append({"file": m.group(1), "line": int(m.group(2)),
                               "error_type": "traceback", "message": line.strip()})
            except (ValueError, IndexError):
                pass
            continue
        m = re.match(r"(ModuleNotFoundError|ImportError|TypeError|NameError|SyntaxError"
                     r"|AttributeError|FileNotFoundError|UnicodeDecodeError"
                     r"|IndentationError):\s+(.+)", line)
        if m:
            errors.append({"file": "", "line": 0, "error_type": m.group(1).lower(),
                           "message": line.strip()})
            continue
    return errors


def _parse_rust_errors(output: str) -> list[dict]:
    errors = []
    for line in output.splitlines():
        m = re.match(r'error\[?E\d*\]?:\s+(.+?)\s+-->\s+([^:]+):(\d+):(\d+)', line)
        if not m:
            m = re.match(r'error\[?\d*\]?:\s+-->\s+([^:]+):(\d+):(\d+):\s*(.+)', line)
        if m:
            try:
                errors.append({"file": m.group(2), "line": int(m.group(3)),
                               "error_type": "rustc", "message": line.strip()})
            except (ValueError, IndexError):
                pass
        m = re.match(r'warning:\s+(.+?)\s+-->\s+([^:]+):(\d+):(\d+)', line)
        if m:
            try:
                errors.append({"file": m.group(2), "line": int(m.group(3)),
                               "error_type": "warning", "message": line.strip()})
            except (ValueError, IndexError):
                pass
    return errors


def _parse_go_errors(output: str) -> list[dict]:
    errors = []
    for line in output.splitlines():
        m = re.match(r'(.+?):(\d+):(\d+):\s*(.+)', line)
        if m:
            try:
                errors.append({"file": m.group(1), "line": int(m.group(2)),
                               "error_type": "go", "message": line.strip()})
            except (ValueError, IndexError):
                pass
            continue
        m = re.match(r'(.+?)\s+#(.+)', line)
        if m and ":" not in m.group(1):
            errors.append({"file": m.group(1), "line": 0,
                           "error_type": "go", "message": line.strip()})
    return errors


def _parse_java_errors(output: str) -> list[dict]:
    errors = []
    for line in output.splitlines():
        m = re.match(r'(.+?)\[ERROR\]\s+(.+?)\s+-->\s+(.+?):(\d+)', line)
        if m:
            errors.append({"file": m.group(3), "line": int(m.group(4)),
                           "error_type": "maven", "message": f"{m.group(1)}: {m.group(2)}"})
    return errors


def _parse_js_errors(output: str) -> list[dict]:
    errors = []
    for line in output.splitlines():
        m = re.match(r'(.+?):(\d+):(\d+)\s*-\s*(.+)', line)
        if m:
            errors.append({"file": m.group(1), "line": int(m.group(2)),
                           "error_type": "javascript", "message": line.strip()})
    return errors


def _parse_ts_errors(output: str) -> list[dict]:
    errors = []
    for line in output.splitlines():
        m = re.match(r"(.+?)\((\d+),(\d+)\):\s+error\s+(TS\d+):\s+(.+)", line)
        if m:
            errors.append({"file": m.group(1), "line": int(m.group(2)),
                           "error_type": "typescript",
                           "message": f"TS{m.group(4)}: {m.group(5)}"})
    return errors


def _parse_generic_errors(output: str) -> list[dict]:
    errors = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(("Error:", "error:", "FAILED")):
            errors.append({"file": "", "line": 0, "error_type": "generic",
                           "message": stripped})
    return errors


def _categorize_errors(errors: list[dict]) -> dict:
    categorized: dict = {}
    for err in errors:
        t = err.get("error_type", "unknown")
        if t not in categorized:
            categorized[t] = []
        categorized[t].append(err)
    return categorized


def _suggest_fix(err: dict, language: str) -> str:
    msg = err.get("message", "").lower()
    etype = err.get("error_type", "")
    if etype in ("import", "modulenotfounderror", "importerror"):
        if "modulenotfounderror" in msg or "no module named" in msg:
            pkg = re.search(r"named '([^']+)'", msg)
            if pkg:
                return f"pip install {pkg.group(1)}"
        return "Check import path — ensure module is installed and in PYTHONPATH"
    if etype == "syntax" or "syntaxerror" in msg:
        if "unexpected indent" in msg:
            return "Fix indentation — check for mixed tabs/spaces or wrong nesting level"
        return "Check syntax near the error line — look for missing punctuation"
    if etype in ("type", "typeerror"):
        if "none" in msg or "nonetype" in msg:
            return "None passed where value expected — add None check or use .get()"
        return "Check argument types — likely type mismatch between function call and definition"
    if etype == "rustc":
        if "cannot find" in msg and "in this scope" in msg:
            return "Add missing import: use 'use' statement or fully qualify the path"
        if "mismatched types" in msg:
            return "Type mismatch — add type annotation or cast to match expected type"
        if "use of moved value" in msg:
            return "Value moved — clone() before move, or use &reference"
        return "See Rust error message above for specific fix"
    if etype == "go":
        if "undefined:" in msg or "undeclared name:" in msg:
            return "Add missing import or declare the variable"
        return "See Go error message above for specific fix"
    return "Review the error message above and fix the indicated issue"
