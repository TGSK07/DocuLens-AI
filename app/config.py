"""Environment-driven settings."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Gemini
    gemini_api_key: str = Field(...)
    gemini_model: str = Field(default="gemini-2.5-flash")
    gemini_max_tokens: int = Field(default=4096)

    # Server
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    log_level: str = Field(default="INFO")

    # Paths
    data_dir: Path = Field(default=Path("./data"))
    database_path: Path = Field(default=Path("./data/extractions.db"))

    # Document handling
    pdf_render_dpi: int = Field(default=144)
    max_image_long_edge_px: int = Field(default=2048)
    max_pages_per_request: int = Field(default=20)
    max_upload_mb: int = Field(default=20)

    @property
    def extractions_dir(self) -> Path:
        return self.data_dir / "extractions"


settings = Settings()  # type: ignore[call-arg]

settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.extractions_dir.mkdir(parents=True, exist_ok=True)
