---
name: feature_library
type: core
version: 1.0.0
CI: 50
dependencies: [context, workflow]
last_dream: 2026-04-14
---

## Feature Library Skill — Pattern Router for Backend, API, Auth, and More

Suggests the best architectural patterns and code implementations for a project
based on: tech stack, requirements, and detected use cases.

**This skill generalizes the `ui_library` pattern beyond UI** — covering:
- 🔐 Authentication & Authorization (JWT, OAuth, RBAC, sessions)
- 🌐 API Design (REST, error handling, rate limiting, versioning)
- 🗄️ Database & ORM (migrations, repository pattern, query optimization)
- ⚡ Real-time & Async (WebSockets, SSE, background jobs)
- 📁 File Handling (upload, validation, S3, CDN)
- 🛡️ Resilience (circuit breaker, retries, graceful degradation)
- 📊 Observability (structured logging, tracing, metrics)

---

## How It Works

When invoked, this skill:
1. Loads structured pattern data from `feature_library.json`
2. Detects tech stack and use cases from project context
3. Scores each pattern against requirements
4. Returns **top recommendations** with reasoning + install command + code snippet

---

## Usage

```
route_feature(task, tech_stack, requirements) → {recommended, alternatives, reasoning}
```

**Example:**
```python
from skills.core.feature_library.logic import route_feature

result = route_feature(
    task="Build a SaaS API with auth, rate limiting, and background jobs",
    tech_stack="python",
    requirements="FastAPI backend, PostgreSQL, Redis"
)
# Returns: JWT auth, REST API, Celery background jobs, etc.
```

---

## Categories & Patterns

| Category | Icon | Patterns |
|----------|------|----------|
| Authentication | 🔐 | JWT, Sessions (Redis), OAuth 2.0, RBAC |
| API Design | 🌐 | REST, Error Handling, Rate Limiting |
| Database | 🗄️ | Migrations (Alembic), Repository Pattern + ORM |
| Real-time | ⚡ | WebSockets, SSE, Background Jobs (Celery) |
| File Handling | 📁 | Secure Upload, Presigned S3 URLs |
| Resilience | 🛡️ | Circuit Breaker, Retry + Backoff |
| Observability | 📊 | Structured Logging, Distributed Tracing |

---

## Decision Logic

Priority scoring:
1. **Stack match** — does pattern support the tech stack?
2. **Use case match** — what the project actually needs
3. **Complexity** — appropriate for project size?
4. **Tradeoffs** — does the user understand the costs?

If multiple patterns score equally → return all as alternatives.

---

## Integration

This skill is invoked by the **SPEC debate skill** during `/spec` step:
- After tech stack is confirmed in Round 1 (assumption challenge)
- Patterns suggested as part of the SPEC.md tech stack section
- User confirms or overrides

Also invoked by the **workflow skill** during `/spec` step.

---

## Data Format (feature_library.json)

Each pattern entry contains:
- `name` — display name
- `aliases` — alternative names for AI matching
- `stack` — supported languages/frameworks
- `use_cases` — app types that need this pattern
- `complexity` — low / medium / high
- `description` — one-line description
- `implementation` — code snippets per stack
- `install` — pip/npm install commands
- `tradeoffs` — what you're trading away
- `when` / `dont_when` — decision guide

---

## CI Update
- Pattern suggested and accepted in SPEC: **+2 CI**
- Pattern prevented a known mistake: **+3 CI**
