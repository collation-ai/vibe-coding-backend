from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Master Database
    master_db_url: str

    # Azure Database
    azure_db_host: str
    azure_db_port: int = 5432
    azure_db_user: Optional[str] = None
    azure_db_password: Optional[str] = None
    azure_db_ssl: str = "require"

    # Security
    encryption_key: str
    api_key_salt: str

    # Configuration
    max_query_time_seconds: int = 30
    max_rows_per_query: int = 10000
    default_page_size: int = 100
    max_request_size_mb: int = 10
    max_pool_size: int = 5
    min_pool_size: int = 1

    # Monitoring
    log_level: str = "INFO"
    enable_audit_logs: bool = True
    sentry_dsn: Optional[str] = None

    # Development
    dev_mode: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton instance
settings = Settings()
