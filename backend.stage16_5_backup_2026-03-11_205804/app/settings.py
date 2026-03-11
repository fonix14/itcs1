from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    app_env: str = 'dev'
    app_name: str = 'itcs'
    database_url: str

    # Web Push (VAPID)
    vapid_public_key: str = Field(default="")
    vapid_private_key: str = Field(default="")
    vapid_subject: str = Field(default="mailto:admin@example.com")

    # Email fallback (SMTP)
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_pass: str = Field(default="")
    smtp_from: str = Field(default="itcs@example.com")
    smtp_tls: bool = Field(default=True)

    # Matrix (primary channel)
    matrix_base_url: str = Field(default="")
    matrix_access_token: str = Field(default="")
    matrix_room_id: str = Field(default="")

    # Portal links in notifications
    portal_base_url: str = Field(default="")

    # Outbox poller (legacy)
    outbox_poll_interval_sec: int = Field(default=10)
    outbox_batch_size: int = Field(default=25)

    # Notifier policy
    notifier_daily_health_hour_utc: int = Field(default=7)  # 07:00 UTC (~10:00 MSK)
    notifier_worker_alive_sec: int = Field(default=120)
    notifier_max_attempts: int = Field(default=10)
    notifier_lock_batch_size: int = Field(default=20)


settings = Settings()
