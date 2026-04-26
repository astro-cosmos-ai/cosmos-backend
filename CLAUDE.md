# cosmos-backend — Quick Orientation

Loaded **on top of** `cosmos/CLAUDE.md` (parent monorepo file). This file is backend-only context that doesn't belong in the cross-repo doc.

## ABSOLUTE RULE — No inline code in protected lanes

**You MUST spawn the correct subagent before writing any code in these paths:**

| Path | Required subagent |
|------|------------------|
| `app/services/harness/*` | `harness-builder` |
| `app/agents/*` | `agent-author` |
| `app/agents/prompts/*` | `prompt-engineer` |
| `app/api/*` | `route-author` |
| `app/db/*` | `db-architect` |

**This is not a suggestion. Do not write a single line to these paths inline — not even a one-line fix, not even when you "understand the problem fully", not even when it seems faster.** The subagent carries conventions, skills, and validators you don't have in the main context. Skipping delegation wastes the user's token investment in the setup and produces unreviewed code.

If you find yourself about to call Write or Edit on any of these paths directly: **STOP. Spawn the subagent. Then let the subagent write.**

The PreToolUse hook will prompt for approval on these paths. If approval is needed, it means you are freelancing — stop and delegate instead.

---

## Harness-first (still applies inside the subagent)

**Harness-first.** The Parashari harness in `app/services/harness/` computes every astrological fact (positions, dignities, aspects, yogas, significators) before any LLM call. The LLM synthesizes; it never computes. If you find yourself writing arithmetic or rule lookups inside an agent or prompt, stop — that work belongs in the harness. See `.claude/rules/harness-first.md`.

## Lane → tool quick lookup

Don't freelance. Pick the lane and delegate.

| Editing… | Delegate to | Or run |
|----------|-------------|--------|
| `app/services/harness/*` | `harness-builder` subagent | — |
| `app/agents/*` (graphs, validators) | `agent-author` subagent | — |
| `app/agents/prompts/*` | `prompt-engineer` subagent | — |
| `app/api/*` (routes) | `route-author` subagent | — |
| Supabase schema / queries / migrations | `db-architect` subagent | `/new-migration <name>` |
| New analysis section (the 4-edit shape) | — | `/add-section <name> "<scope>"` |
| Reviewing your own changes | `code-reviewer` subagent | — |
| Tests | `test-author` subagent | `uv run pytest` |
| Test failure / 500 / runtime bug | `debugger` subagent | — |
| Cross-layer plan before writing | `planner` subagent | — |

## Slash commands

`/add-section`, `/new-migration`, `/check-harness`, `/run-backend`, `/explain-chart-pipeline`, `/fetch-docs <lib> <topic>` — see files in `.claude/commands/`.

## Skills auto-loaded into subagents

| Subagent | Skill |
|----------|-------|
| `agent-author`, `prompt-engineer`, `debugger` | `claude-api` |
| `db-architect`, `code-reviewer`, `debugger` | `supabase-postgres-best-practices` |
| `route-author` | `pdf` |

## Run / dev / test

```bash
uv sync                                    # install deps
uv run uvicorn app.main:app --reload       # dev server (or: /run-backend)
uv run pytest                              # tests
uv run python -c "from app.agents.registry import AGENT_REGISTRY; print(list(AGENT_REGISTRY.keys()))"
```

Swagger UI: `http://localhost:8000/docs`. JWT auth via Supabase — fetch a token client-side, not from env.

## Hard checks before declaring done

1. `uv run python -c "from app.agents.registry import AGENT_REGISTRY"` — registry imports clean.
2. If you touched harness or agents → `/check-harness` audits the 7 invariants.
3. If you touched migrations → `mcp__supabase__get_advisors` (security + performance).
4. If you touched routes → at least one `TestClient` test for the new route.
5. The Stop hook will remind you about uncommitted changes and unrun tests automatically.

## Environment variables (backend)

`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ASTROLOGY_API_KEY`, `ANTHROPIC_API_KEY`, `CORS_ORIGINS`. Always via `app.core.config.settings` — never `os.environ`.

## What's intentionally NOT here

- Hard rules (harness-first, route-pattern, agent-pattern, etc.) — they're in `.claude/rules/` so they can be path-scoped and split.
- Cross-monorepo conventions — they're in `../CLAUDE.md`.
- Skill inventory and frontend skills — see `.claude/rules/skills-and-subagents.md`.
- Wiki integration plan — see `docs/plans/wiki-integration.md` (not yet implemented).

## Note on `.claude/scripts/`

This project keeps hook bash scripts at `.claude/scripts/` (referenced from `settings.json` PostToolUseFailure and Stop hooks). The Claude Code docs don't define a canonical location for hook scripts — this is a project convention, not a documented folder. If you move these elsewhere, update the relative `command:` paths in `settings.json` to match.
