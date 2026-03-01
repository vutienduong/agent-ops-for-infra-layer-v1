from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AgentOps Server"
    database_url: str = "sqlite:///./agentops.db"
    api_key_header: str = "X-AgentOps-Key"


settings = Settings()
