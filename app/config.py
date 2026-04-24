from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Firebase
    firebase_credentials_path: str = "firebase-credentials.json"
    firebase_project_id: str = ""

    # JWT
    secret_key: str = "change-this-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Tesseract
    tesseract_cmd: str = "tesseract"

    # App
    app_env: str = "development"
    debug: bool = True

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
