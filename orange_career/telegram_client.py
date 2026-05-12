from __future__ import annotations

import requests


class TelegramClient:
    """Envia mensagens para um chat via Telegram Bot API."""

    API_BASE = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        timeout_seconds: int = 20,
    ) -> None:
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is required")
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._timeout = timeout_seconds
        self._session = requests.Session()

    def send_message(self, text: str) -> None:
        """Envia uma mensagem em formato Markdown v2."""
        url = self.API_BASE.format(token=self._bot_token)
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        response = self._session.post(url, json=payload, timeout=self._timeout)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram sendMessage failed: {data}")
