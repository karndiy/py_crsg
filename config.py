import os
from pathlib import Path

from sqlalchemy.pool import StaticPool

BASE_DIR = Path(__file__).resolve().parent


def _bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'instance' / 'community_radio.db').as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    APP_HOST = os.environ.get("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.environ.get("APP_PORT", "5000"))

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-this-password")
    RADIO_API_KEY = os.environ.get("RADIO_API_KEY", "change-this-api-key")

    SMS_ENABLED = _bool_env("SMS_ENABLED", True)
    SMS_PORT = os.environ.get("SMS_PORT", "/dev/ttyUSB2")
    SMS_BAUD = int(os.environ.get("SMS_BAUD", "115200"))
    SMS_AUTO_DELETE = _bool_env("SMS_AUTO_DELETE", True)
    SMS_POLL_INTERVAL = int(os.environ.get("SMS_POLL_INTERVAL", "3"))

    CALL_ENABLED = _bool_env("CALL_ENABLED", True)
    CALL_AUTO_REJECT = _bool_env("CALL_AUTO_REJECT", True)

    AUTO_ANNOUNCE = _bool_env("AUTO_ANNOUNCE", True)

    PIPER_EXECUTABLE = os.environ.get("PIPER_EXECUTABLE", "piper")
    PIPER_MODEL = os.environ.get("PIPER_MODEL", "models_voice/th_TH-model.onnx")

    AUDIO_PLAYER = os.environ.get("AUDIO_PLAYER", "aplay")
    AUDIO_DEVICE = os.environ.get("AUDIO_DEVICE", "default")
    AUDIO_OUTPUT_DIR = os.environ.get("AUDIO_OUTPUT_DIR", str(BASE_DIR / "static" / "audio"))

    MAX_MESSAGE_LENGTH = int(os.environ.get("MAX_MESSAGE_LENGTH", "500"))
    RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", "10"))

    MULTIPART_TIMEOUT_SECONDS = int(os.environ.get("MULTIPART_TIMEOUT_SECONDS", "300"))

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # A plain ":memory:" SQLite DB is per-connection; without a shared
    # connection, the app and a test's own queries would each see an
    # empty database. StaticPool keeps every checkout on the same
    # connection for the life of the process.
    SQLALCHEMY_ENGINE_OPTIONS = {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
    SMS_ENABLED = False
    CALL_ENABLED = False
    SECRET_KEY = "test-secret"
    ADMIN_PASSWORD = "test-admin-password"
    RADIO_API_KEY = "test-api-key"


CONFIG_BY_NAME = {
    "production": Config,
    "development": Config,
    "testing": TestConfig,
}


def get_config(name: str | None = None):
    name = name or os.environ.get("APP_ENV", "production")
    return CONFIG_BY_NAME.get(name, Config)
