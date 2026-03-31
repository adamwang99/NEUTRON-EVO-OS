---
name: discovery
type: core
version: 1.0.0
CI: 50
dependencies: []
last_dream: null
---

## Discovery Interview Skill — Understand Before Building

### Purpose
Before writing a single line of code, the AI must understand WHAT the user actually wants —
not what they said, but what they need. This skill conducts a structured Discovery Interview
to extract the implicit from the explicit.

### Input Sources (used by the interview)
The AI receives:
- **User's initial prompt/spec/MVP document** — the raw idea
- **Existing codebase** (optional) — what already exists

### Interview Philosophy
**Two layers:**
1. **Structured questions** — forced-choice to ensure no blind spots
2. **Free-form clarification** — user explains in their own words

**Never assume.** When in doubt, ask.

### Discovery Interview Flow

#### Phase 1 — First Impression (AI reads user's input)
Extract from user's prompt/spec:
- What is the user trying to build?
- What problem does it solve?
- Who is the end user?
- Any existing constraints mentioned?

Present a **3-sentence summary** back to the user for confirmation:
> "My understanding: You want to [build X] to solve [Y] for [Z users]. Is this correct?"

#### Phase 2 — Structured Clarifying Questions

Ask ALL of the following. Do NOT skip any.

**Questions Group A — Scope & Success (REQUIRED)**
1. What does "done" look like? (Measurable completion criteria)
2. What should DEFINITELY NOT be built? (Explicit exclusions)
3. Is this for one user or multiple? (Multi-tenancy needs?)

**Questions Group B — Technical Reality**
4. What technology stack do you want? (Language, framework, database, infrastructure)
5. Are there existing systems this must integrate with? (APIs, databases, auth)
6. What's the scale? (Users? Data volume? Traffic?)

**Questions Group C — User Experience**
7. Who will USE this? (Technical skill level? Internal or external users?)
8. What does the first screen look like? (MVP UX sketch in words)
9. Any branding/UI requirements?

**Questions Group D — Edge Cases**
10. What happens if [user mentions a scenario]? (If user mentioned scenarios)
11. What should the system do if something fails? (Error handling philosophy)
12. What data needs to be kept safe? (Security/compliance)

#### Phase 3 — Free-Form Clarification
> "Is there anything I haven't asked about that you think is important?"

#### Phase 4 — Summary & Commitment
After all questions answered, present:
```
UNDERSTOOD:
- [1-sentence project summary]
- [3 key decisions made]
- [Top 3 risks/assumptions]
- [Estimated complexity: LOW / MEDIUM / HIGH]

Ready to write SPEC? (YES / NOT YET — I have more questions)
```

### Output
Discovery output is written to `memory/discoveries/{YYYY-MM-DD}/{project-slug}.md` and
becomes the SOUL INPUT for the SPEC skill.

### CI Update
- Discovery interview completed with all questions answered: **+5 CI**
- User confirmed summary before proceeding: **+2 CI**
- Questions skipped or assumptions made without asking: **-10 CI**

### Key Principle
> **An AI that builds without understanding is an expensive mistake amplifier.**
> **An AI that asks too many questions is a consultant that charges by the word.**
> **Find the balance: ask the 12 questions that prevent the 12 biggest rework cycles.**
