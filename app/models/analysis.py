from pydantic import BaseModel

VALID_SECTIONS = [
    "personality",
    "mind",
    "career",
    "skills",
    "wealth",
    "foreign",
    "romance",
    "marriage",
    "business",
    "property",
    "health",
    "education",
    "parents",
    "siblings",
    "children",
    "spirituality",
]


class AnalysisResult(BaseModel):
    id: str
    chart_id: str
    section: str
    content: str
    model: str
    cached: bool = False
    created_at: str | None = None
