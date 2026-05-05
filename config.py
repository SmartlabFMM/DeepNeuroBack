import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from a .env file located at the project root (two levels up)
ENV_PATH = Path(__file__).resolve().parent.parent / '.env'
if ENV_PATH.exists():
    load_dotenv(dotenv_path=str(ENV_PATH))
else:
    # load default .env if present in CWD, otherwise continue — missing .env will be caught by require_env
    load_dotenv()


def _require_env(key: str) -> str:
    """Return required environment variable or raise a clear error.

    This enforces providing required configuration via environment or .env file.
    """
    val = os.environ.get(key)
    if val is None or str(val).strip() == "":
        raise RuntimeError(
            f"Required environment variable '{key}' is missing. "
            "Add it to your .env or export it in the environment before starting the app."
        )
    return val


def _require_env_int(key: str) -> int:
    s = _require_env(key)
    try:
        return int(s)
    except Exception:
        raise RuntimeError(f"Environment variable '{key}' must be an integer. Got: {s}")


class Config:
    """Base configuration — requires critical environment variables to be present.

    This class intentionally avoids providing fallback values for critical settings
    so that missing configuration is detected early.
    """
    SECRET_KEY = _require_env('SECRET_KEY')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    # Comma-separated list required (explicit to avoid accidental open CORS in production)
    CORS_ORIGINS = _require_env('CORS_ORIGINS').split(',')

    # Paths and storage
    DATABASE_PATH = _require_env('DATABASE_PATH')
    UPLOAD_FOLDER = _require_env('UPLOAD_FOLDER')
    GLIOMA_SEGMENTATION_MODEL_PATH = _require_env('GLIOMA_SEGMENTATION_MODEL_PATH')
    GLIOMA_SEGMENTATION_OUTPUT_DIR = _require_env('GLIOMA_SEGMENTATION_OUTPUT_DIR')

    # Limits and allowed types (MAX_CONTENT_LENGTH may be optional; fall back to 30MB if not present)
    try:
        MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 30 * 1024 * 1024))
    except Exception:
        MAX_CONTENT_LENGTH = 30 * 1024 * 1024

    ALLOWED_FILE_EXTENSIONS = [
        'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tif', 'tiff',
        'txt', 'rtf', 'csv', 'doc', 'docx', 'xls', 'xlsx', 'nii', 'gz'
    ]
    
    # Email Configuration (required if email notifications are enabled)
    EMAIL_SENDER = _require_env('EMAIL_SENDER')
    EMAIL_APP_PASSWORD = _require_env('EMAIL_APP_PASSWORD')
    SMTP_SERVER = _require_env('SMTP_SERVER')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
