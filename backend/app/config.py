from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables / .env file.
    Pydantic validates all fields on startup — any missing required var raises a clear error.
    
    Production features:
    - Multi-environment support (dev, staging, prod)
    - Configuration validation on startup
    - Rate limiting thresholds
    - Performance tuning knobs
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Deployment
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    # AI Provider
    AI_PROVIDER: Literal["google_genai", "groq"] = "google_genai"
    GEMINI_API_KEY: str = ""
    AI_MODEL_NAME: str = "gemini-2.0-flash"

    GROQ_API_KEY: str = ""
    GROQ_MODEL_NAME: str = "llama-3.1-8b-instant"
    GROQ_API_URL: str = "https://api.groq.com/openai/v1"

    # Company Info
    COMPANY_NAME: str = "TechNovance Solutions"
    HR_EMAIL: str = "hr@technovance.com"
    HR_PHONE: str = "+91-40-2345-6789"
    HRMS_PORTAL: str = "https://hrms.technovance.internal"
    
    # Security & CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    # Performance
    REQUEST_TIMEOUT_SECONDS: int = 30
    GROQ_MAX_RETRIES: int = 3
    GROQ_RETRY_BACKOFF_MS: int = 100
    CACHE_TTL_SECONDS: int = 3600
    
    # Rate Limiting (production safety)
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_REQUESTS_PER_HOUR: int = 1000
    
    # Logging
    LOG_LEVEL: str = "INFO"

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Normalize environment name."""
        return v.lower()

    @property
    def active_provider(self) -> str:
        return self.AI_PROVIDER.lower()

    @property
    def is_api_configured(self) -> bool:
        if self.active_provider == "groq":
            return bool(self.GROQ_API_KEY) and self.GROQ_API_KEY != "YOUR_GROQ_API_KEY"
        return bool(self.GEMINI_API_KEY) and self.GEMINI_API_KEY != "YOUR_GEMINI_API_KEY"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()
