from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/finengine"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_REDIS_URL: str = "redis://localhost:6379/1"

    # Process startup options used by deploy scripts.
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    APP_WORKERS: int = 1
    APP_FORWARDED_ALLOW_IPS: str = "*"
    CELERY_LOG_LEVEL: str = "INFO"
    CELERY_POOL: str = "solo"
    CELERY_HOSTNAME: str = "finengine@%h"
    CELERY_QUEUES: str = ""
    CELERY_CONCURRENCY: int | None = None

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    ALGORITHM: str = "HS256"

    # Superadmin init
    SUPERADMIN_INIT_PASSWORD: str = "admin123"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    # Upload
    MAX_UPLOAD_SIZE_MB: int = 1024  # 最大上传文件大小 1024MB

    # API encryption
    API_CRYPTO_ENABLED: bool = True
    API_CRYPTO_PRIVATE_KEY: str = ""  # PEM string; empty = generate on process startup
    API_CRYPTO_REPLAY_WINDOW_SECONDS: int = 300

    # Logging
    LOG_DIR: str = str(BACKEND_DIR / "logs")
    LOG_LEVEL: str = "INFO"
    LOG_RETENTION_DAYS: int = 15
    LOG_ROTATION_TIME: str = "00:00"

    # Alibaba Cloud credentials
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""

    # Alibaba Cloud OSS
    ALIYUN_OSS_REGION: str = "cn-hangzhou"
    ALIYUN_OSS_BUCKET: str = ""
    ALIYUN_OSS_ENDPOINT: str = ""  # e.g. https://oss-cn-hangzhou.aliyuncs.com
    INTERNAL_DOWNLOAD: bool = False
    ALIYUN_OSS_INTERNAL_ENDPOINT: str = ""  # e.g. https://oss-cn-hangzhou-internal.aliyuncs.com

    # Alibaba Cloud STS
    ALIYUN_STS_ROLE_ARN: str = ""
    ALIYUN_STS_EXPIRE_SECONDS: int = 3600
    ALIYUN_STS_POLICY: str = ""  # JSON string; empty = use default role policy

    # Export center
    EXPORT_OSS_PREFIX: str = "system-export"
    EXPORT_FILE_EXPIRE_DAYS: int = 7


settings = Settings()
