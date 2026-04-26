"""
Ashtakoot compatibility computation.
All 8 Kootas computed from Moon nakshatra and Moon sign data stored in chart JSONB.
Zero LLM calls — pure rule-based computation.
"""

# Nakshatra index 1–27 (Ashwini=1, Bharani=2, ... Revati=27)
# Nakshatra → Nadi (0=Adi, 1=Madhya, 2=Antya)
_NADI = [
    0, 1, 2, 0, 1, 2, 0, 1, 2,   # 1–9
    0, 1, 2, 0, 1, 2, 0, 1, 2,   # 10–18
    0, 1, 2, 0, 1, 2, 0, 1, 2,   # 19–27
]

# Nakshatra → Gana (0=Deva, 1=Manushya, 2=Rakshasa)
_GANA = [
    0, 2, 0, 1, 1, 2, 0, 2, 0,   # 1–9
    2, 0, 0, 2, 0, 1, 2, 1, 2,   # 10–18
    0, 1, 1, 0, 2, 0, 2, 1, 0,   # 19–27
]

# Nakshatra → Yoni (0=Ashwa, 1=Gaja, 2=Mesh, 3=Sarpa, 4=Shvan, 5=Marjara,
#                   6=Mushaka, 7=Gau, 8=Mahisha, 9=Vyaaghra, 10=Mriga, 11=Vanar, 12=Nakula, 13=Simha)
_YONI = [
    0, 1, 2, 3, 4, 5, 6, 7, 4, 8, 9, 10, 10, 1, 9, 5, 11, 12,
    6, 2, 13, 0, 13, 7, 11, 8, 3,
]

# Yoni compatibility matrix (yoni_a, yoni_b) → True if friendly
_YONI_FRIENDLY = {
    frozenset([0, 0]), frozenset([1, 1]), frozenset([2, 2]), frozenset([3, 3]),
    frozenset([4, 4]), frozenset([5, 5]), frozenset([6, 6]), frozenset([7, 7]),
    frozenset([8, 8]), frozenset([9, 9]), frozenset([10, 10]), frozenset([11, 11]),
    frozenset([12, 12]), frozenset([13, 13]),
    frozenset([0, 2]),  # Ashwa-Mesh
    frozenset([4, 10]), # Shvan-Mriga
    frozenset([1, 8]),  # Gaja-Mahisha
    frozenset([9, 13]), # Vyaaghra-Simha
}

# Planet/sign lords for Graha Maitri — sign (1-indexed) → lord
_SIGN_LORD = {
    1: "mars", 2: "venus", 3: "mercury", 4: "moon", 5: "sun",
    6: "mercury", 7: "venus", 8: "mars", 9: "jupiter", 10: "saturn",
    11: "saturn", 12: "jupiter",
}

# Planet friendships: (lord_a, lord_b) → 2=great friend, 1=friend/neutral, 0=enemy
_PLANET_RELATION = {
    ("sun", "moon"): 2, ("sun", "mars"): 2, ("sun", "mercury"): 1,
    ("sun", "jupiter"): 2, ("sun", "venus"): 0, ("sun", "saturn"): 0,
    ("moon", "sun"): 2, ("moon", "mercury"): 1, ("moon", "mars"): 1,
    ("moon", "jupiter"): 2, ("moon", "venus"): 1, ("moon", "saturn"): 0,
    ("mars", "sun"): 2, ("mars", "moon"): 1, ("mars", "mercury"): 0,
    ("mars", "jupiter"): 2, ("mars", "venus"): 0, ("mars", "saturn"): 0,
    ("mercury", "sun"): 1, ("mercury", "moon"): 0, ("mercury", "mars"): 0,
    ("mercury", "jupiter"): 1, ("mercury", "venus"): 2, ("mercury", "saturn"): 1,
    ("jupiter", "sun"): 2, ("jupiter", "moon"): 2, ("jupiter", "mars"): 2,
    ("jupiter", "mercury"): 0, ("jupiter", "venus"): 0, ("jupiter", "saturn"): 0,
    ("venus", "sun"): 0, ("venus", "moon"): 1, ("venus", "mars"): 0,
    ("venus", "mercury"): 2, ("venus", "jupiter"): 0, ("venus", "saturn"): 2,
    ("saturn", "sun"): 0, ("saturn", "moon"): 0, ("saturn", "mars"): 0,
    ("saturn", "mercury"): 2, ("saturn", "jupiter"): 0, ("saturn", "venus"): 2,
}

# Varna: sign (1-indexed) → 0=Shudra, 1=Vaishya, 2=Kshatriya, 3=Brahmin
_VARNA = {
    1: 2, 2: 1, 3: 3, 4: 0, 5: 2, 6: 0, 7: 1, 8: 2, 9: 3, 10: 0, 11: 0, 12: 3,
}

# Vashya: sign → vashya group (0=Manava, 1=Chatushpada, 2=Jalchar, 3=Vanchar, 4=Keeta)
_VASHYA = {
    1: 3, 2: 1, 3: 0, 4: 2, 5: 3, 6: 0, 7: 0, 8: 2, 9: 3, 10: 1, 11: 0, 12: 2,
}


def _nakshatra_index(nakshatra_name: str) -> int | None:
    """Returns 1-indexed nakshatra index from name."""
    _NAKSHATRAS = [
        "ashwini", "bharani", "krittika", "rohini", "mrigashira", "ardra",
        "punarvasu", "pushya", "ashlesha", "magha", "purva phalguni", "uttara phalguni",
        "hasta", "chitra", "swati", "vishakha", "anuradha", "jyeshtha",
        "mula", "purva ashadha", "uttara ashadha", "shravana", "dhanishtha",
        "shatabhisha", "purva bhadrapada", "uttara bhadrapada", "revati",
    ]
    name = nakshatra_name.lower().strip()
    for i, n in enumerate(_NAKSHATRAS):
        if n in name or name in n:
            return i + 1
    return None


