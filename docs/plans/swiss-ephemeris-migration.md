# Plan: Replace AstrologyAPI with Swiss Ephemeris (pyswisseph)

**Status:** not started
**Estimated effort:** 2–4 days, split across 2 PRs
**Reference implementation:** `cosmos-app/src/lib/swiss.ts` (~800 lines TypeScript) — proves the math is correct; this plan ports it to Python.

---

## Goal

Stop calling AstrologyAPI for every chart creation. Compute everything locally using Swiss Ephemeris, the same engine used by professional Vedic tools (Solar Fire, Jagannatha Hora) and by the sibling `cosmos-app`.

## Why

| | AstrologyAPI today | pyswisseph after switch |
|---|---|---|
| Latency per chart | 1.5–3s (HTTP) | 30–80ms (in-process C call) |
| Cost per chart | $ per call | $0 |
| Rate limit | Yes (`Semaphore(5)`) | None |
| Third-party outage risk | Yes | None |
| Determinism in tests | Network-dependent fixtures | Pure function — easy to test |
| Same engine as cosmos-app | No | Yes — cross-app consistency |

The hard ceiling on chart creation latency goes away, which unlocks: bulk chart generation, batch compatibility, transit timeline scans, and a much faster feedback loop in development.

---

## What changes (and what does not)

**Stays the same:**
- `chart_json` shape — same keys, same types. The harness, agents, registry, and validators don't change at all.
- `app/services/harness/*` — all the Parashari rule logic stays untouched. The harness is downstream of the assembler.
- All routes, all prompts, all migrations.
- Cache key strategy in `analyses` table.

**Goes away:**
- `app/services/astrology_api/client.py`
- `app/services/astrology_api/assembler.py` (its current AstrologyAPI-flavored normalization)
- `ASTROLOGY_API_KEY` env var
- The `Semaphore(5)` concurrency cap (no longer relevant)

**Gets added:**
- `app/services/swiss/` — new computation layer (replaces astrology_api/)
- `pyswisseph` dep in `pyproject.toml`
- Swiss Ephemeris data files (`*.se1`) bundled at `app/services/swiss/ephe/` (~30 MB)
- A few config knobs in `app/core/config.py` (ayanamsa, node mode)

---

## Migration in two PRs

### PR 1 — Build the Swiss layer behind a feature flag (~2 days)

Goal: side-by-side execution. Both AstrologyAPI and Swiss produce a `chart_json`; a flag picks which one feeds the harness. Nothing is deleted.

1. **Add deps**
   - `pyproject.toml` → `pyswisseph = "^2.10"` (or latest). Lock with `uv lock`.
   - Verify wheel exists for your deploy target (Linux x86_64 / arm64). If on Vercel Python, smoke-test the build early.

2. **Bundle ephemeris files**
   - Download `sepl_*.se1`, `semo_*.se1`, `seas_*.se1` from astro.com (ranges covering 1800–2100 are usually enough for natal use).
   - Store at `app/services/swiss/ephe/`. Add to git LFS if size > 100 MB total — usually not needed for the standard set.
   - Set `swe.set_ephe_path(...)` once at module load.

3. **Create `app/services/swiss/` layout**
   ```
   app/services/swiss/
   ├── __init__.py
   ├── ephe/                      # .se1 files (gitignored if large; otherwise committed)
   ├── calculator.py              # entrypoint: produce chart_json
   ├── ephemeris.py               # raw planet/house/ascendant computation via pyswisseph
   ├── vimshottari.py             # 5-level dasha computation (port from cosmos-app)
   ├── ashtakavarga.py            # bindus per planet/house (port from cosmos-app)
   ├── kp.py                      # sub-lords + planet/house significators (port from cosmos-app)
   ├── doshas.py                  # manglik, kaal sarp, sade sati live, pitra
   ├── calendar.py                # tithi, vara, yoga, karana (for muhurta)
   └── ayanamsa.py                # ayanamsa selection + sidereal mode setup
   ```

4. **Port the JS implementation**
   - Source: `cosmos-app/src/lib/swiss.ts` (~800 lines). Functions to port:
     - `generateChart(input)` → `calculator.compute_chart(birth_input)`
     - Vimshottari dasha tree (5 levels: MD/AD/PD/SD/SSD)
     - Ashtakavarga bindu computation
     - KP sub-lord chains
     - Doshas (Manglik %, Kaal Sarp, **live Sade Sati** — queries Saturn at current UTC)
     - Tithi / Vara / Nakshatra / Yoga / Karana
   - Port style: keep function names and constants identical to the JS where reasonable, so future drift is easy to spot.

