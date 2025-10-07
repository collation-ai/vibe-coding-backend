from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


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

    # Azure Communication Services
    azure_comm_service_conn_string: Optional[str] = None
    azure_comm_sender_email: Optional[str] = None
    azure_comm_sender_name: str = "Vibe Coding"

    # Password Policy
    password_expiry_days: int = 90
    password_reset_token_expiry_hours: int = 24

    # Development
    dev_mode: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


# Singleton instance
settings = Settings()
