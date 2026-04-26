# Rule: Use Skills, Subagents, and Slash Commands — Don't Freelance

Before writing code that falls into a known lane, invoke the right tool. Starting from a blank page when a scaffold exists is how the project drifts.

## Installed skills (`~/.claude/skills/`) — full inventory

### Cosmos-backend relevant (wired into subagents via frontmatter)

| Skill | Auto-loaded into | Use for |
|-------|------------------|---------|
| `claude-api` | `agent-author`, `prompt-engineer`, `debugger` | Anthropic SDK calls, prompt caching, streaming, tool use, thinking blocks |
| `supabase-postgres-best-practices` | `db-architect`, `code-reviewer`, `debugger` | Postgres schema, indexes, RLS performance, query plans, JSONB indexing |
| `pdf` | `route-author` | ReportLab PDF generation (`/report.pdf` route, `report_service.py`) |
| `context7-mcp` | (global rule loads it for all relevant tasks) | Live library/framework docs |
| `mcp-builder` | (invoke directly) | Only if we ever build an MCP server |

### Frontend-relevant (will wire when we do `cosmos-frontend/.claude/`)

| Skill | Use for |
|-------|---------|
| `frontend-design` | Distinctive, production-grade UI |
| `react-best-practices` | Vercel React/Next.js performance |
| `composition-patterns` | Compound components, render props, refactoring boolean-prop chaos |
| `react-view-transitions` | View Transition API animations |
| `gsap-core`, `gsap-react`, `gsap-scrolltrigger`, `gsap-timeline`, `gsap-utils`, `gsap-performance`, `gsap-plugins`, `gsap-frameworks` | GSAP animation suite |
| `web-design-guidelines` | Accessibility / UX audit |
| `webapp-testing` | Playwright frontend tests |
| `deploy-to-vercel` | Vercel deploys |

### Not directly applicable to cosmos (acknowledged for completeness)

`caveman` (token-compression mode — invoke with `/caveman` if needed), `doc-coauthoring`, `wiki-*` (9 skills, Obsidian wiki management), `skill-creator` (meta — to author new skills), `stitch-design`/`stitch-loop` (Stitch design tooling), `web-artifacts-builder` (claude.ai HTML artifacts), `react-native-skills` (mobile, not relevant), `xlsx` / `docx` (Office files, not currently used).

### Note: there is no `update-config` skill

An earlier draft of CLAUDE.md referenced `/update-config`; it doesn't exist in your install. For hooks/permissions, edit `.claude/settings.json` directly and validate with `jq .`.

## Project slash commands (backend)

| Task | Command |
|------|---------|
| New analysis section (prompt + context + registry + whitelist) | `/add-section <name> "<scope>"` |
| New Supabase migration (inspect → write → apply → advisors → types) | `/new-migration <snake_name>` |
| Verify harness-first invariants still hold | `/check-harness` |
| Start the dev server with env checks | `/run-backend` |
| Walk the chart-creation + analysis pipeline | `/explain-chart-pipeline` |
| Fetch current library docs (Context7) | `/fetch-docs <lib> <question>` |

## Project subagents (backend)

### Building lanes (write code)
| Editing / creating | Subagent |
|--------------------|----------|
| `app/services/harness/*` (dignity, aspects, yogas, context) | `harness-builder` |
| `app/agents/*` (LangGraph graphs, validators) | `agent-author` |
| Any Supabase schema/query/migration | `db-architect` |
| `app/api/*` (FastAPI routes) | `route-author` |
| `app/agents/prompts/*` (system prompts) | `prompt-engineer` |

### Verifying / planning lanes
| When | Subagent |
|------|----------|
| Right after writing or modifying code (PR review, sanity check) | `code-reviewer` (read-only — checks harness-first, RLS, async, validator wiring) |
| Adding tests, raising coverage, fixing a flaky test | `test-author` (pytest + fixtures, no harness mocks) |
| Test failure, 500, stack trace, validator looping past 2 retries | `debugger` (pulls Supabase logs via MCP, isolates root cause) |
| Multi-layer feature (db + harness + route + tests) before writing anything | `planner` (read-only, orders steps by layer, names the right subagent for each step) |

Invoke a subagent via the `Agent` tool with `subagent_type: "<name>"`. They carry the project conventions in their system prompt — you do not have to re-explain.

## Why this matters

Each skill / command / subagent is a pre-loaded context. Skipping them means:
- Rewriting conventions from memory (which drifts).
- Missing the MCP calls the scaffold would have made.
- Producing code that doesn't match the rest of the codebase.

**Rule of thumb**: if the work fits a lane above, use the tool. If it doesn't, ask the user before proceeding.
