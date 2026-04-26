# cosmos-backend

FastAPI backend for the Cosmos Vedic Astrology Platform. All astrological computation runs through a rule-based harness before any LLM call — Claude synthesizes, never computes.

## Stack

- **Runtime**: Python 3.12, FastAPI, Uvicorn
- **AI**: Anthropic SDK (`claude-sonnet-4-6` for analysis, `claude-haiku-4-5` for chat)
- **Agents**: LangGraph (5-node LOAD → EXTRACT → COMPUTE → SYNTHESIZE → VALIDATE)
- **Database**: Supabase (Postgres + RLS)
- **Chart engines** (switchable via `CHART_ENGINE` env var):
  - `astrology_api` (default) — AstrologyAPI cloud service, concurrency-capped at 5
  - `swiss` — Swiss Ephemeris via pyswisseph (Moshier mode, no file downloads needed)
- **PDF**: ReportLab

## Setup

```bash
cd cosmos-backend
cp .env.example .env   # fill in keys (see Environment Variables below)
uv sync
uv run uvicorn app.main:app --reload
```

Swagger UI: `http://localhost:8000/docs`

## Chart Engines

Both engines produce the same chart contract and are validated against each other by `tests/test_swiss_parity.py`.

| Setting | Value | Behaviour |
|---------|-------|-----------|
| `CHART_ENGINE=astrology_api` | default | Live HTTP calls to AstrologyAPI; requires `ASTROLOGY_API_KEY` |
| `CHART_ENGINE=swiss` | opt-in | Local pyswisseph (Moshier); no external calls, no file downloads |
| `AYANAMSA` | `lahiri` (default) / `raman` / `krishnamurti` / `yukteshwar` | Sidereal ayanamsa used by the Swiss engine |
| `NODE_MODE` | `mean` (default) / `true` | Rahu/Ketu node type for the Swiss engine |

Switch engines without restarting by changing `.env` and reloading.

## Architecture

### Harness-First (Non-Negotiable)
All significators, dignities, aspects, and yogas are computed before any LLM call. Claude only synthesizes the pre-computed context into readable prose.

```
Birth input → Chart Engine (AstrologyAPI or Swiss) → Assembler
                                                          ↓
                                               Parashari Harness → detect_yogas()
                                                          ↓
                                               Context Builder → Claude → Validator
```

### LangGraph Agent Pattern (5 nodes)
```
LOAD → EXTRACT → COMPUTE → SYNTHESIZE → VALIDATE
                                ↑              |
                                └──── retry ───┘  (max 2)
```

## API Routes

### Charts
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/charts` | Create a birth chart (fetches chart engine, runs harness, detects yogas) |
| `GET` | `/api/charts/{id}` | Retrieve full chart row |
| `GET` | `/api/charts/{id}/summary` | Lightweight summary (no raw API data) |

### Analysis (16 sections)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/charts/{id}/analyze/{section}` | Run AI analysis for a section (cached) |
| `GET` | `/api/charts/{id}/analyses` | List all cached analyses |

**Valid sections**: `personality`, `mind`, `career`, `skills`, `wealth`, `foreign`, `romance`, `marriage`, `business`, `property`, `health`, `education`, `parents`, `siblings`, `children`, `spirituality`

### Chat
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/charts/{id}/chat` | SSE streaming chat about the chart (Haiku) |
| `GET` | `/api/charts/{id}/chat/history` | Retrieve conversation history |

### Compatibility
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/compatibility/` | Compute Ashtakoot (8 kootas/36 pts) + LLM interpretation |
| `GET` | `/api/compatibility/{id1}/{id2}` | Retrieve cached compatibility report |

### Timeline
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/charts/{id}/timeline` | Vimshottari dasha timeline with antardashas |

### Prediction & Transits
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/charts/{id}/predict` | Event prediction: dasha scan + transit confirmation + LLM narrative |
| `GET` | `/api/charts/{id}/transits` | Real-time transit snapshot for any date |
| `GET` | `/api/charts/{id}/double-transit` | Jupiter + Saturn joint influence per house |
| `GET` | `/api/charts/{id}/sadesati` | Sade Sati status (rising / peak / setting) |
| `POST` | `/api/charts/{id}/muhurta` | Find auspicious dates for a life event |

### Varshaphal (Annual Chart)
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/charts/{id}/varshaphal?year=2025` | Solar return chart + annual forecast (cached per year) |

### Report
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/charts/{id}/report.pdf` | Download full PDF report (planets, yogas, dashas, analyses) |

## Key Services

