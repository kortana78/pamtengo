from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Pamtengo API"
    database_url: str = "sqlite:///./pamtengo.db"
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    rate_limit_per_minute: int = 120
    ai_provider: str = "mock"
    ai_timeout_seconds: int = 20
    ai_max_retries: int = 2
    ai_max_tokens: int = 2000
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    seed_admin_email: str = "admin@pamtengo.demo"
    seed_admin_role: str = "admin"
    csv_max_bytes: int = 1_048_576
    csv_max_rows: int = 1000


settings = Settings()
