from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "BotClientes Backend"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Supabase / PostgreSQL
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    DATABASE_URL: str

    # Evolution API (WhatsApp)
    EVOLUTION_API_URL: str
    EVOLUTION_API_KEY: str
    EVOLUTION_INSTANCE_NAME: str

    # Voice API (RTX 3050 local)
    VOICE_API_URL: str = "http://localhost:8001"
    VOICE_API_KEY: Optional[str] = None

    # Google Maps / Places API
    GOOGLE_MAPS_API_KEY: str

    # GitHub
    GITHUB_TOKEN: Optional[str] = None

    # LLM
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Queue
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Concurrency control
    MAX_CONCURRENT_AUDIO_JOBS: int = 1
    AUDIO_QUEUE_TIMEOUT: int = 300

    # Anti-ban settings
    MIN_DELAY_BETWEEN_CALLS: int = 300  # 5 minutes
    MAX_DELAY_BETWEEN_CALLS: int = 600  # 10 minutes
    TYPING_DELAY_MIN: int = 4000
    TYPING_DELAY_MAX: int = 6000
    RECORDING_DELAY_MIN: int = 5000
    RECORDING_DELAY_MAX: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()