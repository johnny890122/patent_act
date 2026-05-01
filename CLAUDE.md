# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Specification-Driven Development Workflow

When given a new feature request or change in requirements, follow these steps in order — always, without skipping.

### Core Docs (`docs/`)

| File | Purpose |
|---|---|
| `requirements.md` | Single source of truth for what the app does — user stories and scenarios |
| `design.md` | How the app is built — module breakdown, data flows, API specs, interaction details |
| `tasks.md` | Actionable checklist of concrete coding steps derived from the design |
| `static/css/style.css` | UI/console design system |

### Steps

1. **Update `requirements.md`** — Translate the natural language request into user stories and scenarios. Ask for clarification if the request is ambiguous before proceeding.
2. **Update `design.md`** — Amend the technical design to directly map to the new/changed requirements. Include all interaction and system details.
3. **Update `tasks.md`** — Break the updated design into a clear, itemized checklist of distinct, manageable coding tasks.

Never skip or reorder these steps. Never write code for a feature before all three docs reflect it.

---

