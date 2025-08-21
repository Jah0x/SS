from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    DB_DSN: str = Field(..., env="DB_DSN")

    WATCH_NAMESPACE: str = Field("securelink", env="WATCH_NAMESPACE")
    WATCH_LABEL_SELECTOR: str = Field("app=xray,component=clients", env="WATCH_LABEL_SELECTOR")
    POOL_LABEL_KEY: str = Field("pool", env="POOL_LABEL_KEY")
    CM_CLIENTS_KEY: str = Field("clients.json", env="CM_CLIENTS_KEY")

    INTERNAL_TOKEN: str = Field(..., env="SUBS_INTERNAL_TOKEN")
    RESCAN_INTERVAL_SEC: int = Field(600, env="RESCAN_INTERVAL_SEC")

    class Config:
        case_sensitive = False

settings = Settings()
