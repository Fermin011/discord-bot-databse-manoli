from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gmail IMAP
    gmail_email: str = ""
    gmail_app_password: str = ""
    gmail_search_subject: str = "manoli_backup"
    gmail_check_interval_minutes: int = 60

    # Base de datos
    database_path: str = "./data/database.db"
    json_path: str = "./data/data.json"

    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Discord Bot
    discord_token: str = ""
    discord_prefix: str = "!"
    discord_allowed_channels: str = ""
    discord_admin_user_ids: str = ""

    # Seguridad
    sql_max_rows: int = 100

    @property
    def db_path(self) -> Path:
        return Path(self.database_path).resolve()

    @property
    def json_file_path(self) -> Path:
        return Path(self.json_path).resolve()

    @property
    def allowed_channels(self) -> List[int]:
        if not self.discord_allowed_channels:
            return []
        return [int(ch.strip()) for ch in self.discord_allowed_channels.split(",") if ch.strip()]

    @property
    def admin_user_ids(self) -> List[int]:
        if not self.discord_admin_user_ids:
            return []
        return [int(uid.strip()) for uid in self.discord_admin_user_ids.split(",") if uid.strip()]

    @property
    def api_base_url(self) -> str:
        return f"http://127.0.0.1:{self.api_port}"


settings = Settings()
