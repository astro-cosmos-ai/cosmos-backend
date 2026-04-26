"""Vimshottari dasha computation — 5 levels (MD/AD/PD/SD/SSD)."""
from datetime import datetime, timedelta, timezone

DASHA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS: dict[str, float] = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}
DASHA_TOTAL = 120.0
_YEAR_DAYS = 365.25


def _add_years(dt: datetime, years: float) -> datetime:
    return dt + timedelta(days=years * _YEAR_DAYS)


def _sub_periods(lord: str, start: datetime, duration_years: float) -> list[dict]:
    lord_idx = DASHA_ORDER.index(lord)
    out: list[dict] = []
    cursor = start
    for i in range(9):
        sub = DASHA_ORDER[(lord_idx + i) % 9]
        dur = (DASHA_YEARS[sub] * duration_years) / DASHA_TOTAL
        end = _add_years(cursor, dur)
        out.append({"planet": sub, "start": cursor.isoformat(), "end": end.isoformat()})
        cursor = end
    return out


def compute_vimshottari(birth_utc: datetime, moon_lon: float) -> tuple[list[dict], dict]:
    """
    Returns (mahadashas, current_dasha).
    mahadashas: list of 9 {planet, start, end}
    current_dasha: {major, minor, sub_minor, sub_sub_minor, sub_sub_sub_minor} each {planet, start, end}
    """
    span = 360 / 27
    norm_moon = ((moon_lon % 360) + 360) % 360
    nak_idx = int(norm_moon / span)
    pos_in_nak = norm_moon - nak_idx * span
    fraction_elapsed = pos_in_nak / span
    fraction_remaining = 1 - fraction_elapsed

    start_lord_idx = nak_idx % 9
    start_lord = DASHA_ORDER[start_lord_idx]
    start_lord_years = DASHA_YEARS[start_lord]

    # Natural start of the first mahadasha (before birth by elapsed fraction)
    natural_start = _add_years(birth_utc, -start_lord_years * fraction_elapsed)

    mahadashas: list[dict] = []
    cursor = natural_start
    for i in range(9):
        lord = DASHA_ORDER[(start_lord_idx + i) % 9]
        end = _add_years(cursor, DASHA_YEARS[lord])
        display_start = birth_utc if i == 0 else cursor
        mahadashas.append({"planet": lord, "start": display_start.isoformat(), "end": end.isoformat()})
        cursor = end

    empty = {"planet": "", "start": "", "end": ""}
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    maj_idx = next(
        (i for i, d in enumerate(mahadashas) if datetime.fromisoformat(d["start"]) <= now < datetime.fromisoformat(d["end"])),
        -1,
    )
    if maj_idx == -1:
        return mahadashas, {"major": empty, "minor": empty, "sub_minor": empty, "sub_sub_minor": empty, "sub_sub_sub_minor": empty}

    major = mahadashas[maj_idx]
    maj_natural_start = natural_start if maj_idx == 0 else datetime.fromisoformat(major["start"])
    maj_years = DASHA_YEARS[major["planet"]]

    antardashas = _sub_periods(major["planet"], maj_natural_start, maj_years)
    minor = next((a for a in antardashas if datetime.fromisoformat(a["start"]) <= now < datetime.fromisoformat(a["end"])), empty)

    sub_minor = empty
    sub_sub_minor = empty
    sub_sub_sub_minor = empty

    if minor.get("planet"):
        ant_years = (DASHA_YEARS[minor["planet"]] * maj_years) / DASHA_TOTAL
        pratyantars = _sub_periods(minor["planet"], datetime.fromisoformat(minor["start"]), ant_years)
        sub_minor = next((p for p in pratyantars if datetime.fromisoformat(p["start"]) <= now < datetime.fromisoformat(p["end"])), empty)

        if sub_minor.get("planet"):
            pt_years = (DASHA_YEARS[sub_minor["planet"]] * ant_years) / DASHA_TOTAL
            sookshmas = _sub_periods(sub_minor["planet"], datetime.fromisoformat(sub_minor["start"]), pt_years)
            sub_sub_minor = next((s for s in sookshmas if datetime.fromisoformat(s["start"]) <= now < datetime.fromisoformat(s["end"])), empty)

            if sub_sub_minor.get("planet"):
                sk_years = (DASHA_YEARS[sub_sub_minor["planet"]] * pt_years) / DASHA_TOTAL
                pranas = _sub_periods(sub_sub_minor["planet"], datetime.fromisoformat(sub_sub_minor["start"]), sk_years)
                sub_sub_sub_minor = next((p for p in pranas if datetime.fromisoformat(p["start"]) <= now < datetime.fromisoformat(p["end"])), empty)

    return mahadashas, {
        "major": major,
        "minor": minor,
        "sub_minor": sub_minor,
        "sub_sub_minor": sub_sub_minor,
        "sub_sub_sub_minor": sub_sub_sub_minor,
    }
