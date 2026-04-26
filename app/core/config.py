from typing import Literal
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_key: str
    supabase_anon_key: str
    astrology_api_key: str = ""
    anthropic_api_key: str
    cors_origins: str = "http://localhost:3000"
    debug: bool = False
    chart_engine: Literal["astrology_api", "swiss"] = "astrology_api"
    ayanamsa: Literal["lahiri", "raman", "krishnamurti", "yukteshwar"] = "lahiri"
    node_mode: Literal["mean", "true"] = "mean"

    @model_validator(mode="after")
    def _require_api_key_for_astrology_api(self) -> "Settings":
        if self.chart_engine == "astrology_api" and not self.astrology_api_key:
            raise ValueError("ASTROLOGY_API_KEY must be set when CHART_ENGINE=astrology_api")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
