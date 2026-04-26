---
description: Create and apply a new Supabase migration safely — inspects current schema first, auto-numbers the file, runs RLS + advisor checks, regenerates frontend types.
argument-hint: <snake_case_description>
allowed-tools: Read, Write, Edit, Glob, Bash, Agent, mcp__supabase__list_tables, mcp__supabase__list_migrations, mcp__supabase__apply_migration, mcp__supabase__get_advisors, mcp__supabase__generate_typescript_types
model: inherit
---

Create a new Supabase migration for: **$1**

Delegate the full flow to the `db-architect` subagent. Brief it with:

1. **Inspect first** — call `mcp__supabase__list_migrations` and `mcp__supabase__list_tables` to learn the current state. Derive the next migration number (highest existing + 1, zero-padded to 3 digits).

2. **Ask the user** for the concrete DDL intent before writing SQL if the one-liner "$1" is ambiguous. Never guess column types or FK relationships.

3. **Write the file** at `app/db/migrations/<NNN>_$1.sql`. RLS must be enabled on any new user-facing table with at least `USING (auth.uid() = user_id)` for SELECT. Include a header comment explaining what the migration does and why.

4. **Apply via MCP** — `mcp__supabase__apply_migration` with the full SQL. Do not use `psql` or Bash.

5. **Advisor sweep** — call `mcp__supabase__get_advisors` with `type: "security"` then `type: "performance"`. Report findings to the user.

6. **Regenerate frontend types** — `mcp__supabase__generate_typescript_types`, write to `../cosmos-frontend/src/types/database.ts` (verify the path exists first with `Glob`).

7. **Summarize** — file created, SQL applied, advisor findings, types regenerated.

If the migration touches `app/db/queries.py`-referenced tables, update `queries.py` in the same turn.
