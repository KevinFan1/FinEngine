from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/finengine"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    ALGORITHM: str = "HS256"

    # Superadmin init
    SUPERADMIN_INIT_PASSWORD: str = "admin123"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://localhost:8080"]

    # Upload
    MAX_UPLOAD_SIZE_MB: int = 1024  # 最大上传文件大小 1024MB

    # Alibaba Cloud credentials
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""

    # Alibaba Cloud OSS
    ALIYUN_OSS_REGION: str = "cn-hangzhou"
    ALIYUN_OSS_BUCKET: str = ""
    ALIYUN_OSS_ENDPOINT: str = ""  # e.g. https://oss-cn-hangzhou.aliyuncs.com

    # Alibaba Cloud STS
    ALIYUN_STS_ROLE_ARN: str = ""
    ALIYUN_STS_EXPIRE_SECONDS: int = 3600
    ALIYUN_STS_POLICY: str = ""  # JSON string; empty = use default role policy


settings = Settings()
