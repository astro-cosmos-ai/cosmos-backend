# cosmos-backend

FastAPI backend for the Cosmos Vedic Astrology Platform. All astrological computation runs through a rule-based harness before any LLM call — Claude synthesizes, never computes.

## Stack

- **Runtime**: Python 3.12, FastAPI, Uvicorn
- **AI**: Anthropic SDK (`claude-sonnet-4-6` for analysis, `claude-haiku-4-5` for chat)
- **Agents**: LangGraph (5-node LOAD → EXTRACT → COMPUTE → SYNTHESIZE → VALIDATE)
- **Database**: Supabase (Postgres + RLS)
- **Astrology data**: AstrologyAPI (concurrency-capped at 5 via `asyncio.Semaphore`)
- **PDF**: ReportLab

## Setup

```bash
cd cosmos-backend
cp .env.example .env   # fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, ASTROLOGY_API_KEY, ANTHROPIC_API_KEY
uv sync
uv run uvicorn app.main:app --reload
```

Swagger UI: `http://localhost:8000/docs`

## Architecture

### Harness-First (Non-Negotiable)
All significators, dignities, aspects, and yogas are computed before any LLM call. Claude only synthesizes the pre-computed context into readable prose.

```
Birth input → AstrologyAPI → Assembler → Parashari Harness → detect_yogas()
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
| `POST` | `/api/charts` | Create a birth chart (fetches AstrologyAPI, runs harness, detects yogas) |
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

| File | Purpose |
|------|---------|
| `app/services/harness/parashari.py` | Parashari significators (house lords, occupants, aspects) |
| `app/services/harness/yogas.py` | Yoga detection (Raj, Dhana, Pancha Mahapurusha, Gaja Kesari, etc.) |
| `app/services/harness/context_builder.py` | Section-specific context strings for LLM |
| `app/services/astrology_api/assembler.py` | Assembles all AstrologyAPI data into a single chart row |
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

## Database Schema

Tables: `profiles`, `charts`, `analyses`, `chat_messages`, `comparisons`

RLS is enabled on all tables. All user data is isolated by `user_id = auth.uid()`.

Key `charts` columns:
- `planets`, `dashas`, `ashtakavarga`, `kp_planet_significators`, `parashari_significators` — JSONB from AstrologyAPI + harness
- `yogas` — JSONB list of detected yogas (computed at creation time)
- `varshaphal` — JSONB dict keyed by year, caches annual chart analyses

## Environment Variables

```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ASTROLOGY_API_KEY=
ANTHROPIC_API_KEY=
CORS_ORIGINS=http://localhost:3000
```
