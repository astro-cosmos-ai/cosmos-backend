# Rule: Mandatory MCP Usage

## Context7 — always fetch docs before writing library code

Required for: LangGraph, FastAPI, Supabase SDK, Anthropic SDK, httpx, pydantic-settings.

```
1. mcp__context7__resolve-library-id  →  get the library ID
2. mcp__context7__get-library-docs    →  fetch relevant section
3. Write code using fetched docs
```

Do not skip this even for "obvious" APIs. Library versions change; training data is stale.

## Supabase MCP — all DB operations

| Task | Tool |
|------|------|
| Create/alter tables | `mcp__supabase__apply_migration` |
| Query data | `mcp__supabase__execute_sql` |
| Check schema | `mcp__supabase__list_tables` |
| Debug queries | `mcp__supabase__get_logs` |

Never use `psql`, raw `supabase.table().select()` in non-query files, or Bash SQL commands.
Always check `mcp__supabase__list_tables` before writing a new migration to avoid conflicts.
