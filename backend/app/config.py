from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables / .env file.
    Pydantic validates all fields on startup — any missing required var raises a clear error.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    GEMINI_API_KEY: str = ""
    COMPANY_NAME: str = "TechNovance Solutions"
    HR_EMAIL: str = "hr@technovance.com"
    HR_PHONE: str = "+91-40-2345-6789"
    HRMS_PORTAL: str = "https://hrms.technovance.internal"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def is_api_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY) and self.GEMINI_API_KEY != "YOUR_GEMINI_API_KEY"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
