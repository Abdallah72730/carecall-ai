"""Email notifications via Resend."""
from __future__ import annotations

import logging

import resend

from config import settings

logger = logging.getLogger(__name__)


def _ensure_configured() -> bool:
    if not settings.RESEND_API_KEY:
        logger.info("Resend not configured (RESEND_API_KEY empty), skipping email")
        return False
    resend.api_key = settings.RESEND_API_KEY
    return True


def send_message_alert(
    clinic_email: str,
    clinic_name: str,
    caller_name: str | None,
    caller_phone: str | None,
    message_reason: str | None,
) -> bool:
    """Notify the clinic that an after-hours message was captured."""
    if not _ensure_configured() or not clinic_email:
        return False

    name = caller_name or "An unidentified caller"
    phone = caller_phone or "(no number captured)"
    reason = message_reason or "(no reason given)"

    html = (
        f"<h2>New after-hours message &mdash; {clinic_name}</h2>"
        f"<p><strong>Caller:</strong> {name}</p>"
        f"<p><strong>Phone:</strong> {phone}</p>"
        f"<p><strong>Reason:</strong> {reason}</p>"
        f"<p style='color:#666;font-size:13px'>"
        f"Captured by your CareCall AI receptionist while the clinic was closed."
        f"</p>"
    )
    text = (
        f"New after-hours message — {clinic_name}\n\n"
        f"Caller: {name}\nPhone: {phone}\nReason: {reason}\n\n"
        f"Captured by CareCall AI."
    )
    try:
        resend.Emails.send(
            {
                "from": settings.RESEND_FROM_EMAIL or "CareCall AI <noreply@carecallai.net>",
                "to": [clinic_email],
                "subject": f"New after-hours message for {clinic_name}",
                "html": html,
                "text": text,
            }
        )
        return True
    except Exception as exc:
        logger.warning("Resend send failed: %s", exc)
        return False
