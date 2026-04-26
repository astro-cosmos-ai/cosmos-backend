"""
Dasha window scanner: finds Vimshottari MD/AD periods where the combined
house significations cover a target set of houses.
Zero LLM calls — pure rule-based computation.
"""
from datetime import date

from app.services.timeline_service import _houses_activated, _parse_date

# Question keyword → target houses for prediction
QUESTION_HOUSE_MAP: dict[str, list[int]] = {
    "marriage":        [2, 7, 11],
    "wed":             [2, 7, 11],
    "spouse":          [2, 7, 11],
    "relationship":    [2, 7, 11],
    "partner":         [2, 7, 11],
    "job":             [2, 6, 10, 11],
    "career":          [2, 6, 10, 11],
    "promotion":       [2, 6, 10, 11],
    "employment":      [6, 10],
    "business":        [2, 7, 10, 11],
    "foreign":         [3, 9, 12],
    "abroad":          [3, 9, 12],
    "travel":          [3, 9, 12],
    "immigration":     [9, 12],
    "child":           [2, 5, 11],
    "children":        [2, 5, 11],
    "baby":            [2, 5, 11],
    "property":        [4, 11],
    "house":           [4, 11],
    "land":            [4, 11],
    "education":       [4, 5, 9],
    "study":           [4, 5, 9],
    "degree":          [4, 5, 9],
    "health":          [1, 6, 8],
    "illness":         [6, 8, 12],
    "surgery":         [6, 8],
    "wealth":          [2, 5, 9, 11],
    "money":           [2, 11],
    "lottery":         [5, 8, 11],
    "spiritual":       [9, 12],
    "spiritual growth":[9, 12],
}


def classify_question_to_houses(question: str) -> list[int] | None:
    """
    Keyword match against QUESTION_HOUSE_MAP.
    Returns first matching house list, or None if no keyword matches.
    """
    q = question.lower()
    for keyword, houses in QUESTION_HOUSE_MAP.items():
        if keyword in q:
            return houses
    return None


def scan_dasha_windows(
    chart_row: dict,
    target_houses: list[int],
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Iterates all MD/AD windows in the stored Vimshottari dasha.
    For each window: computes union of MD lord + AD lord signified houses.
    If target_houses ⊆ union → candidate window.

    Returns sorted list (earliest first) of:
      {md_lord, ad_lord, start, end, houses_activated, match_score}
    """
    dashas = chart_row.get("dashas") or {}
    vimshottari = dashas.get("vimshottari") or []
    kp_planet_sig = chart_row.get("kp_planet_significators")
    parashari_sig = chart_row.get("parashari_significators") or {}
    target_set = set(target_houses)

    candidates: list[dict] = []

    for md in (vimshottari if isinstance(vimshottari, list) else []):
        if not isinstance(md, dict):
            continue

        md_lord = (md.get("dasha") or md.get("planet") or md.get("lord") or "").lower()
        md_start_str = md.get("start") or md.get("start_date") or ""
        md_end_str = md.get("end") or md.get("end_date") or ""
        md_start = _parse_date(md_start_str)
        md_end = _parse_date(md_end_str)

        if not md_start or not md_end:
            continue

        # MD lord's houses
        md_kp = _houses_activated(md_lord, kp_planet_sig)
        md_para = {int(h) for h, d in parashari_sig.items() if d.get("lord", "").lower() == md_lord}
        md_houses = md_kp | md_para

        # Check antardashas
        antardashas = md.get("antardashas") or []
        if not antardashas:
            # Fall back to computed antardashas from timeline_service
            from app.services.timeline_service import _compute_antardashas
            if md_start and md_end:
                antardashas = _compute_antardashas(md_lord, md_start, md_end, kp_planet_sig, parashari_sig)

        for ad in (antardashas if isinstance(antardashas, list) else []):
            if not isinstance(ad, dict):
                continue

            ad_lord = (ad.get("lord") or "").lower()
            ad_start = _parse_date(ad.get("start_date") or ad.get("start") or "")
            ad_end = _parse_date(ad.get("end_date") or ad.get("end") or "")

            if not ad_start or not ad_end:
                continue

            # Filter by date range
            if ad_end < start_date or ad_start > end_date:
                continue

            ad_kp = _houses_activated(ad_lord, kp_planet_sig)
            ad_para = {int(h) for h, d in parashari_sig.items() if d.get("lord", "").lower() == ad_lord}
            ad_houses = ad_kp | ad_para

            all_houses = md_houses | ad_houses

            if not target_set.issubset(all_houses):
                continue

            # Match score: how many extra target houses beyond minimum are activated
            overlap = len(target_set & all_houses)
            match_score = overlap / len(target_set) if target_set else 0

            candidates.append({
                "md_lord": md_lord.title(),
                "ad_lord": ad_lord.title(),
                "start": str(ad_start),
                "end": str(ad_end),
                "houses_activated": sorted(all_houses),
                "match_score": round(match_score, 2),
                "transit_confirmed": False,  # updated later by confirm_node
                "ashtakavarga_score": None,  # updated later
            })

    candidates.sort(key=lambda w: w["start"])
    return candidates


def rank_windows(
    windows: list[dict],
    double_transit_map: dict[int, dict],
    av_assessments: dict[str, dict],
    target_houses: list[int],
) -> list[dict]:
    """
    Re-scores windows using double transit confirmation and ashtakavarga quality.
    Mutates windows in place and returns re-sorted list.
    """
    for w in windows:
        # Check if Jupiter or Saturn double-transits any target house
        for h in target_houses:
            dt = double_transit_map.get(h) or {}
            if dt.get("double"):
                w["transit_confirmed"] = True
                break

        # Average ashtakavarga quality for key planets (Jupiter, Saturn, MD lord, AD lord)
        scores = []
        for pname in [w["md_lord"].lower(), w["ad_lord"].lower(), "jupiter", "saturn"]:
            av = av_assessments.get(pname) or {}
            bindus = av.get("bindus")
            if bindus is not None:
                scores.append(bindus)
        w["ashtakavarga_score"] = round(sum(scores) / len(scores), 1) if scores else None

        # Boost match_score for transit-confirmed windows
        if w["transit_confirmed"]:
            w["match_score"] = min(1.0, w["match_score"] + 0.2)

    windows.sort(key=lambda w: (-w["match_score"], w["start"]))
    return windows
