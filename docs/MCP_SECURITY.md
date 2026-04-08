# MCP Security Vetting Checklist

> **Source:** Distilled from `claude-code-ultimate-guide` security methodology.
> Every MCP server added to NEUTRON must pass this checklist.

---

## 5-Minute Vetting Checklist

### Phase 1: Source Verification (2 min)

```
□ Check npm/pypi source — is it the official package?
  Run: npm view <package> repository.url
       pip show <package> | grep Home-page

□ Verify GitHub repo exists and has recent commits
  - Last commit < 6 months ago?
  - >10 contributors?
  - Security policy present?

□ Check for known malicious patterns:
  grep -r "eval(" <repo>        # Code injection
  grep -r "exec(" <repo>        # Shell injection
  grep -r "subprocess" <repo>   # Subprocess execution
  grep -r "os.system" <repo>    # Shell execution
```

### Phase 2: Permission Surface (2 min)

```
□ Read the MCP server manifest (mcp.json or similar)
□ Map all tools/resources to required permissions:
  - File system access (read/write/glob)?
  - Network access (HTTP requests)?
  - Environment variable access?
  - Command execution?
  - Credential access?

□ Is permission scope minimal?
  - A code analysis tool should NOT need network access
  - A documentation tool should NOT need file write access
```

### Phase 3: Runtime Verification (1 min)

```
□ Run in a sandboxed environment first:
  docker run --rm -it python:3.11-slim
  npm install -g <package>
  echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | node server.js

□ Check for unexpected network calls:
  strace -e network -f node server.js 2>&1 | grep connect

□ Verify API key never leaves the machine:
  - Does it POST to an external analytics service?
  - Does it phone home to a telemetry endpoint?
```

---

## CVE Catalog (2025-2026)

> Source: `claude-code-ultimate-guide` — 24 mapped CVEs, 655 malicious skills catalog

### Critical (CVSS ≥ 9.0)

| CVE | Package | Vulnerability | Impact |
|-----|---------|--------------|--------|
| CVE-2026-0755 | gemini-mcp-tool | RCE via unsanitized command injection | Remote code execution |
| CVE-2025-35028 | HexStrike AI MCP Server | OS command injection in tool parameters | Shell execution |
| CVE-2025-15061 | Framelink Figma MCP Server | Shell metacharacter injection in file paths | File write as code |
| CVE-2026-25253 | OpenClaw | One-click RCE (17,500+ exposed instances) | Full system compromise |

### High (CVSS 7.0-8.9)

| CVE | Package | Vulnerability |
|-----|---------|--------------|
| CVE-2025-3XXXX | [Various AI MCP servers] | Tool injection via prompt in tool name |
| CVE-2025-4XXXX | [Community skill packages] | Dependency confusion attack |
| CVE-2025-5XXXX | [npm MCP packages] | Malicious post-install script |

---

## Rug Pull Attack Detection

### Attack Pattern

```
Week 1:  Attacker publishes benign MCP server
         → User approves in Claude Code settings
         → Server runs with full permissions

Week 2-4: Attacker builds trust, gets 1000+ installs
         → Attacker pushes malicious update
         → All users running latest version are compromised

Attacker's goal: Exfiltrate ~/.ssh, .env, API keys, git credentials
```

### Detection

```
□ Watch for version jumps without changelog
  npm view <package> time
  pip index versions <package>

□ Check npm/pypi publish frequency:
  - >1 publish/day = suspicious
  - Publish from personal account vs org = caution

□ Run: npm audit, pip audit BEFORE every use
  npm audit
  pip audit

□ Subscribe to:
  - npm security advisories
  - PyPI security advisories
  - GitHub security advisories for MCP projects
```

### Prevention

```
NEUTRON RULE:
1. Pin MCP server versions: "version": "1.2.3" (exact)
   → Never use "latest" or "^1.2.3"
2. Review changelog before upgrading
3. Run in sandboxed environment first
4. Set up GitHub Actions to notify on dependency updates
5. Use: npm audit + pip audit + grepscan before every session
```

---

## MCP Permission Audit Workflow

### Before Adding an MCP Server

```bash
# 1. Clone to temp directory
git clone https://github.com/<user>/<mcp-server>.git /tmp/mcp-audit
cd /tmp/mcp-audit

# 2. Scan for dangerous patterns
grep -rn "eval\|exec\|subprocess\|os.system\|curl\|wget" --include="*.js" --include="*.py"

# 3. Check network calls
npm install && node -e "
  const net = require('net');
  // Monkey-patch to log outbound connections
  const original = net.connect;
  net.connect = function() {
    console.log('OUTBOUND:', arguments[0]);
    return original.apply(this, arguments);
  };
"

# 4. Verify manifest permissions
cat mcp.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('permissions',{}), indent=2))"

# 5. Run npm audit
npm audit 2>&1 | grep -E "critical|high|moderate" || echo "OK"
```

### NEUTRON Integration

Add to `memory/.mcp_audit_log.json` after each MCP server review:

```json
{
  "server": "mcp-server-name",
  "audited_at": "2026-04-05T12:00:00",
  "source_verified": true,
  "permission_surface": ["filesystem.read", "network"],
  "cve_check": "passed",
  "rug_pull_risk": "low",
  "notes": "Verified via npm audit + strace"
}
```

---

## MCP Top 10 Risks

> Based on OWASP MCP Top 10 + NEUTRON threat model

1. **Tool Injection** — Attacker controls tool name/args via prompt
2. **Credential Exfiltration** — MCP server steals API keys from environment
3. **File System Overwrite** — Malicious tool writes executable code
4. **Dependency Confusion** — Malicious package with same name as internal tool
5. **Rug Pull** — Benign MCP → malicious update after trust built
6. **Permission Scope Creep** — Tool requests more permissions than needed
7. **Telemetry/Phone Home** — MCP server sends data to attacker without user knowledge
8. **Sandbox Escape** — MCP server breaks out of Claude Code's permission model
9. **State Pollution** — Malicious tool corrupts shared state
10. **Supply Chain Attack** — MCP server depends on malicious npm/pypi package
