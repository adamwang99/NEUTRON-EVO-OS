"""
Go Reviewer Skill — Expert Go code review.
Based on ECC's go-reviewer agent pattern.
"""
from __future__ import annotations

from pathlib import Path
import re


def run_go_reviewer(task: str, context: dict = None) -> dict:
    """
    Review Go code for goroutine leaks, race conditions, error handling issues.

    Args:
        task: Files to review
        context: {files: [...], check: "all|safety|errors|style"}

    Returns: {status, findings: [...], ci_delta}
    """
    context = context or {}
    files = context.get("files", [])
    check_type = context.get("check", "all")

    findings: list[dict] = []

    if not files:
        return {
            "status": "ok",
            "output": "No files specified. Provide paths in context['files'].",
            "findings": [],
            "ci_delta": 0,
        }

    for file_path in files:
        p = Path(file_path)
        if not p.exists():
            findings.append({
                "file": file_path, "line": 0, "severity": "ERROR",
                "issue": f"File not found",
                "fix": "Check path.",
            })
            continue

        try:
            content = p.read_text()
        except Exception as e:
            findings.append({
                "file": file_path, "line": 0, "severity": "ERROR",
                "issue": f"Cannot read: {e}",
                "fix": "Check permissions.",
            })
            continue

        findings += _check_goroutines(content, file_path)
        findings += _check_errors(content, file_path)
        findings += _check_context(content, file_path)
        findings += _check_interface(content, file_path)

    # Run go vet
    vet_output = _run_go_vet([f for f in files if Path(f).exists()])
    findings += vet_output

    critical = [f for f in findings if f["severity"] == "CRITICAL"]
    high = [f for f in findings if f["severity"] == "HIGH"]

    return {
        "status": "ok",
        "output": f"Reviewed {len(files)} Go file(s): {len(findings)} findings"
                  + (f" | ⚠️ {len(critical)} CRITICAL" if critical else "")
                  + (f" | ⚠️ {len(high)} HIGH" if high else ""),
        "findings": findings,
        "critical_count": len(critical),
        "high_count": len(high),
        "ci_delta": 3,
    }


def _check_goroutines(content: str, file_path: str) -> list[dict]:
    findings = []
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        # go func() without done channel or context
        if re.search(r"\bgo\s+func\s*\(", line):
            # Check if there's a done channel or context nearby
            window = "\n".join(lines[max(0, i-5):min(len(lines), i+10)])
            if "done" not in window.lower() and "ctx.Done()" not in window and "context" not in window.lower():
                findings.append({
                    "file": file_path, "line": i,
                    "severity": "HIGH",
                    "issue": "goroutine without done channel or context — potential leak",
                    "fix": "Add a done channel or use context.WithCancel.",
                })
        # sync.Mutex used with pointer receiver only
        if "sync.Mutex" in line and "struct" in "\n".join(lines[max(0, i-10):i+10]):
            struct_window = "\n".join(lines[max(0, i-10):i+10])
            if "sync.Mutex" in struct_window and "mu" not in struct_window:
                findings.append({
                    "file": file_path, "line": i,
                    "severity": "MEDIUM",
                    "issue": "sync.Mutex should be a pointer field (mu *sync.Mutex)",
                    "fix": "Change to mu sync.Mutex → *sync.Mutex",
                })
    return findings


def _check_errors(content: str, file_path: str) -> list[dict]:
    findings = []
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        # fmt.Printf or log.Printf with error but no wrapping
        if re.search(r'(fmt\.Printf|log\.Printf|log\.Print)\s*\(.*%v.*err', line):
            findings.append({
                "file": file_path, "line": i,
                "severity": "MEDIUM",
                "issue": "Logging error with %v — lost error chain",
                "fix": "Use %w for wrapped errors, or log error.Error() separately.",
            })
        # Returning error without wrapping
        if re.search(r'return\s+.*errors\.New\(', line) and "fmt.Errorf" not in line:
            findings.append({
                "file": file_path, "line": i,
                "severity": "LOW",
                "issue": "errors.New() without context — consider fmt.Errorf with %w",
                "fix": "Use fmt.Errorf(\"...: %w\", err) for wrapped errors.",
            })
    return findings


def _check_context(content: str, file_path: str) -> list[dict]:
    findings = []
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        # ctx stored in struct field
        if re.search(r"\bctx\s+(context\.Context|\*golang\.org/.*Context)", line):
            window = "\n".join(lines[max(0, i-3):i])
            if "struct" in window or "type" in window:
                findings.append({
                    "file": file_path, "line": i,
                    "severity": "CRITICAL",
                    "issue": "context.Context stored in struct — not goroutine-safe",
                    "fix": "Pass context as first parameter, not as a struct field.",
                })
        # context.Background() in request handler
        if "context.Background()" in line and "http" in content:
            findings.append({
                "file": file_path, "line": i,
                "severity": "HIGH",
                "issue": "context.Background() in HTTP handler — discards request context",
                "fix": "Use r.Context() from the *http.Request instead.",
            })
    return findings


def _check_interface(content: str, file_path: str) -> list[dict]:
    findings = []
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        # Large interface (>5 methods)
        if re.search(r"type\s+\w+\s+interface\s*{", line):
            body = []
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("}"):
                body.append(lines[j])
                j += 1
            methods = [m for m in body if re.search(r"\w+\s*\(", m)]
            if len(methods) > 5:
                findings.append({
                    "file": file_path, "line": i,
                    "severity": "LOW",
                    "issue": f"Large interface with {len(methods)} methods — consider splitting",
                    "fix": "Split into smaller interfaces (Interface Segregation Principle).",
                })
    return findings


def _run_go_vet(paths: list[str]) -> list[dict]:
    import subprocess, os
    if not paths:
        return []
    valid = [p for p in paths if os.path.exists(p)]
    if not valid:
        return []

    # Build package list from the file paths, respecting the `paths` parameter.
    # `go vet ./...` ignores paths and runs all packages in the module.
    # Instead, compute packages from the files themselves.
    packages: set[str] = set()
    for p in valid:
        abs_path = os.path.abspath(p)
        # Walk up from file to find nearest go.mod
        dir_path = os.path.dirname(abs_path)
        while dir_path and dir_path != os.path.dirname(dir_path):
            if os.path.exists(os.path.join(dir_path, "go.mod")):
                # Compute package import path relative to module root
                module_root = dir_path
                # Get relative path from module root to this file's dir
                rel = os.path.relpath(os.path.dirname(abs_path), module_root)
                # Replace OS separator with /
                pkg = rel.replace(os.sep, "/")
                if pkg == ".":
                    pkg = ""
                if pkg:
                    packages.add(pkg)
                else:
                    # It's a root-level file — use module package
                    with open(os.path.join(module_root, "go.mod")) as mf:
                        for line in mf:
                            if line.startswith("module "):
                                packages.add(line.strip().split()[1])
                                break
                break
            dir_path = os.path.dirname(dir_path)

    try:
        # Run `go vet <packages>` instead of `go vet ./...` to respect paths parameter
        cmd = ["go", "vet"] + (list(packages) if packages else ["./..."])
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=60,
            cwd=os.path.dirname(valid[0]) or ".",
        )
        findings = []
        for line in (result.stdout + result.stderr).splitlines():
            m = re.match(r"^([^:]+):(\d+):\s+(.+)$", line)
            if m:
                findings.append({
                    "file": m.group(1), "line": int(m.group(2)),
                    "severity": "HIGH",
                    "issue": m.group(3),
                    "fix": "Fix go vet violation.",
                })
        return findings
    except FileNotFoundError:
        return []
    except Exception:
        return []