def _moon_sign(chart: dict) -> int | None:
    """Returns 1-indexed Moon sign from chart JSONB."""
    planets = chart.get("planets") or {}
    moon = planets.get("moon") or {}
    sign = moon.get("current_sign")
    if sign and isinstance(sign, int):
        return sign
    # Fallback via astro_details
    astro = chart.get("astro_details") or {}
    sign_name = astro.get("moon_sign") or astro.get("moonsign") or ""
    _SIGNS = ["aries", "taurus", "gemini", "cancer", "leo", "virgo",
              "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
    for i, s in enumerate(_SIGNS):
        if s in sign_name.lower():
            return i + 1
    return None


def _moon_nakshatra(chart: dict) -> str | None:
    planets = chart.get("planets") or {}
    moon = planets.get("moon") or {}
    nak = moon.get("nakshatra")
    if nak:
        return nak
    astro = chart.get("astro_details") or {}
    return astro.get("nakshatra")


def _varna_score(sign_a: int, sign_b: int) -> int:
    va, vb = _VARNA.get(sign_a, 0), _VARNA.get(sign_b, 0)
    return 1 if vb <= va else 0


def _vashya_score(sign_a: int, sign_b: int) -> int:
    va, vb = _VASHYA.get(sign_a, 0), _VASHYA.get(sign_b, 0)
    return 2 if va == vb else 1 if abs(va - vb) <= 1 else 0


def _tara_score(nak_a: int, nak_b: int) -> int:
    """Tara: count from nak_a to nak_b mod 9. Groups 1/3/5/7 are friendly."""
    tara = ((nak_b - nak_a) % 27) % 9 + 1
    return 3 if tara in {1, 3, 5, 7} else 0


def _yoni_score(nak_a: int, nak_b: int) -> int:
    ya, yb = _YONI[nak_a - 1], _YONI[nak_b - 1]
    if ya == yb:
        return 4
    if frozenset([ya, yb]) in _YONI_FRIENDLY:
        return 3
    return 1


def _graha_maitri_score(sign_a: int, sign_b: int) -> int:
    la = _SIGN_LORD.get(sign_a, "")
    lb = _SIGN_LORD.get(sign_b, "")
    if not la or not lb:
        return 2
    rel_ab = _PLANET_RELATION.get((la, lb), 1)
    rel_ba = _PLANET_RELATION.get((lb, la), 1)
    combined = rel_ab + rel_ba
    if combined >= 4:
        return 5
    if combined == 3:
        return 4
    if combined == 2:
        return 3
    if combined == 1:
        return 1
    return 0


def _gana_score(nak_a: int, nak_b: int) -> int:
    ga, gb = _GANA[nak_a - 1], _GANA[nak_b - 1]
    if ga == gb:
        return 6
    if (ga == 0 and gb == 1) or (ga == 1 and gb == 0):
        return 5
    if (ga == 0 and gb == 2) or (ga == 2 and gb == 0):
        return 0
    return 0


def _bhakoot_score(sign_a: int, sign_b: int) -> int:
    """Bhakoot: house relationship between signs (from sign_a's perspective)."""
    rel = ((sign_b - sign_a) % 12) + 1
    # 2/12, 5/9, 6/8 are inauspicious
    if rel in {2, 12, 5, 9, 6, 8}:
        return 0
    return 7


def _nadi_score(nak_a: int, nak_b: int) -> int:
    na, nb = _NADI[nak_a - 1], _NADI[nak_b - 1]
    return 0 if na == nb else 8


def compute_ashtakoot(chart_a: dict, chart_b: dict) -> dict:
    """
    Returns Ashtakoot scores between two charts.
    chart_a, chart_b: full chart JSONB from Supabase.
    """
    sign_a = _moon_sign(chart_a) or 1
    sign_b = _moon_sign(chart_b) or 1
    nak_name_a = _moon_nakshatra(chart_a) or ""
    nak_name_b = _moon_nakshatra(chart_b) or ""
    nak_a = _nakshatra_index(nak_name_a) or 1
    nak_b = _nakshatra_index(nak_name_b) or 1

    scores = {
        "varna":        {"score": _varna_score(sign_a, sign_b),    "max": 1},
        "vashya":       {"score": _vashya_score(sign_a, sign_b),   "max": 2},
        "tara":         {"score": _tara_score(nak_a, nak_b),       "max": 3},
        "yoni":         {"score": _yoni_score(nak_a, nak_b),       "max": 4},
        "graha_maitri": {"score": _graha_maitri_score(sign_a, sign_b), "max": 5},
        "gana":         {"score": _gana_score(nak_a, nak_b),       "max": 6},
        "bhakoot":      {"score": _bhakoot_score(sign_a, sign_b),  "max": 7},
        "nadi":         {"score": _nadi_score(nak_a, nak_b),       "max": 8},
    }
    total = sum(v["score"] for v in scores.values())

    # Identify doshas
    doshas = []
    if scores["nadi"]["score"] == 0:
        doshas.append("Nadi Dosha")
    if scores["bhakoot"]["score"] == 0:
        doshas.append("Bhakoot Dosha")
    if scores["gana"]["score"] == 0:
        doshas.append("Gana Dosha")

    return {
        "scores": scores,
        "total": total,
        "max": 36,
        "doshas": doshas,
        "moon_sign_a": sign_a,
        "moon_sign_b": sign_b,
        "moon_nakshatra_a": nak_name_a,
        "moon_nakshatra_b": nak_name_b,
    }