### Harness & Chart Engines
| File | Purpose |
|------|---------|
| `app/services/astrology_api/assembler.py` | Assembles AstrologyAPI data into a single chart row; dispatches to Swiss when `CHART_ENGINE=swiss` |
| `app/services/astrology_api/client.py` | Async HTTP client with `Semaphore(5)` concurrency cap |
| `app/services/swiss/ephemeris.py` | Sidereal planetary positions + nakshatras via pyswisseph (Moshier mode) |
| `app/services/swiss/vimshottari.py` | 5-level Vimshottari dasha computation |
| `app/services/swiss/ashtakavarga.py` | Classical Bhinnashtakavarga + Sarvashtakavarga (337-bindu invariant) |
| `app/services/swiss/kp.py` | KP sub-lords and sub-sub-lords (Placidus cusps) |
| `app/services/swiss/doshas.py` | Manglik, Kaal Sarp, Pitra Dosha, Sade Sati |
| `app/services/swiss/calendar.py` | Panchang: tithi, yoga, karana, vara |
| `app/services/swiss/divisional.py` | D1 (Rashi), D9 (Navamsha), Moon chart |
| `app/services/swiss/calculator.py` | Main Swiss entrypoint — produces the same chart contract as the assembler |

### Parashari Harness
| File | Purpose |
|------|---------|
| `app/services/harness/parashari.py` | Parashari significators (house lords, occupants, aspects) |
| `app/services/harness/yogas.py` | Yoga detection (Raj, Dhana, Pancha Mahapurusha, Gaja Kesari, etc.) |
| `app/services/harness/context_builder.py` | Section-specific context strings for LLM |
| `app/services/harness/dignity.py` | Exaltation, debilitation, own-sign lookups |
| `app/services/harness/aspects.py` | Special aspects (Mars 4th/8th, Jupiter 5th/9th, Saturn 3rd/10th) |
| `app/services/harness/atmakaraka.py` | Atmakaraka detection |

### Other Services
| File | Purpose |
|------|---------|
| `app/services/compatibility_service.py` | Ashtakoot engine (all 8 kootas) |
| `app/services/transit_service.py` | Real-time transit positions + whole-sign house assignment |
| `app/services/double_transit.py` | Jupiter + Saturn joint influence detection |
| `app/services/ashtakavarga_service.py` | Bindu strength lookup (3 response shape variants) |
| `app/services/sadesati_service.py` | Saturn/Moon transit phase tracking |
| `app/services/dasha_scanner.py` | Finds MD/AD windows matching target house sets |
| `app/services/muhurta_service.py` | Nakshatra/tithi/vara scoring for auspicious dates |
| `app/services/varshaphal_service.py` | Solar return chart computation |
| `app/services/report_service.py` | ReportLab PDF generation |
| `app/services/timeline_service.py` | Vimshottari timeline with antardasha computation |

## Adding a New Analysis Section

1. Add system prompt → `app/agents/prompts/<section>.py`
2. Add context builder → `app/services/harness/context_builder.py`
3. Register in `app/agents/registry.py`
4. Add name to `VALID_SECTIONS` in `app/models/analysis.py`

No new route needed — `POST /api/charts/{id}/analyze/{section}` is generic.

Or run `/add-section <name> "<scope>"` in Claude Code to scaffold all four edits automatically.

## Tests

```bash
uv run pytest                          # all tests
uv run pytest tests/test_swiss_calculator.py   # Swiss engine unit tests (30 tests, no network)
uv run pytest tests/test_swiss_parity.py       # parity: Swiss vs AstrologyAPI (requires ASTROLOGY_API_KEY)
```

Parity tests validate that both engines agree on ascendant sign, planet signs, nakshatras, whole-sign houses, current dasha lord, and sarvashtaka totals across three birth charts (Delhi 1990, Mumbai 1985, New York 1995). Skipped automatically in CI when `ASTROLOGY_API_KEY` is absent.

## Database Schema

Tables: `profiles`, `charts`, `analyses`, `chat_messages`, `comparisons`

RLS is enabled on all tables. All user data is isolated by `user_id = auth.uid()`.

Key `charts` columns:
- `planets`, `dashas`, `ashtakavarga`, `kp_planet_significators`, `parashari_significators` — JSONB from chart engine + harness
- `yogas` — JSONB list of detected yogas (computed at creation time)
- `varshaphal` — JSONB dict keyed by year, caches annual chart analyses

## Environment Variables

```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ASTROLOGY_API_KEY=          # required when CHART_ENGINE=astrology_api
ANTHROPIC_API_KEY=
CORS_ORIGINS=http://localhost:3000

# Chart engine (optional — defaults shown)
CHART_ENGINE=astrology_api  # or: swiss
AYANAMSA=lahiri             # or: raman, krishnamurti, yukteshwar
NODE_MODE=mean              # or: true
```
