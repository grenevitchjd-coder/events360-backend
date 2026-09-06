# events360-backend/app/config.py
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

    # Email — generic SMTP relay, provider swappable via config vars alone
    # (the same pattern EventNXT uses; replaces the old hardcoded SendGrid
    # relay). Current provider: Resend. Heroku config vars to set:
    #   SMTP_HOST=smtp.resend.com
    #   SMTP_PORT=587                (465 also supported — uses SSL instead)
    #   SMTP_USERNAME=resend        (literally the word "resend")
    #   SMTP_PASSWORD=<a Resend API key>
    #   EMAIL_FROM=no-reply@events360.app
    # EMAIL_FROM may include a display name: "Events360 <no-reply@events360.app>"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = "resend"
    smtp_password: str = ""
    email_from: str = "no-reply@events360.app"

    app_url: str = "http://localhost:8000"  # backend URL, used in reminder email links
    # The deployed frontend's URL — used to build links that land on frontend
    # pages (the password reset page). Set FRONTEND_URL on Heroku.
    frontend_url: str = "http://localhost:5173"

    # CORS: comma-separated list of allowed frontend origins.
    # Defaults to common local dev ports; add your real frontend's Heroku
    # URL here once deployed (e.g. "https://events360-frontend.herokuapp.com").
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    class Config:
        env_file = ".env"
        # Heroku's DATABASE_URL for Postgres sometimes comes as "postgres://",
        # SQLAlchemy 2.x requires "postgresql://" — normalized in database.py.


settings = Settings()