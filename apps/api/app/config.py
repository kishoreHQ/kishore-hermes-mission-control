from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://hermes:hermes@localhost:5432/hermes_os"
    redis_url: str = "redis://localhost:6379/0"
    hermes_data_dir: str = "data"
    hermes_home: str = ""
    session_secret: str = "dev-secret"
    cors_origins: list[str] = ["http://localhost:3000"]
    auto_create_tables: bool = True


settings = Settings()
