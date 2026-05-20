from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CALLIOPE_", env_file=".env", extra="ignore")

    api_title: str = "Calliope"
    database_url: str = "postgresql+psycopg://calliope:calliope@localhost:5432/calliope"
    embedding_dimensions: int = Field(default=384, ge=1)
