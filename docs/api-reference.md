# Cosmos Backend — API Reference

Base URL: `http://localhost:8000` (dev) — replace with your deployed URL in production.

All endpoints except `/health` require a Supabase JWT:
```
Authorization: Bearer <supabase_access_token>
```

---

## Auth

Get a token via Supabase Auth (from your frontend Supabase client, or for testing):

```bash
curl -X POST "https://<PROJECT>.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: <SUPABASE_ANON_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'
```

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## Health

### `GET /health`
```bash
curl http://localhost:8000/health
```
```json
{ "status": "ok", "version": "0.1.0" }
```

---

## Charts

### `POST /api/charts` — Create or return chart
Creates the birth chart on first call. Returns existing chart on subsequent calls (one chart per user).

```bash
curl -X POST http://localhost:8000/api/charts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Aadarsh",
    "dob": "1996-08-01",
    "tob": "06:30:00",
    "pob_name": "Mumbai, India",
    "pob_lat": 19.0760,
    "pob_lon": 72.8777,
    "timezone": 5.5
  }'
```

**Request body:**
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Person's name |
| `dob` | date `YYYY-MM-DD` | Date of birth |
| `tob` | time `HH:MM:SS` | Time of birth |
| `pob_name` | string | Place of birth (label only) |
| `pob_lat` | float | Latitude (-90 to 90) |
| `pob_lon` | float | Longitude (-180 to 180) |
| `timezone` | float | UTC offset e.g. `5.5` for IST, `-5.0` for EST |

**Response:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "Aadarsh",
  "dob": "1996-08-01",
  "tob": "06:30:00",
  "pob_name": "Mumbai, India",
  "pob_lat": 19.076,
  "pob_lon": 72.8777,
  "timezone": 5.5,
  "astro_details": {
    "ascendant": "Cancer",
    "ascendant_sign_num": 4,
    "tithi": "Ekadashi",
    "yoga": "Siddha",
    "karana": "Bava",
    "vaara": "Thursday"
  },
  "planets": {
    "sun": {
      "name": "Sun",
      "current_sign": 4,
      "sign": "Cancer",
      "full_degree": 15.32,
      "nakshatra": "Pushya",
      "nakshatra_pad": 2,
      "nakshatraLord": "Saturn",
      "house_parashari": 1,
      "isRetro": "false"
    },
    "moon": { "..." : "..." },
    "mars": { "..." : "..." },
    "mercury": { "..." : "..." },
    "jupiter": { "..." : "..." },
    "venus": { "..." : "..." },
    "saturn": { "..." : "..." },
    "rahu": { "..." : "..." },
    "ketu": { "..." : "..." }
  },
  "current_dasha": {
    "major": { "planet": "Jupiter", "start": "2020-01-01", "end": "2036-01-01" },
    "minor": { "planet": "Saturn", "start": "2024-06-01", "end": "2027-02-01" },
    "sub_minor": { "planet": "Mercury", "start": "2025-01-01", "end": "2025-07-01" }
  },
  "dashas": {
    "mahadashas": [
      { "planet": "Jupiter", "start": "2020-01-01", "end": "2036-01-01" }
    ]
  },
  "ashtakavarga": {
    "sun": { "aries": 4, "taurus": 3, "..." : "..." },
    "sarvashtaka": { "aries": 28, "taurus": 25, "..." : "..." }
  },
  "doshas": {
    "manglik": { "present": true, "status": "Manglik" },
    "kaal_sarp": { "present": false },
    "pitra": { "present": false },
    "sade_sati": { "active": false }
  },
  "yogas": [
    { "name": "Gaja Kesari Yoga", "present": true, "description": "..." }
  ],
  "parashari_significators": { "..." : "..." },
  "divisional_charts": {
    "D1": { "house_1": { "sign": 4, "sign_name": "Cancer" }, "..." : "..." },
    "D9": { "..." : "..." },
    "moon_chart": { "..." : "..." }
  },
  "panchang": {
    "tithi": "Ekadashi",
    "yoga": "Siddha",
    "karana": "Bava",
    "vaara": "Thursday"
  },
  "created_at": "2025-04-26T10:00:00Z"
}
```

---

### `GET /api/charts/{chart_id}` — Get chart
```bash
curl http://localhost:8000/api/charts/$CHART_ID \
  -H "Authorization: Bearer $TOKEN"
```
Returns same shape as `POST /api/charts`.

---

### `POST /api/charts/{chart_id}/load` — Refresh dynamic data
Recomputes today's transit snapshot and varshaphal for the given year. Call this on a schedule (e.g. daily on app open).

```bash
curl -X POST "http://localhost:8000/api/charts/$CHART_ID/load" \
  -H "Authorization: Bearer $TOKEN"

