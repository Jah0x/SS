from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # читаем переменные окружения как есть (без префикса), регистр не важен
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    DB_DSN: str = Field(...)

    WATCH_NAMESPACE: str = Field("securelink")
    WATCH_LABEL_SELECTOR: str = Field("app=xray,component=clients")
    POOL_LABEL_KEY: str = Field("pool")
    CM_CLIENTS_KEY: str = Field("clients.json")

    INTERNAL_TOKEN: str = Field(..., alias="SUBS_INTERNAL_TOKEN")
    RESCAN_INTERVAL_SEC: int = Field(600)

settings = Settings()
