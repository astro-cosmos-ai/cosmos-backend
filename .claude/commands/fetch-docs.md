---
description: Fetch current library docs via Context7 MCP. Use before writing code that touches a library — never rely on training data.
argument-hint: <library> <question>
allowed-tools: mcp__context7__resolve-library-id, mcp__context7__get-library-docs
model: inherit
---

Fetch fresh documentation for: **$1** — topic: $2.

1. Call `mcp__context7__resolve-library-id` with `libraryName: "$1"` and inspect the candidates. Pick the one that best matches: exact name > description relevance > snippet count > source reputation. If the user gave a version hint in $2, prefer the version-specific ID.

2. Call `mcp__context7__get-library-docs` with that ID and `topic: "$2"`. Set `tokens` based on breadth: 3000 for focused snippets, 8000 for multi-feature walkthroughs.

3. Summarize the relevant API shape, then quote the smallest code snippet that answers the question.

Do **not** answer from memory if the docs returned useful content — the user explicitly wants current docs.
