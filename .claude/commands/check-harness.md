---
description: Sanity-check the harness-first invariant — scans for LLM calls inside harness code, missing validators, wrong house systems, and unregistered sections.
allowed-tools: Read, Grep, Glob, Bash
model: inherit
---

Run the harness-first audit. Report findings as a punch list — pass/fail per check, no filler.

### 1. No LLM imports inside the harness
```
!grep -rn "import anthropic\|from anthropic\|anthropic\." app/services/harness/ || echo "PASS: no anthropic imports in harness/"
```

### 2. No AstrologyAPI calls inside the harness
```
!grep -rn "astrology_api" app/services/harness/ || echo "PASS: harness decoupled from AstrologyAPI client"
```

### 3. Whole-sign house formula used (not Placidus / bhava chalit)
```
!grep -rn "placidus\|koch\|bhava_chalit\|chalit" app/services/harness/ app/services/astrology_api/ || echo "PASS: no non-whole-sign house system references"
```

### 4. Every section in VALID_SECTIONS has a prompt AND a context builder AND a registry entry
Read `app/models/analysis.py`, `app/agents/prompts/`, `app/services/harness/context_builder.py`, and `app/agents/registry.py`. For each section in `VALID_SECTIONS`:
- `app/agents/prompts/<section>.py` exists and exports `SYSTEM_PROMPT`
- `build_<section>_context` exists in `context_builder.py`
- Entry exists in `AGENT_REGISTRY`

Report any mismatches.

### 5. position_validator is wired in the graph
```
!grep -n "validate_output\|position_validator" app/agents/base_agent.py
```
Confirm `validate_node` calls `validate_output` and the conditional edge routes back to SYNTHESIZE on failure.

### 6. Retry cap is exactly 2
```
!grep -n "retry_count" app/agents/base_agent.py
```
Confirm the ">= 2" check is present and not been relaxed.

### 7. Semaphore(5) on the AstrologyAPI client
```
!grep -n "Semaphore" app/services/astrology_api/client.py
```

### Final report

Green-light summary if all 7 checks pass. Otherwise list each failure with the exact file:line and a one-line remediation.