# For a specific year's varshaphal:
curl -X POST "http://localhost:8000/api/charts/$CHART_ID/load?year=2025" \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "loaded": true,
  "varshaphal_year": 2025,
  "transit_date": "2025-04-26"
}
```

---

## Analysis (16 sections)

### `POST /api/charts/{chart_id}/analyze/{section}` — Run analysis
Runs AI analysis for a section. Cached — subsequent calls return the same result instantly.

**Valid sections:** `personality` `mind` `career` `skills` `wealth` `foreign` `romance` `marriage` `business` `property` `health` `education` `parents` `siblings` `children` `spirituality`

```bash
curl -X POST http://localhost:8000/api/charts/$CHART_ID/analyze/career \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "id": "uuid",
  "chart_id": "uuid",
  "section": "career",
  "content": "Your 10th house lord Mercury sits in the 11th house...",
  "model": "claude-sonnet-4-6",
  "cached": false,
  "created_at": "2025-04-26T10:00:00Z"
}
```

---

### `GET /api/charts/{chart_id}/analyses` — List all analyses
```bash
curl http://localhost:8000/api/charts/$CHART_ID/analyses \
  -H "Authorization: Bearer $TOKEN"
```

```json
[
  {
    "id": "uuid",
    "chart_id": "uuid",
    "section": "career",
    "content": "...",
    "model": "claude-sonnet-4-6",
    "cached": false,
    "created_at": "2025-04-26T10:00:00Z"
  }
]
```

---

## Chat

### `POST /api/charts/{chart_id}/chat` — Streaming chat (SSE)
Returns a Server-Sent Events stream. Each chunk is `data: {"text": "..."}`. Stream ends with `data: [DONE]`.

```bash
curl -X POST http://localhost:8000/api/charts/$CHART_ID/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What does my 10th house say about career?"}' \
  --no-buffer
```

```
data: {"text": "Your"}
data: {"text": " 10th"}
data: {"text": " house..."}
data: [DONE]
```

**Frontend (JS):**
```js
const res = await fetch(`/api/charts/${chartId}/chat`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: 'Tell me about my career' }),
});
const reader = res.body.getReader();
const decoder = new TextDecoder();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const lines = decoder.decode(value).split('\n');
  for (const line of lines) {
    if (line.startsWith('data: ') && line !== 'data: [DONE]') {
      const { text } = JSON.parse(line.slice(6));
      // append text to UI
    }
  }
}
```

---

### `GET /api/charts/{chart_id}/chat/history`
```bash
curl http://localhost:8000/api/charts/$CHART_ID/chat/history \
  -H "Authorization: Bearer $TOKEN"
```

```json
[
  { "role": "user", "content": "What about my career?", "created_at": "..." },
  { "role": "assistant", "content": "Your 10th house...", "created_at": "..." }
]
```

---

## Transits

### `GET /api/charts/{chart_id}/transits` — Today's transit snapshot
Returns pre-loaded snapshot. Call `/load` first to populate it.

```bash
curl http://localhost:8000/api/charts/$CHART_ID/transits \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "date": "2025-04-26",
  "natal_asc_sign": 4,
  "planets": {
    "sun": {
      "transit_sign": 1,
      "sign_name": "Aries",
      "transit_house": 10,
      "nakshatra": "Ashwini",
      "retrograde": false,
      "dignity": "neutral"
    },
    "saturn": { "..." : "..." }
  }
}
```

---

### `GET /api/charts/{chart_id}/double-transit` — Jupiter + Saturn joint influence
```bash
curl http://localhost:8000/api/charts/$CHART_ID/double-transit \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "date": "2025-04-26",
  "houses": {
    "4": { "jupiter": true, "saturn": false, "both": false },
    "7": { "jupiter": false, "saturn": true, "both": false }
  }
}
```

---

### `GET /api/charts/{chart_id}/sadesati` — Sade Sati status
```bash
curl http://localhost:8000/api/charts/$CHART_ID/sadesati \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "active": true,
  "phase": "peak",
  "natal_moon_sign": 8,
  "saturn_transit_sign": 8,
  "saturn_transit_house_from_moon": 1,
  "severity_factors": ["Saturn transiting natal Moon sign"],
  "note": "Peak phase — Saturn directly on natal Moon"
}
```

---

## Timeline

### `GET /api/charts/{chart_id}/timeline` — Vimshottari dasha timeline
```bash
curl http://localhost:8000/api/charts/$CHART_ID/timeline \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "current_dasha": {
    "major": { "planet": "Jupiter", "start": "2020-01-01", "end": "2036-01-01" },
    "minor": { "planet": "Saturn", "start": "2024-06-01", "end": "2027-02-01" }
  },
  "timeline": [
    {
      "planet": "Jupiter",
      "start": "2020-01-01",
      "end": "2036-01-01",
      "antardashas": [
        { "planet": "Jupiter", "start": "2020-01-01", "end": "2022-02-01" },
        { "planet": "Saturn",  "start": "2022-02-01", "end": "2024-06-01" }
      ]
    }
  ]
}
```

---

## Muhurta

### `POST /api/charts/{chart_id}/muhurta` — Find auspicious dates
```bash
curl -X POST http://localhost:8000/api/charts/$CHART_ID/muhurta \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "marriage",
    "start_date": "2025-06-01",
    "end_date": "2025-12-31",
    "top_n": 5
  }'
