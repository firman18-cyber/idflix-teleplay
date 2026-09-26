from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    telegram_api_id: int
    telegram_api_hash: str
    telegram_bot_token: str
    telegram_helper_bot_tokens_str: str = Field("", alias="TELEGRAM_HELPER_BOT_TOKENS")
    telegram_chat_id: int

    stream_token: str = ""
    telegram_client_concurrency: int = 3
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    cors_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def telegram_helper_bot_tokens(self) -> list[str]:
        return [x.strip() for x in self.telegram_helper_bot_tokens_str.split(",") if x.strip()]

    @property
    def all_bot_tokens(self) -> list[str]:
        return [self.telegram_bot_token] + self.telegram_helper_bot_tokens

    @property
    def allowed_origins(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache()
def get_settings() -> Settings:
    return Settings()
