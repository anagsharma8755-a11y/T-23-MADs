import os
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
    speech_provider: str = "disabled"
    speech_api_key: str = ""
    speech_transcription_model: str = "gpt-4o-mini-transcribe"
    speech_api_base: str = "https://api.openai.com/v1"
    elevenlabs_api_key: str = ""
    elevenlabs_api_base: str = "https://api.elevenlabs.io/v1"
    elevenlabs_voice_id: str = "XrExE9yKIg1WjnnlVkGX"
    elevenlabs_tts_model: str = "eleven_v4_turbo"
    elevenlabs_stt_model: str = "scribe_v2"
    assistant_max_audio_bytes: int = 8 * 1024 * 1024
    assistant_max_recording_seconds: int = 60
    assistant_requests_per_minute: int = 30
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

if os.getenv("VERCEL"):
    if settings.database_url.startswith("sqlite"):
        raise RuntimeError("DATABASE_URL must use the production Supabase database")
    if settings.secret_key == "local-development-secret-change-me-12345" or len(settings.secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be a production secret of at least 32 characters")

