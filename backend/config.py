"""Environment configuration. All env vars flow through here."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class _Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    VAPI_API_KEY: str = os.getenv("VAPI_API_KEY", "")

    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "")

    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PILOT_PRICE_ID: str = os.getenv("STRIPE_PILOT_PRICE_ID", "")
    STRIPE_STARTER_PRICE_ID: str = os.getenv("STRIPE_STARTER_PRICE_ID", "")

    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "")

    SENTRY_DSN_BACKEND: str = os.getenv("SENTRY_DSN_BACKEND", "")

    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    TEST_CLINIC_ID: str = os.getenv("TEST_CLINIC_ID", "")
    SENTENCE_TRANSFORMERS_HOME: str = os.getenv("SENTENCE_TRANSFORMERS_HOME", "")


settings = _Settings()


def require(name: str) -> str:
    value = getattr(settings, name, "")
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value
