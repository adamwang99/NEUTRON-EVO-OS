---
name: go-reviewer
type: core
version: 0.1.0
CI: 50
dependencies: []
last_dream: 2026-04-14
---

# Go Reviewer Skill

## Purpose

Expert Go code reviewer: goroutines, channels, error handling, interface design.

## What It Checks

- **Goroutine leaks** — goroutines started but never terminated
- **Race conditions** — unsynchronized access to shared state
- **Error wrapping** — `%w` vs `%v`, proper error chain
- **Context propagation** — `ctx` passed correctly, never stored in struct
- **Interface segregation** — small interfaces, dependency inversion
- **Dependency hygiene** — `go.mod` clean, `go.sum` complete
- **go vet / golangci-lint** — static analysis violations

## Output Format

Structured findings with severity:
- `[CRITICAL]` — goroutine leak, race condition
- `[HIGH]` — missing error wrap, context misuse
- `[MEDIUM]` — lint warnings, interface design
- `[LOW]` — suggestions

## Based On

Inspired by `everything-claude-code`'s `go-reviewer` agent.
