from pydantic import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GEMINI_API_KEY: str
    GOOGLE_APPLICATION_CREDENTIALS: str

    class Config:
        env_file = ".env"

settings = Settings()
