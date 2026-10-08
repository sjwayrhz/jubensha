"""全部配置从环境变量读取，绝不硬编码密码。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    app_name: str = "jubensha"

    tidb_host: str = ""
    tidb_port: int = 4000
    tidb_user: str = ""
    tidb_password: str = ""
    tidb_db: str = "jubensha"
    tidb_ssl_ca: str = ""  # TiDB Cloud 需要 TLS 时填 CA 证书路径

    jwt_secret: str = "change-me"  # 生产必须经环境变量覆盖
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # 剧本 PDF 上传
    upload_dir: str = "uploads"
    max_upload_mb: int = 50
    # 文字提取少于该字数则判定为扫描版，走 OCR
    ocr_text_threshold: int = 200

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.tidb_user}:{self.tidb_password}"
            f"@{self.tidb_host}:{self.tidb_port}/{self.tidb_db}?charset=utf8mb4"
        )

    @property
    def db_configured(self) -> bool:
        return bool(self.tidb_host and self.tidb_user and self.tidb_password)


settings = Settings()
