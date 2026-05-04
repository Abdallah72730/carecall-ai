"""Operator notifications via Telegram."""
from __future__ import annotations

import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)


def send_telegram(text: str) -> bool:
    """Send a plain message to the configured Telegram chat. No-op if unset."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = httpx.post(
            url,
            json={
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10.0,
        )
        if r.status_code != 200:
            logger.warning("telegram %s: %s", r.status_code, r.text[:300])
            return False
        return True
    except Exception as exc:
        logger.warning("telegram send failed: %s", exc)
        return False
