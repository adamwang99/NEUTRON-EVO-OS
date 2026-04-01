---
name: ui_library
type: core
version: 0.1.0
CI: 50
dependencies: [context, workflow]
last_dream: null
---

## UI Library Router Skill

Suggests the best UI library for a frontend project based on: framework, app type, and requirements.

---

## How It Works

When invoked with project context (`project_type`, `tech_stack`, `requirements`), this skill:
1. Loads structured library data from `ui_libraries.json`
2. Scores each library against the project requirements
3. Returns the **top recommendation** with reasoning + repo link + install command

---

## Usage

```
route_ui_library(project_type, tech_stack, requirements) → {recommended, alternatives, reasoning}
```

**Example call:**
```python
from skills.core.ui_library.logic import route_ui_library

result = route_ui_library(
    project_type="landing page",
    tech_stack="next.js",
    requirements="animation-heavy, modern aesthetic"
)
# Returns: shadcn/ui or Magic UI + alternatives + reasoning
```

---

## Supported Libraries

| Library | Best For | Framework | Bundle |
|---------|----------|-----------|--------|
| **shadcn/ui** | Tùy biến cao, dashboard, SaaS | React/Next.js | Tree-shake |
| **Ant Design** | Enterprise dashboard, data-heavy | React/Vue/Angular | ~500KB |
| **Mantine** | Full-featured app, forms, mobile-first | React/Next.js | ~200KB |
| **Magic UI** | Landing page, animations, marketing | React/Vue/Svelte/HTML | Per-comp |
| **DaisyUI** | Nhẹ nhất, utility-first, any project | Any | ~10KB |

---

## Decision Logic

Priority scoring:
1. **Framework match** — does library support the tech stack?
2. **Use case match** — landing vs dashboard vs admin vs SaaS
3. **Requirements match** — animation, performance, customizability

If multiple libraries score equally → return all as alternatives.

---

## Fields in `ui_libraries.json`

Each library entry contains:
- `name` — display name
- `aliases` — alternative names the AI can match
- `stack` — supported frameworks
- `use_cases` — app types this library suits
- `bundle` — approximate bundle size
- `customizability` — how flexible it is
- `style` — aesthetic character
- `motion` — animation support
- `repo` — GitHub repo URL
- `install` — quick install command
- `when` / `dont_when` — decision guide for AI

---

## Integration

This skill is automatically invoked by the **workflow skill** during `/spec` step:
- After tech stack is confirmed
- Before writing SPEC.md
- User confirms or changes the suggested library
