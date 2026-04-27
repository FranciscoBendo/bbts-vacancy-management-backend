from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://bbts:bbts@db:5432/bbts"
    SECRET_KEY: str = "super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8
    GEMINI_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
