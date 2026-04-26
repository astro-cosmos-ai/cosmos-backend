from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_key: str
    supabase_anon_key: str
    anthropic_api_key: str
    cors_origins: str = "http://localhost:3000"
    debug: bool = False
    ayanamsa: Literal["lahiri", "raman", "krishnamurti", "yukteshwar"] = "lahiri"
    node_mode: Literal["mean", "true"] = "mean"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
