from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.app_name = "isy-shell-api"
        self.api_prefix = "/api/v1"
        self.environment = os.getenv("ENVIRONMENT", "development").strip().lower()
        self.api_token = os.getenv("ISY_API_TOKEN", "change-me-token")
        self.script_base_path = Path(
            os.getenv(
                "SCRIPT_BASE_PATH",
                "./scripts" if self.environment == "development" else "/opt/isyone/scripts",
            )
        )
        if self.environment == "development":
            self.database_url = "sqlite:///./isy_shell_dev.db"
        else:
            self.database_url = os.getenv(
                "DATABASE_URL",
                "postgresql://isy:isy@postgres:5432/isy_shell",
            )
        self.script_timeout_seconds = int(os.getenv("SCRIPT_TIMEOUT_SECONDS", "120"))
        self.max_logs_limit = int(os.getenv("MAX_LOGS_LIMIT", "500"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
