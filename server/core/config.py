"""Configuration settings for the application."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings."""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Airflow
    AIRFLOW_BASE_URL: str = os.getenv("AIRFLOW_BASE_URL")
    AIRFLOW_USERNAME: str = os.getenv("AIRFLOW_USERNAME")
    AIRFLOW_PASSWORD: str = os.getenv("AIRFLOW_PASSWORD")


settings = Settings()
