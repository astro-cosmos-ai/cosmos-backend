from datetime import date, time
from typing import Any
from pydantic import BaseModel, Field


class BirthInput(BaseModel):
    name: str
    dob: date
    tob: time
    pob_name: str
    pob_lat: float = Field(..., ge=-90, le=90)
    pob_lon: float = Field(..., ge=-180, le=180)
    timezone: float = Field(..., ge=-12, le=14, description="UTC offset, e.g. 5.5 for IST")



class LoadResponse(BaseModel):
    loaded: bool
    varshaphal_year: int
    transit_date: str


class ChartRow(BaseModel):
    id: str
    user_id: str
    name: str
    dob: str
    tob: str
    pob_name: str
    pob_lat: float
    pob_lon: float
    timezone: float
    birth_details: dict[str, Any] | None = None
    astro_details: dict[str, Any] | None = None
    planets: dict[str, Any] | None = None
    divisional_charts: dict[str, Any] | None = None
    kp_planets: list[Any] | dict[str, Any] | None = None
    kp_cusps: list[Any] | dict[str, Any] | None = None
    kp_house_significators: list[Any] | dict[str, Any] | None = None
    kp_planet_significators: list[Any] | dict[str, Any] | None = None
    parashari_significators: dict[str, Any] | None = None
    dashas: dict[str, Any] | None = None
    current_dasha: dict[str, Any] | None = None
    ashtakavarga: dict[str, Any] | None = None
    doshas: dict[str, Any] | None = None
    panchang: dict[str, Any] | None = None
    varshaphal_raw: dict[str, Any] | None = None
    transit_snapshot: dict[str, Any] | None = None
    created_at: str | None = None
