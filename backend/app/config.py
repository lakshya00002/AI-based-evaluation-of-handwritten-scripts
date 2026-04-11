"""Application configuration from environment variables."""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from `.env` and environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="mysql+pymysql://assess:change_me@localhost:3306/handwritten_assessment",
        alias="DATABASE_URL",
    )
    secret_key: str = Field(default="dev-secret-change-in-production", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60 * 24 * 7, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    tesseract_cmd: str | None = Field(default=None, alias="TESSERACT_CMD")
    default_ocr_lang: str = Field(default="eng", alias="DEFAULT_OCR_LANG")

    sbert_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="SBERT_MODEL_NAME",
    )
    weight_semantic: float = Field(default=0.65, alias="WEIGHT_SEMANTIC")
    weight_keyword: float = Field(default=0.35, alias="WEIGHT_KEYWORD")

    cors_origins: str = Field(
        default="http://localhost:5173",
        alias="CORS_ORIGINS",
    )
    upload_dir: str = Field(default="data/uploads", alias="UPLOAD_DIR")
    max_upload_mb: int = Field(default=25, alias="MAX_UPLOAD_MB")

    use_easyocr: bool = Field(default=False, alias="USE_EASYOCR")

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
