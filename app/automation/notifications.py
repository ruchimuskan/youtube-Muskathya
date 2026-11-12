from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self) -> None:
        self.settings = get_settings()

    def send(self, subject: str, body: str) -> None:
        sent = False
        if self.settings.telegram_bot_token and self.settings.telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
                httpx.post(url, json={"chat_id": self.settings.telegram_chat_id, "text": f"{subject}\n\n{body}"})
                sent = True
            except httpx.HTTPError as exc:
                logger.warning("Telegram notify failed: %s", exc)

        if self.settings.smtp_host and self.settings.notify_email:
            try:
                msg = EmailMessage()
                msg["Subject"] = subject
                msg["From"] = self.settings.smtp_user or self.settings.notify_email
                msg["To"] = self.settings.notify_email
                msg.set_content(body)
                with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as smtp:
                    smtp.starttls()
                    if self.settings.smtp_user:
                        smtp.login(self.settings.smtp_user, self.settings.smtp_password)
                    smtp.send_message(msg)
                sent = True
            except OSError as exc:
                logger.warning("Email notify failed: %s", exc)

        if not sent:
            logger.info("[notification] %s — %s", subject, body)
