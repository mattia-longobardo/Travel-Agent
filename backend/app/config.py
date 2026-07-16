from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    travel_host: str = "travel.longobardo.me"
    session_secret: str = "dev-secret"
    postgres_user: str = "travel"
    postgres_db: str = "travel"
    db_travel_password: str = "travel"
    postgres_host: str = "travel-postgres"
    redis_host: str = "travel-redis"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"
    lastminute_mcp_url: str = "https://mcp.lastminute.com/mcp"
    admin_username: str = "admin"
    admin_password: str = "admin"
    admin_email: str = "admin@example.com"

    @property
    def database_url(self) -> str:
        return (f"postgresql+asyncpg://{self.postgres_user}:{self.db_travel_password}"
                f"@{self.postgres_host}:5432/{self.postgres_db}")

@lru_cache
def get_settings() -> Settings:
    return Settings()
