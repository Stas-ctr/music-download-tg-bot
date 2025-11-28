import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram Bot Token
    BOT_TOKEN: str

    # Настройки поиска
    MAX_SEARCH_RESULTS: int = 5
    REQUEST_TIMEOUT: int = 30

    # Пути
    STORAGE_PATH: str = "./storage"

    class Config:
        env_file = ".env"


# Создание экземпляра настроек
settings = Settings()

# Создание необходимых директорий
os.makedirs(settings.STORAGE_PATH, exist_ok=True)