import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _int_env("PORT", 8000)
    max_file_size_mb: int = _int_env("MAX_FILE_SIZE_MB", 100)
    max_files_per_upload: int = _int_env("MAX_FILES_PER_UPLOAD", 10)
    retention_hours: int = _int_env("RETENTION_HOURS", 24)

    fabrix_endpoint_url: str = os.getenv("FABRIX_ENDPOINT_URL", "").strip()
    fabrix_client_key: str = os.getenv("FABRIX_CLIENT_KEY", "").strip()
    fabrix_openapi_token: str = os.getenv("FABRIX_OPENAPI_TOKEN", "").strip()
    fabrix_model_id: str = os.getenv("FABRIX_MODEL_ID", "").strip()
    fabrix_model_name: str = os.getenv("FABRIX_MODEL_NAME", "gpt-4o").strip()
    fabrix_user_email: str = os.getenv("FABRIX_USER_EMAIL", "").strip()

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def llm_enabled(self) -> bool:
        return all(
            [
                self.fabrix_endpoint_url,
                self.fabrix_client_key,
                self.fabrix_openapi_token,
                self.fabrix_model_id,
                self.fabrix_model_name,
            ]
        )


settings = Settings()
