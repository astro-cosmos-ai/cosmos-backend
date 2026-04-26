# Plan: Wiki integration for cosmos-backend

**Status:** not started
**Goal:** stop re-exploring code every session. Make the Obsidian wiki the architecture map I check first, before grep/glob.

**Vault:** `~/Documents/muninn/` (already exists)
**Skills involved:** `wiki-update`, `wiki-query`, `wiki-status`, `wiki-ingest`, `wiki-rebuild`

---

## The core behavior change

Right now: question → grep/glob/read → re-derive architecture each session.
Target: question → wiki-query first → grep/glob only if wiki returned nothing or for verification before edits.

Rules of thumb:
- **Architecture / "how does X work" / "where is Y handled" / "what calls Z"** → wiki-query first.
- **About to edit code** → read the actual file (wiki may be stale).
- **After significant architecture change** → run `wiki-update` to refresh the relevant pages.

---

## Pages to seed in the wiki (one-time push)

These are the "code maps" the user wants — what we currently re-derive every session.

| Page | Content |
|------|---------|
| `Cosmos: layer map` | Directory tour. File → purpose. Layer → responsibilities. Top-down. |
| `Cosmos: chart pipeline` | Birth input → AstrologyAPI → assembler → harness → yogas → DB → analysis. Call graph with file:line refs. |
| `Cosmos: harness internals` | dignity / aspects / parashari / yogas / atmakaraka — what each owns, public API per file, key constants (`DIGNITY` dict, `SPECIAL_ASPECTS`). |
| `Cosmos: agent registry` | Section → (context_builder, system_prompt). Refresh whenever a section is added. |
| `Cosmos: API surface` | Every route. Method + path + request model + response model + auth + caching behavior. |
| `Cosmos: db schema snapshot` | Tables, columns, JSONB shapes, RLS policies. Refresh after each migration. |
| `Cosmos: design decisions` | Why ReportLab / Sonnet for analyses / whole-sign / 5-node graph / Semaphore(5) / harness-first. The *reasons* we'd otherwise lose. |
| `Vedic astrology reference` | Cross-project. House meanings, dignity rules, dasha system, yoga catalog. Lets prompt-engineer write better prompts without re-explaining. |

---

## Implementation steps (in order)

### Step 1 — Seed the wiki (one-time, ~10–15 min skill run)

From inside `cosmos-backend/`:

```
Run wiki-update with the page list above as scope.
```

Verify after with `wiki-status`. The 8 pages above should show up under the appropriate vault folders (likely `projects/cosmos/` and `references/`).

### Step 2 — Wire `wiki-query` into the right subagents

Edit frontmatter `skills:` field. **Add `wiki-query`, do not replace existing skills.**

| File | New `skills:` line |
|------|--------------------|
| `cosmos-backend/.claude/agents/planner.md` | `skills: wiki-query` |
| `cosmos-backend/.claude/agents/code-reviewer.md` | `skills: supabase-postgres-best-practices, wiki-query` |
| `cosmos-backend/.claude/agents/debugger.md` | `skills: claude-api, supabase-postgres-best-practices, wiki-query` |

**Do NOT auto-load wiki-query into:**
- `harness-builder`, `agent-author`, `route-author`, `prompt-engineer`, `db-architect`, `test-author` — these *write* code; they should consult wiki for context but verify against actual source. Easier to keep wiki-query off-by-default for them and let them invoke it explicitly when needed.

### Step 3 — Add a hard rule

Create `cosmos-backend/.claude/rules/wiki-first.md`:

```markdown
# Rule: Wiki-first for architecture questions

For questions about *how* the codebase works, *where* something is handled, or *what* calls something — query the wiki BEFORE grep/glob/read.

## Triggers (wiki-query first)
- "how does X work"
- "where is X handled / where does X live"
- "what calls Y / who uses Z"
- "what's the architecture / design of X"
- "explain the X pipeline"
- "why did we do X this way" (design decisions)

## NOT triggers (read source directly)
- About to edit a file → read the file fresh; wiki may be stale.
- Looking at a specific function's implementation → read it.
- Debugging a runtime error → read traceback + actual code.

## After significant architecture changes
Run `wiki-update` before declaring done. Otherwise the wiki drifts and future sessions get stale answers.
```

### Step 4 — Update SessionStart hook

In `cosmos-backend/.claude/settings.json`, append to the SessionStart `additionalContext` string:

```
**Knowledge sources:** wiki at ~/Documents/muninn/ has cosmos architecture pages. Use wiki-query before re-exploring code for architecture questions. See .claude/rules/wiki-first.md.
```

### Step 5 — Update UserPromptSubmit hook

In `cosmos-backend/.claude/settings.json`, add a new keyword block to the UserPromptSubmit hook command:

```
if echo "$prompt" | grep -qiE '\b(how does|where is|what calls|architecture|pipeline|why did we|how is .* handled)\b'; then
  hints="$hints$nl- Architecture question → wiki-query FIRST before grep/glob. See .claude/rules/wiki-first.md."
fi
```

### Step 6 — Add Stop hook nudge for wiki freshness

In `cosmos-backend/.claude/scripts/stop-nudge.sh`, add a check: if files in `app/services/harness/`, `app/agents/`, `app/api/`, or `app/db/migrations/` were modified, append:

```
- Architecture-impacting files changed. Consider running wiki-update before stopping so the wiki doesn't drift.
```

---

## Verification (how to know it's working)

After step 1 completes:
- `ls ~/Documents/muninn/projects/cosmos/` — should show the 8 pages.
- `wiki-status` — should report them as ingested.

After steps 2–6:
- New session, ask "how does the chart analysis pipeline work?"
- Expected: I invoke `wiki-query` first (you'll see the skill activate in the transcript) and answer from the wiki, citing pages.
- If I instead start with `Glob`/`Grep`/`Read` of `app/`, the wiring failed — re-check that wiki-query is in the planner subagent's frontmatter and the rule file is loaded.

---

## Maintenance

- **Trigger to re-run `wiki-update`**: after any of the following lands —
  - new analysis section
  - new route or removed route
  - migration
  - harness module added or significantly refactored
  - design decision changed (e.g. switched models, dropped a dependency)
- **Trigger to `wiki-rebuild`** (heavier, archives + re-ingests): if the wiki gets out of sync after several missed updates, or if a major refactor invalidates many pages.
- **Cosmos pages live under** `~/Documents/muninn/projects/cosmos/` (the vault structure created by `wiki-setup`). The cross-project Vedic reference lives under `~/Documents/muninn/references/`.

---

## Open questions for the user (resolve when implementing)

1. Does `~/Documents/muninn/` already have the project structure (`projects/`, `references/`, `concepts/`, etc.) or does `wiki-setup` need to run first? Run `wiki-status` to find out.
2. Is `QMD_WIKI_COLLECTION` set in the vault's `.env`? If so, semantic search works; if not, wiki-query falls back to Grep (still useful, just slower).
3. Do you want me to seed the `Vedic astrology reference` page or do you have one already from a prior project? It's cross-project so it may already exist.

---

## What this plan does NOT do

- It does not replace auto-memory (`~/.claude/projects/-Users-aadarsh-Documents-cosmos/memory/`) — that stays for live state and user prefs.
- It does not replace CLAUDE.md or `.claude/rules/` — those stay as hard rules.
- It does not auto-update the wiki on every commit. `wiki-update` is invoked explicitly when architecture changes.
- It does not solve drift entirely — wiki can still go stale between updates. The Stop hook nudge is a soft mitigation.
