from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Composed from parts; override any with DATABASE_HOST, DATABASE_PORT, …"""

    model_config = SettingsConfigDict(env_prefix="DATABASE_", env_file=".env", extra="ignore")

    driver: str = "postgresql+psycopg"
    user: str = "postgres"
    password: str = "postgres"
    host: str = "localhost"
    port: int = 5432
    name: str = "facefinder"

    @property
    def url(self) -> str:
        return f"{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class AuthSettings(BaseSettings):
    """Override with AUTH_JWT_SECRET, AUTH_JWT_EXPIRY_MINUTES."""

    model_config = SettingsConfigDict(env_prefix="AUTH_", env_file=".env", extra="ignore")

    jwt_secret: str = "change-me-in-production"
    jwt_expiry_minutes: int = 60


class ScoreSettings(BaseSettings):
    """Override with SCORES_DET_THRESHOLD, SCORES_MATCH_STRONG, …"""

    model_config = SettingsConfigDict(env_prefix="SCORES_", env_file=".env", extra="ignore")

    det_threshold: float = 0.5
    match_strong: float = 0.65
    match_possible: float = 0.45
    band_suggested: float = 0.5
    band_probable: float = 0.7
    band_confirmed: float = 0.9


class StorageSettings(BaseSettings):
    """Separate location per kind — a local path or any fsspec URL. Override with
    IMAGES / FACES (e.g. FACES=s3://bucket/crops).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    images: str = "storage/images"
    faces: str = "storage/faces"


class SeedSettings(BaseSettings):
    """Optional default admin created on a fresh install (empty user table).
    Leave the password empty to disable seeding — there is no built-in default
    password. Put real values in .env (gitignored). Override with
    SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD / SEED_ADMIN_NAME.
    """

    model_config = SettingsConfigDict(env_prefix="SEED_ADMIN_", env_file=".env", extra="ignore")

    email: str = "admin@facefinder.local"
    password: str = ""  # empty → no seeding
    name: str = "Admin"


class Settings(BaseSettings):
    """All runtime config, grouped by domain. Each group reads its own prefixed
    env vars, e.g. settings.database.host <- DATABASE_HOST, settings.auth.jwt_secret
    <- AUTH_JWT_SECRET.
    """

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    scores: ScoreSettings = Field(default_factory=ScoreSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    seed: SeedSettings = Field(default_factory=SeedSettings)


settings = Settings()
