from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str = "NEXA CITY"
    app_version: str = "1.0.0"
    debug: bool = False

    # Telegram
    telegram_bot_token: str
    telegram_owner_id: int

    # Database
    database_url: str

    # Security
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # CORS
    frontend_url: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
