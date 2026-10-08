"""全部配置从环境变量读取，绝不硬编码密码。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env 固定在项目根目录（backend/ 的上一级），与启动时的 CWD 无关
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

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

    # 剧本 PDF 上传：固定在项目根 script-library/uploads，与启动时的 CWD 无关
    # （网页上传的剧本进剧本库，随仓库提交）
    upload_dir: str = str(_PROJECT_ROOT / "script-library" / "uploads")
    max_upload_mb: int = 50
    # 文字提取少于该字数则判定为扫描版，走 OCR
    ocr_text_threshold: int = 200

    # 异步语音条
    voice_dir: str = "uploads/voice"
    max_voice_mb: int = 2
    voice_allowed_ext: str = "mp3,m4a,wav,amr,webm"  # webm：手机浏览器 MediaRecorder 默认格式

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
