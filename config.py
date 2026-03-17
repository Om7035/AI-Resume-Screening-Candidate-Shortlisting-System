"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file (if available)
load_dotenv()


@dataclass
class Settings:
    """Strongly-typed settings for the application."""

    # Paths
    base_dir: Path = Path(__file__).resolve().parent
    resumes_dir: Path = base_dir / "sample_data" / "resumes"
    output_dir: Path = base_dir / "output"
    job_description_file: Path = base_dir / "sample_data" / "job_description.txt"

    # LLM settings
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai").lower()
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    gemini_base_url: str = os.getenv(
        "GEMINI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/models",
    )

    # Email settings (Gmail SMTP)
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    email_username: str = os.getenv("EMAIL_USERNAME", "")
    email_password: str = os.getenv("EMAIL_PASSWORD", "")
    sender_name: str = os.getenv("SENDER_NAME", "HR Team")

    # Business settings
    shortlist_top_n: int = int(os.getenv("SHORTLIST_TOP_N", "3"))
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "45"))


settings = Settings()
