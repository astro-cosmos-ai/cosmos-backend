from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    question: str = Field(..., description="Natural-language question about a life event (e.g. 'When will I get married?')")
    start_date: date = Field(default_factory=date.today, description="Start of prediction window")
    end_date: Optional[date] = Field(None, description="End of prediction window (default: 15 years from start)")


class PredictWindow(BaseModel):
    md_lord: str
    ad_lord: str
    start: str
    end: str
    houses_activated: list[int]
    match_score: float
    transit_confirmed: bool
    ashtakavarga_score: Optional[float]


class PredictResponse(BaseModel):
    chart_id: str
    question: str
    target_houses: list[int]
    windows: list[PredictWindow]
    analysis: str
    sadesati_active: bool
    sadesati_phase: Optional[str]


class TransitSnapshotResponse(BaseModel):
    date: str
    natal_asc_sign: int
    planets: dict


class DoubleTansitResponse(BaseModel):
    date: str
    houses: dict[str, dict]


class SadeSatiResponse(BaseModel):
    active: bool
    phase: Optional[str]
    natal_moon_sign: Optional[int]
    saturn_transit_sign: Optional[int]
    saturn_transit_house_from_moon: Optional[int]
    severity_factors: list[str]
    note: Optional[str]
    error: Optional[str] = None
