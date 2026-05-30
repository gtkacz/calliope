from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CALLIOPE_", env_file=".env", extra="ignore")

    api_title: str = "Calliope"
    database_url: str = "postgresql+psycopg://calliope:calliope@localhost:5432/calliope"
    # Host directory mounted into the container; the folder picker opens here by
    # default. Only paths under a mounted root are visible to the containerized
    # backend. None falls back to the user's home directory.
    browse_root: str | None = None
    embedding_dimensions: int = Field(default=384, ge=1)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
    )
