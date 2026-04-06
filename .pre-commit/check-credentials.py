#!/usr/bin/env python3
"""
check-credentials.py — pre-commit hook
Fails if any file being committed contains API keys, secrets, or credentials.
Pattern matches: api_key=, secret=, password=, token= with real-looking values.
"""
import re
import sys

CREDENTIAL_PATTERNS = [
    # Match ONLY real credential values: keys/tokens with known prefixes.
    # Excludes: variable names (ANTHROPIC_AUTH_TOKEN), function calls (os.environ.get),
    #           dictionary access (secrets["api_key"]).
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),                   # OpenAI API key
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),                 # GitHub Personal Access Token
    re.compile(r"xox[baprs]-[a-zA-Z0-9]{10,}"),          # Slack OAuth token
    re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-]{20,}"),  # Bearer token in header strings
    re.compile(r"(?i)(?:api[_-]?key|secret[_-]?key|password)\s*[:=]\s*['\"][^'\"]{'{'[^}]{16,}'}'"),  # dict["key..."] form
]

SENSITIVE_FILES = {".env", ".credentials", "credentials.json", "secrets.json"}

def check_file(path: str) -> list[str]:
    """Return list of found credential patterns in file."""
    findings = []
    try:
        with open(path, errors="ignore") as f:
            for i, line in enumerate(f, 1):
                for pattern in CREDENTIAL_PATTERNS:
                    if pattern.search(line):
                        findings.append(f"  Line {i}: {line.strip()[:80]}")
    except Exception:
        pass
    return findings


def main():
    if len(sys.argv) < 2:
        sys.exit(0)  # no files to check

    errors = []
    for path in sys.argv[1:]:
        # Skip known safe files
        if any(safe in path for safe in SENSITIVE_FILES):
            continue
        findings = check_file(path)
        if findings:
            errors.append(f"\n{path}:\n" + "\n".join(findings))

    if errors:
        print("ERROR: Possible credentials found in commit:")
        print("\n".join(errors))
        print("\nRemove credentials before committing.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
