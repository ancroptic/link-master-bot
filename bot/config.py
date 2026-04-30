"""Centralized configuration loaded from environment variables."""
from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_TELEGRAM_ID: int = int(os.getenv("ADMIN_TELEGRAM_ID", "0") or "0")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")
    ADMIN_SHORTENER_TYPE: str = os.getenv("ADMIN_SHORTENER_TYPE", "gplinks")
    BASE_WEB_URL: str = os.getenv("BASE_WEB_URL", "http://localhost:10000")
    RUN_MODE: str = os.getenv("RUN_MODE", "both")


config = Config()
