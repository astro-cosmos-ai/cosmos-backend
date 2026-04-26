"""
Processes stored dasha JSON into a structured timeline with deterministic event markers.
Zero LLM calls — all computation is rule-based.
"""
from datetime import date, timedelta

# House combination → life event mapping (PRD Section 8.2)
HOUSE_EVENT_MAP = [
    (frozenset([2, 7, 11]),      "Marriage / major financial partnership"),
    (frozenset([2, 6, 10, 11]),  "Career advancement / promotion / income rise"),
    (frozenset([3, 9, 12]),      "Foreign travel / relocation"),
    (frozenset([4, 11]),         "Property acquisition / vehicle purchase"),
    (frozenset([5, 9]),          "Higher education / childbirth / spiritual initiation"),
    (frozenset([5, 8, 11]),      "Speculative gains / sudden windfall"),
    (frozenset([1, 5, 9]),       "Personal growth / luck / merit activation"),
    (frozenset([1, 6, 8]),       "Health concern / surgery / accident risk"),
    (frozenset([6, 8, 12]),      "Loss / hospitalization / debt / legal trouble"),
    (frozenset([7, 10, 11]),     "Business success / partnership gains"),
    (frozenset([3, 10, 11]),     "Career through self-effort / communication success"),
    (frozenset([8, 12]),         "Transformation / ending of a chapter"),
]

# Vimshottari dasha years per planet (total = 120)
_DASHA_YEARS: dict[str, int] = {
    "sun": 6, "moon": 10, "mars": 7, "rahu": 18,
    "jupiter": 16, "saturn": 19, "mercury": 17, "ketu": 7, "venus": 20,
}

# Standard Vimshottari sequence
_DASHA_SEQUENCE = ["sun", "moon", "mars", "rahu", "jupiter", "saturn", "mercury", "ketu", "venus"]


def _houses_activated(dasha_lord: str, kp_planet_sig: dict | list | None) -> set[int]:
    if not kp_planet_sig:
        return set()
    if isinstance(kp_planet_sig, list):
        for item in kp_planet_sig:
            if isinstance(item, dict) and item.get("planet", "").lower() == dasha_lord.lower():
                houses = item.get("significators") or item.get("houses") or []
                return set(int(h) for h in houses if str(h).isdigit())
    elif isinstance(kp_planet_sig, dict):
        entry = kp_planet_sig.get(dasha_lord.lower()) or kp_planet_sig.get(dasha_lord.title())
        if entry:
            houses = entry if isinstance(entry, list) else (entry.get("houses") or [])
            return set(int(h) for h in houses if str(h).isdigit())
    return set()


def _event_markers(activated_houses: set[int]) -> list[str]:
    events = []
    for house_set, event in HOUSE_EVENT_MAP:
        if house_set.issubset(activated_houses):
            events.append(event)
    return events


def _parse_date(date_str: str) -> date | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(date_str[:10], fmt).date()
        except ValueError:
            continue
    return None


def _compute_antardashas(
    md_lord: str,
    md_start: date,
    md_end: date,
    kp_planet_sig: dict | list | None,
    parashari_sig: dict,
) -> list[dict]:
    """
    Compute 9 antardasha periods within a mahadasha using Vimshottari proportional durations.
    Sequence starts from the mahadasha lord.
    """
    md_years = _DASHA_YEARS.get(md_lord.lower(), 0)
    if md_years == 0:
        return []

    # Start from the mahadasha lord in the sequence
    try:
        start_idx = _DASHA_SEQUENCE.index(md_lord.lower())
    except ValueError:
        return []

    antardashas = []
    cursor = md_start

    for i in range(9):
        ad_lord = _DASHA_SEQUENCE[(start_idx + i) % 9]
        ad_years = _DASHA_YEARS[ad_lord]

        # Duration = (MD_years × AD_years) / 120 years, as days
        total_days = (md_end - md_start).days
        ad_fraction = ad_years / 120.0
        ad_days = int(total_days * ad_fraction)

        ad_end = cursor + timedelta(days=ad_days)
        if i == 8:
            ad_end = md_end  # ensure no rounding gap

        kp_houses = _houses_activated(ad_lord, kp_planet_sig)
        parashari_rules = [int(h) for h, data in parashari_sig.items() if data.get("lord", "").lower() == ad_lord]
        all_activated = kp_houses | set(parashari_rules)

        antardashas.append({
            "lord": ad_lord.title(),
            "start_date": cursor.isoformat(),
            "end_date": ad_end.isoformat(),
            "kp_signifies_houses": list(kp_houses),
            "parashari_rules_houses": parashari_rules,
            "event_themes": _event_markers(all_activated),
        })
        cursor = ad_end

    return antardashas


def build_timeline(chart_row: dict) -> dict:
    dashas = chart_row.get("dashas") or {}
    vimshottari = dashas.get("vimshottari") or []
    kp_planet_sig = chart_row.get("kp_planet_significators")
    parashari_sig = chart_row.get("parashari_significators") or {}
    current_dasha = chart_row.get("current_dasha") or {}

    current_md = (current_dasha.get("major_dasha") or current_dasha.get("maha_dasha") or "").lower()
    current_ad = (current_dasha.get("antar_dasha") or current_dasha.get("antar") or "").lower()

    mahadashas = []
    for md in (vimshottari if isinstance(vimshottari, list) else []):
        if not isinstance(md, dict):
            continue
        lord = (md.get("dasha") or md.get("planet") or md.get("lord") or "").lower()
        start_str = md.get("start") or md.get("start_date") or ""
        end_str = md.get("end") or md.get("end_date") or ""

        # KP: houses this lord signifies
        kp_houses = _houses_activated(lord, kp_planet_sig)

        # Parashari: find which houses this lord is lord of
        parashari_rules = [int(h) for h, data in parashari_sig.items() if data.get("lord", "").lower() == lord]

        all_activated = kp_houses | set(parashari_rules)
        events = _event_markers(all_activated)
        is_current = lord == current_md

        # Compute antardashas if we have parseable dates
        antardashas = []
        md_start = _parse_date(start_str)
        md_end = _parse_date(end_str)
        if md_start and md_end:
            antardashas = _compute_antardashas(lord, md_start, md_end, kp_planet_sig, parashari_sig)
            # Mark current antardasha
            for ad in antardashas:
                ad["is_current"] = (is_current and ad["lord"].lower() == current_ad)

        mahadashas.append({
            "lord": lord.title(),
            "start_date": start_str,
            "end_date": end_str,
            "is_current": is_current,
            "parashari_rules_houses": parashari_rules,
            "kp_signifies_houses": list(kp_houses),
            "event_themes": events,
            "antardashas": antardashas,
        })

    return {
        "mahadashas": mahadashas,
        "current_dasha": current_dasha,
    }
