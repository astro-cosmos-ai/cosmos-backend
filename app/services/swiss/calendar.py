"""Panchang: tithi, nakshatra yoga, karana, vara (weekday), ayanamsa."""
from datetime import datetime

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]

_YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti",
]

_KARANA_NAMES = [
    "Bava", "Balava", "Kaulava", "Taitila", "Gara",
    "Vanija", "Vishti", "Bava", "Balava", "Kaulava",
]


def compute_panchang(
    sun_lon: float,
    moon_lon: float,
    year: int,
    month: int,
    day: int,
    moon_nakshatra: str,
) -> dict:
    def norm(lon: float) -> float:
        return ((lon % 360) + 360) % 360

    sun_n = norm(sun_lon)
    moon_n = norm(moon_lon)

    diff = norm(moon_n - sun_n)

    tithi_num = int(diff / 12) + 1          # 1..30
    yoga_num = int(norm(sun_n + moon_n) / (360 / 27)) + 1  # 1..27
    karana_num = int(diff / 6) + 1          # 1..60

    tithi_name = _TITHI_NAMES[tithi_num - 1] if tithi_num <= 30 else "Amavasya"
    yoga_name = _YOGA_NAMES[yoga_num - 1] if yoga_num <= 27 else ""
    # Fixed karana cycles (first 7 are fixed, rest repeating 8)
    if karana_num <= 7:
        karana_name = ["Kimstughna", "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija"][karana_num - 1]
    else:
        karana_name = _KARANA_NAMES[(karana_num - 1) % 7]

    weekday = _WEEKDAYS[datetime(year, month, day).weekday()]

    return {
        "tithi": tithi_num,
        "tithi_name": tithi_name,
        "nakshatra": moon_nakshatra,
        "yoga": yoga_num,
        "yoga_name": yoga_name,
        "karana": karana_num,
        "karana_name": karana_name,
        "vaara": weekday,
        "Weekday": weekday,
    }