5. **Match the assembled `chart_json` contract**
   - Read `app/services/astrology_api/assembler.py` carefully. Note every key it emits, every type, every nested shape.
   - `swiss/calculator.py` must produce **byte-for-byte identical structure** for the keys the harness reads (`planets`, `astro_details`, `current_dasha`, `dashas`, `kp_planet_significators`, `kp_house_significators`, `ashtakavarga`).
   - The harness already adds `parashari_significators` and `yogas` post-assembly — those are unaffected.

6. **Feature flag**
   - `app/core/config.py` → `chart_engine: Literal["astrology_api", "swiss"] = "astrology_api"` (default still old).
   - `app/services/astrology_api/assembler.py` → branch on `settings.chart_engine`. If `"swiss"`, dispatch to `swiss.calculator.compute_chart()`. Otherwise legacy path.
   - **Both paths must produce the same `chart_json` shape** — that's the contract.

7. **Tests**
   - `tests/test_swiss_calculator.py` — feed a known birth (one of the cosmos-app PRD examples) and assert key fields against expected values (hand-computed or cross-checked against a trusted tool).
   - `tests/test_swiss_parity.py` — generates the same chart via both engines (skipped in CI unless both keys present) and diffs.

8. **Verification harness**
   - Pick 5–10 birth charts spanning latitudes (Delhi, Mumbai, Chennai, NYC, London, Sydney). Include at least one in southern hemisphere and one with retrograde Mercury at birth.
   - For each: generate via AstrologyAPI, generate via Swiss with `chart_engine="swiss"`, deep-diff the JSONs.
   - **Acceptance criteria:**
     - Whole-sign house assignments: identical.
     - Planet signs: identical.
     - Planet degrees: within 0.05° (tighter is better; differences usually trace to ayanamsa or node mode mismatch).
     - Vimshottari current Mahadasha: identical name; period start/end within 1 day.
     - Nakshatra and pada: identical.
     - Ashtakavarga totals per house: identical (should match exactly — pure rule logic).
     - KP sub-lords: identical (if AstrologyAPI uses Lahiri-based KP; verify their docs).

### PR 2 — Cut over and delete (~half a day)

Only after PR 1 is merged, the flag has been flipped to `swiss` in staging, and a soak period (1–2 weeks of real chart creation under the new engine) shows no regressions.

1. **Flip the default**
   - `app/core/config.py` → `chart_engine: Literal[...] = "swiss"`.

2. **Delete AstrologyAPI integration**
   - `rm -rf app/services/astrology_api/`
   - Drop `ASTROLOGY_API_KEY` from `.env.example` and `app/core/config.py`.
   - Remove the `httpx.AsyncClient` for AstrologyAPI from any imports.
   - Remove the `Semaphore(5)` references — they no longer apply.

3. **Update assembler/dispatcher**
   - The assembler now just calls `swiss.calculator.compute_chart()` directly. The branch on `chart_engine` goes away.
   - Consider renaming `app/services/astrology_api/` references in service docstrings.

4. **Update docs**
   - `cosmos-backend/CLAUDE.md` — strike the AstrologyAPI lines.
   - `cosmos-backend/.claude/rules/harness-first.md` — update the data-flow header.
   - `cosmos-backend/README.md` — replace the "Astrology data: AstrologyAPI" line with "Astrology data: Swiss Ephemeris (pyswisseph)".

5. **Regression sweep**
   - Re-run all existing tests.
   - Hit `POST /api/charts` for a known fixture and compare to the snapshot saved in PR 1.
   - Run `/check-harness` slash command — invariants should still pass.

---

## Configuration knobs (set once, document them)

```python
# app/core/config.py additions
ayanamsa: Literal["lahiri", "krishnamurti", "raman", "yukteshwar"] = "lahiri"
node_mode: Literal["mean", "true"] = "mean"      # Rahu/Ketu calculation
swiss_ephe_path: str = "app/services/swiss/ephe"
```

In `swiss/__init__.py`, set up sidereal mode once:

```python
import swisseph as swe

def configure(ayanamsa: str, ephe_path: str) -> None:
    swe.set_ephe_path(ephe_path)
    sid_mode = {
        "lahiri": swe.SIDM_LAHIRI,
        "krishnamurti": swe.SIDM_KRISHNAMURTI,
        "raman": swe.SIDM_RAMAN,
        "yukteshwar": swe.SIDM_YUKTESHWAR,
    }[ayanamsa]
    swe.set_sid_mode(sid_mode)
```

