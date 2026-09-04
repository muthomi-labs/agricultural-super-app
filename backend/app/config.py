# app/config.py

import os
import tempfile


def _normalize_database_url(url):
    """
    Some managed Postgres providers (Render included) still hand out
    connection strings using the legacy `postgres://` scheme, but
    SQLAlchemy 2.x's dialect loader only recognizes `postgresql://` and
    raises NoSuchModuleError on the old one. Rewriting just the scheme
    here means the exact DATABASE_URL a provider gives us works as-is,
    with no manual edits needed at deploy time. Anything already using
    `postgresql://` (or any other scheme, e.g. local sqlite) passes
    through unchanged.
    """
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


class Config:
    """
    Shared base configuration. Every value is overridable via environment
    variable so the same codebase runs unmodified across dev/test/prod --
    only the environment differs. Never instantiate this directly; use
    get_config() to select a concrete subclass.
    """

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_DATABASE_URI = _normalize_database_url(
        os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/agri_super_app",
        )
    )

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES_SECONDS = int(
        os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_SECONDS", 60 * 60 * 24)  # 24h
    )

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]

    JSON_SORT_KEYS = False

    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

    PASSWORD_RESET_TOKEN_EXPIRES_SECONDS = int(
        os.environ.get("PASSWORD_RESET_TOKEN_EXPIRES_SECONDS", 60 * 60)  # 1h
    )
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "ollama")
    AI_MODEL = os.environ.get("AI_MODEL")

    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER")

    # Cloudinary (see app/services/upload_service.py): when both are set,
    # uploads go to Cloudinary's free tier instead of local disk, which is
    # ephemeral on a platform like Render's free plan (wiped on every
    # redeploy). Both values are non-secret -- an unsigned upload preset
    # (Cloudinary dashboard -> Settings -> Upload -> Add upload preset,
    # Signing Mode: Unsigned) needs no API key/secret server-side, and the
    # cloud name is already public in every resulting URL. Falls back to
    # local disk when unset, e.g. local dev.
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_UPLOAD_PRESET = os.environ.get("CLOUDINARY_UPLOAD_PRESET")
    # 50MB ceiling so video uploads (up to MAX_VIDEO_SIZE_BYTES in
    # upload_service.py) aren't rejected by Flask before reaching that
    # validation; the image upload path still enforces its own stricter
    # 5MB limit regardless of this global ceiling.
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))  # 50MB
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").strip().lower() in ("true", "1", "yes")
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").strip().lower() in ("true", "1", "yes")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    # Falls back to MAIL_USERNAME (the common case: sending account IS
    # the "from" address) so this doesn't have to be set twice.
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or os.environ.get("MAIL_USERNAME")

    # Comma-separated admin email addresses notified when a new user
    # registers (see auth_service.register_user). Empty by default --
    # nobody is notified until this is explicitly set.
    ADMIN_NOTIFICATION_EMAILS = [
        email.strip()
        for email in os.environ.get("ADMIN_NOTIFICATION_EMAILS", "").split(",")
        if email.strip()
    ]


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    """
    Used by the test suite. Defaults to an in-memory SQLite database so
    tests run fast and never touch a real database unless
    TEST_DATABASE_URL is explicitly set (e.g. to run the suite against
    real Postgres in CI).
    """

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL", "sqlite:///:memory:"
    )
    JWT_ACCESS_TOKEN_EXPIRES_SECONDS = 3600
    UPLOAD_FOLDER = tempfile.mkdtemp(prefix="agri_super_app_test_uploads_")
    MAIL_SERVER = "smtp.test.example.com"
    MAIL_USERNAME = "test@example.com"
    MAIL_PASSWORD = "test-password"
    MAIL_DEFAULT_SENDER = "test@example.com"
    MAIL_SUPPRESS_SEND = True
    PROPAGATE_EXCEPTIONS = False


class ProductionConfig(Config):
    DEBUG = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(config_name=None):
    """
    Resolve a config class by name, falling back to the FLASK_ENV
    environment variable, then to DevelopmentConfig. Returns the class
    itself (not an instance) -- Flask's app.config.from_object() reads
    class attributes directly.
    """
    config_name = config_name or os.environ.get("FLASK_ENV", "default")
    return CONFIG_MAP.get(config_name, DevelopmentConfig)
