from __future__ import annotations

from dataclasses import dataclass
import os
import base64

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    ats_url_template: str
    cities: list[str]
    google_credentials_base64: str
    google_sheet_id: str
    sheets_jobs_name: str
    sheets_logs_name: str
    # --- Telegram (notificador ativo) ---
    telegram_bot_token: str
    telegram_chat_id: str
    # --- SeaTalk (webhook conta de sistema) ---
    seatalk_webhook_url: str
    seatalk_webhook_signature: str
    seatalk_bot_name: str
    request_timeout_seconds: int


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value if value else default


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _parse_cities(value: str) -> list[str]:
    return [city.strip() for city in value.split(",") if city.strip()]


def load_settings() -> Settings:
    cities_value = _get_env("CITIES", "betim,belo horizonte,contagem")
    # Support either a raw JSON credentials in GOOGLE_CREDENTIALS or
    # a base64-encoded JSON in GOOGLE_CREDENTIALS_BASE64. If both are
    # present, GOOGLE_CREDENTIALS takes precedence.
    google_credentials_raw = os.getenv("GOOGLE_CREDENTIALS", "").strip()
    google_credentials_b64_env = _get_env("GOOGLE_CREDENTIALS_BASE64", "")

    if google_credentials_raw:
        google_credentials_base64 = base64.b64encode(
            google_credentials_raw.encode("utf-8")
        ).decode("utf-8")
    else:
        google_credentials_base64 = google_credentials_b64_env

    return Settings(
        ats_url_template=_get_env("ATS_URL_TEMPLATE", ""),
        cities=_parse_cities(cities_value),
        google_credentials_base64=google_credentials_base64,
        google_sheet_id=_get_env("GOOGLE_SHEET_ID", ""),
        sheets_jobs_name=_get_env("SHEETS_JOBS_NAME", "Vagas"),
        sheets_logs_name=_get_env("SHEETS_LOGS_NAME", "Logs"),
        # --- Telegram ---
        telegram_bot_token=_get_env("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=_get_env("TELEGRAM_CHAT_ID", ""),
        # --- SeaTalk (webhook conta de sistema) ---
        seatalk_webhook_url=_get_env("SEATALK_WEBHOOK_URL", ""),
        seatalk_webhook_signature=_get_env("SEATALK_WEBHOOK_SIGNATURE", ""),
        seatalk_bot_name=_get_env("SEATALK_BOT_NAME", ""),
        request_timeout_seconds=_get_int_env("REQUEST_TIMEOUT_SECONDS", 20),
    )


def validate_settings(settings: Settings) -> None:
    missing = []
    if not settings.ats_url_template:
        missing.append("ATS_URL_TEMPLATE")
    if not settings.google_credentials_base64:
        missing.append("GOOGLE_CREDENTIALS_BASE64")
    if not settings.google_sheet_id:
        missing.append("GOOGLE_SHEET_ID")
    if not settings.telegram_bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not settings.telegram_chat_id:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        raise RuntimeError("Missing env vars: " + ", ".join(missing))
