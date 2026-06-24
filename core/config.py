from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    mongo_uri: str = Field(default="")
    mongo_db_name: str = "Ncert_Rag"
    minio_endpoint: str = Field(default="")
    minio_access_key: str = Field(default="")
    minio_secret_key: str = Field(default="")
    minio_bucket: str = "ncert-rag"
    minio_secure: bool = False

    media_storage_path: str = "./media_assets"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached Settings singleton.
    Use this everywhere instead of instantiating Settings() directly.
    """
    return Settings()
