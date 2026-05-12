from __future__ import annotations

from typing import Any

import requests


class SeatalkWebhookClient:
    def __init__(
        self,
        webhook_url: str,
        signature_secret: str,
        bot_name: str,
        timeout_seconds: int = 20,
    ) -> None:
        if not webhook_url:
            raise ValueError("SEATALK_WEBHOOK_URL is required")
        self._webhook_url = webhook_url
        self._signature_secret = signature_secret
        self._bot_name = bot_name
        self._timeout = timeout_seconds
        self._session = requests.Session()

    def send_text_message(self, text: str) -> None:
        payload: dict[str, Any] = {
            "tag": "text",
            "text": {
                "content": text,
            },
        }
        response = self._session.post(
            self._webhook_url,
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
