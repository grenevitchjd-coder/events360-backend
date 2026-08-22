from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Central app configuration, loaded from environment variables.
    On Heroku, DATABASE_URL is injected automatically by the Postgres add-on.
    """

    database_url: str = "postgresql://localhost/events360_dev"
    jwt_secret: str = "change-me-in-production"  # override via JWT_SECRET env var
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # Password policy (documented in architecture doc)
    password_min_length: int = 8

    class Config:
        env_file = ".env"
        # Heroku's DATABASE_URL for Postgres sometimes comes as "postgres://",
        # SQLAlchemy 2.x requires "postgresql://" — normalized in database.py.


settings = Settings()