**Why pin ayanamsa explicitly:** AstrologyAPI defaults to Lahiri. If you flip silently to a different default, every chart shifts ~50 arc-minutes and users won't understand why their dasha changed. Match Lahiri unless you have a reason not to.

---

## Risks & catches (read these before starting)

1. **Timezone precision matters more.** AstrologyAPI is forgiving with rough timezone offsets. Swiss Ephemeris is exact — a wrong DST flag or LMT/IST mixup produces a visibly different chart. Audit your timezone resolution path before cutover. (cosmos-app currently uses `lon/15`, which is a known weakness; cosmos-backend should do better — use the actual IANA tz of the birth place.)
2. **Ayanamsa mismatch silently shifts everything.** Pin explicitly per the config above. Don't rely on defaults.
3. **Mean vs True Node** for Rahu/Ketu — AstrologyAPI uses mean (typically). Match it (`swe.MEAN_NODE`) unless you decide otherwise.
4. **KP sub-lord computation has multiple valid implementations.** The cosmos-app port is one. Cross-check against a second source (KP Stellar, Jagannatha Hora) for a known chart before declaring parity.
5. **Native C extension at deploy time.** `pyswisseph` ships wheels for major platforms. If you deploy the backend on Vercel Python runtime, ARM-only hosts, or Lambda, build a smoke-test chart in CI to catch wheel issues early.
6. **Ephemeris file licensing.** Swiss Ephemeris is GPL. The `.se1` data files distributed by astro.com are free to bundle in non-commercial use; for commercial use the AGPL license terms or the commercial license apply. Verify before shipping if this is a paid product.
7. **Solar return / varshaphal** — implemented as "find moment when Sun returns to natal longitude in target year, compute chart at that moment." sweph supports this directly via iterative search. Port from cosmos-app if it has it; otherwise straightforward to write.
8. **Live Sade Sati** — cosmos-app queries Saturn at current UTC every chart generation. This is correct behavior but means chart_json has a time-varying field. Cosmos-backend currently has `app/services/sadesati_service.py` that queries this on demand instead — likely the better split. Don't include Sade-Sati live results in the persisted `chart_json`; let the dedicated service compute it on each request.

---

## Open questions (resolve at implementation time)

1. **Deploy target?** Confirm pyswisseph wheels exist for your environment. Check `pip install pyswisseph` works on a fresh container of your prod image.
2. **Which Vedic ayanamsa?** Default to Lahiri. Confirm with user before locking it in.
3. **Are there charts already in the `charts` table?** If yes, post-cutover their cached `chart_json` was produced by AstrologyAPI. Two options: regenerate them (one-off batch job) or leave them (existing analyses keyed off the old hash will still hit cache). Pick one before PR 2.
4. **Does `report_service.py` (PDF) read any AstrologyAPI-only field?** Audit before cutover. If so, that field must come from Swiss too.
5. **What's in `app/services/varshaphal_service.py` today?** Confirm whether it makes a separate AstrologyAPI call or works off the natal `chart_json`. If separate, port to sweph in PR 1.

---

## Out of scope for this migration

- Adding new astrological techniques. This is a like-for-like swap. New features (Tajik aspects, Jaimini char dasha, prashna, KP horary) go in separate PRs.
- Changing the harness or any LLM prompt. The harness reads the same `chart_json` either way.
- Frontend changes. cosmos-app already uses sweph; cosmos-backend's frontend (whichever it ends up being) doesn't care which engine produced the chart.
- Deleting `cosmos-app`'s `lib/swiss.ts`. Even if cosmos-app is later wired to call cosmos-backend, the JS implementation is fine to keep as a fallback or for offline-first behavior.

---

## How this composes with the wiki-integration plan

If/when you implement the wiki plan first:
- Add a `Cosmos: chart engine` page to the wiki that documents the engine choice, ayanamsa, node mode, and key ephemeris versions in use.
- After this migration lands, run `wiki-update` to refresh the chart-pipeline page (the AstrologyAPI step disappears, swiss/ replaces it).

If you implement this migration first:
- The wiki plan's "chart pipeline" page should reflect the Swiss-only flow rather than the dual-flagged transitional state.

Either order works. I'd do the wiki plan first because it's purely additive and gives you a place to document the migration as it happens.
