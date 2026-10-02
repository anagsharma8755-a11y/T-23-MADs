from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./muletrace.db"
    secret_key: str = "local-development-secret-change-me-12345"
    session_ttl_hours: int = 8
    cookie_secure: bool = False
    demo_mode: bool = True
    max_upload_bytes: int = 10 * 1024 * 1024
    max_upload_rows: int = 100_000
    max_blockchain_upload_bytes: int = 3 * 1024 * 1024 * 1024
    cors_origins: str = "http://localhost:5173"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "replace-with-a-strong-password"
    neo4j_enabled: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_render_postgres_url(cls, value: str):
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value
settings = Settings()

