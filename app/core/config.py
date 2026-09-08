from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Bot credentials
    BOT_TOKEN: str = Field(default="8926904186:AAGc1v4Z4vzUMkR9O0vpUQzWlPAWcWyuEE4")
    BOT_USERNAME: str = Field(default="digiproductsllr_bot")

    # Mandatory Membership
    MANDATORY_CHANNEL_ID: int = Field(default=-1004438071089)
    MANDATORY_CHANNEL_LINK: str = Field(default="https://t.me/sellify_announcement")
    MANDATORY_GROUP_ID: int = Field(default=-1001987654321)
    MANDATORY_GROUP_LINK: str = Field(default="https://t.me/+SpKs2_u6NcxiN2M1")
    LIVE_SALES_CHANNEL_ID: int | None = Field(default=-1004438071089)

    # Database
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./sellify.db")
    DB_ECHO: bool = Field(default=False)

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Store Settings
    APP_NAME: str = Field(default="Sellify")
    CURRENCY_SYMBOL: str = Field(default="$")
    DEFAULT_REFERRAL_COMMISSION_PERCENT: float = Field(default=10.0)
    SUPPORT_CHAT_ID: int | None = Field(default=None)
    ADMIN_TELEGRAM_IDS: list[int] = Field(default_factory=lambda: [6186806738])

    # Security
    SECRET_KEY: str = Field(default="development_super_secret_key_1234567890")
    JWT_SECRET: str = Field(default="development_jwt_secret_key_1234567890")
    WEBHOOK_SECRET: str = Field(default="dev_webhook_secret")
    WEBHOOK_URL: str = Field(default="")


settings = Settings()
