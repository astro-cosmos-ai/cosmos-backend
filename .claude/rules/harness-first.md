# Rule: Harness-First Architecture

The Parashari harness MUST run before any LLM call. This is the core invariant of this codebase.

## What the harness owns
- Planetary positions and house assignments (whole-sign)
- House lord lookups (`dignity.py` DIGNITY dict)
- Aspect computation (`aspects.py` SPECIAL_ASPECTS)
- Significator assembly (`parashari.py` compute_all_significators)
- Context string formatting (`context_builder.py`)

## What the LLM owns
- Synthesizing harness output into readable prose
- No arithmetic, no rule lookups, no astrological computation

## Enforcement
- `validate_node` in `base_agent.py` runs `position_validator` on every LLM response
- Any planetary reference not in `chart_json['planets']` triggers a retry
- Max 2 retries; after that, the last response is returned as-is with a warning
