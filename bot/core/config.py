from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).parent.parent / ".env"

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    PROXY_URL: str | None = None
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT: int = 5
    RATE_LIMIT_WINDOW: int = 60
    CACHE_TTL: int = 86400
    MAX_SEARCH_RESULTS: int = 10
    ADMIN_IDS: str = ""
    MAX_QUERY_LENGTH: int = 200
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    model_config = SettingsConfigDict(env_file=ENV_PATH, extra="ignore")

    @property
    def admin_ids(self) -> list[int]:
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]

settings = Settings()