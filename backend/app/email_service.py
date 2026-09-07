"""Envio de e-mails transacionais pelo Resend.

Quando RESEND_API_KEY não está configurada, o MVP continua funcionando e
mantém a notificação no banco; isso permite desenvolvimento local sem chave.
"""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import get_settings
from .models import Notification


def send_notification_email(notification: Notification, body: str) -> bool:
    settings = get_settings()
    if not settings.resend_api_key or not notification.recipient_email:
        return False

    html = f"""
    <main style=\"font-family:Arial,sans-serif;max-width:600px;margin:auto;color:#25324a\">
      <h1 style=\"font-size:22px;color:#315efb\">TestCheck</h1>
      <h2 style=\"font-size:18px\">{escape(notification.title)}</h2>
      <p style=\"font-size:15px;line-height:1.5\">{escape(body)}</p>
      <p style=\"font-size:13px;color:#6b778c\">Acesse o TestCheck para acompanhar esta atividade.</p>
      <a href=\"{escape(settings.app_url, quote=True)}/#nonconformities\" style=\"display:inline-block;padding:11px 16px;background:#315efb;color:#fff;text-decoration:none;border-radius:7px\">Abrir não conformidades</a>
    </main>
    """
    try:
        request = Request(
            "https://api.resend.com/emails",
            data=json.dumps(
                {
                "from": settings.email_from,
                "to": [notification.recipient_email],
                "subject": notification.title,
                "html": html,
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                return False
    except (HTTPError, URLError, OSError):
        return False

    notification.email_sent_at = datetime.now(UTC)
    return True