```

```json
{
  "event_type": "marriage",
  "dates": [
    {
      "date": "2025-07-12",
      "score": 87.5,
      "tithi": "Panchami",
      "nakshatra": "Rohini",
      "vaara": "Friday",
      "notes": ["Rohini nakshatra favourable for marriage", "Friday ruled by Venus"]
    }
  ]
}
```

---

## Prediction

### `POST /api/charts/{chart_id}/predict` — Event prediction
Scans dasha windows + transits to find likely periods for a life event.

```bash
curl -X POST http://localhost:8000/api/charts/$CHART_ID/predict \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "When will I get married?",
    "start_date": "2025-01-01",
    "end_date": "2030-12-31"
  }'
```

```json
{
  "chart_id": "uuid",
  "question": "When will I get married?",
  "target_houses": [7, 2, 11],
  "windows": [
    {
      "md_lord": "Jupiter",
      "ad_lord": "Venus",
      "start": "2026-03-01",
      "end": "2026-09-01",
      "houses_activated": [7, 11],
      "match_score": 0.85,
      "transit_confirmed": true,
      "ashtakavarga_score": 32.5
    }
  ],
  "analysis": "The strongest window appears in early 2026...",
  "sadesati_active": false,
  "sadesati_phase": null
}
```

---

## Varshaphal (Annual Chart)

### `GET /api/charts/{chart_id}/varshaphal` — Annual solar return
Requires `/load?year=YYYY` to have been called first.

```bash
curl "http://localhost:8000/api/charts/$CHART_ID/varshaphal?year=2025" \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "chart_id": "uuid",
  "year": 2025,
  "age": 29,
  "natal_ascendant": "Cancer",
  "year_lord": "venus",
  "annual_planets": {
    "sun": {
      "sign": 4,
      "sign_name": "cancer",
      "house": 1,
      "nakshatra": "Pushya",
      "retrograde": false,
      "dignity": "neutral"
    }
  },
  "content": "2025 is governed by Venus as the year lord...",
  "cached": false
}
```

---

## Compatibility

### `POST /api/compatibility/` — Compute compatibility
Both charts must belong to the requesting user.

```bash
curl -X POST http://localhost:8000/api/compatibility/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "chart_id_1": "uuid-a",
    "chart_id_2": "uuid-b"
  }'
```

```json
{
  "chart_id_1": "uuid-a",
  "chart_id_2": "uuid-b",
  "ashtakoot": {
    "total": 28,
    "moon_sign_a": 4,
    "moon_sign_b": 7,
    "moon_nakshatra_a": "Pushya",
    "moon_nakshatra_b": "Vishakha",
    "scores": {
      "varna":     { "score": 1, "max": 1 },
      "vashya":    { "score": 2, "max": 2 },
      "tara":      { "score": 3, "max": 3 },
      "yoni":      { "score": 4, "max": 4 },
      "graha_maitri": { "score": 5, "max": 5 },
      "gana":      { "score": 6, "max": 6 },
      "bhakoot":   { "score": 7, "max": 7 },
      "nadi":      { "score": 0, "max": 8 }
    },
    "doshas": ["nadi_dosha"]
  },
  "analysis": "With 28/36 points, this is a strong match...",
  "cached": false
}
```

---

### `GET /api/compatibility/{chart_id_1}/{chart_id_2}` — Get cached report
```bash
curl http://localhost:8000/api/compatibility/$CHART_ID_1/$CHART_ID_2 \
  -H "Authorization: Bearer $TOKEN"
```
Returns same shape as `POST /api/compatibility/` with `"cached": true`.

---

## PDF Report

### `GET /api/charts/{chart_id}/report.pdf` — Download PDF
```bash
curl http://localhost:8000/api/charts/$CHART_ID/report.pdf \
  -H "Authorization: Bearer $TOKEN" \
  -o report.pdf
```
Returns a binary PDF file (`Content-Type: application/pdf`).

---

## Error Responses

All errors follow FastAPI's standard shape:
```json
{ "detail": "Human-readable error message" }
```

| Status | Meaning |
|--------|---------|
| `401` | Missing or invalid JWT |
| `404` | Chart / resource not found |
| `422` | Validation error or prerequisite not met (e.g. `/load` not called) |
| `502` | Swiss Ephemeris computation failed |
