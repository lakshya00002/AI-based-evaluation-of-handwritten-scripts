from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./app.db"
    session_cookie_name: str = "session_id"
    session_max_age_seconds: int = 60 * 60 * 24 * 7


settings = Settings()
