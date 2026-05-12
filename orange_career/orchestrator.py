from __future__ import annotations

import logging

from .api_client import AtsApiClient
from .config import load_settings, validate_settings
from .sheets_client import SheetsClient
from .telegram_client import TelegramClient
from .seatalk_webhook_client import SeatalkWebhookClient
from .summary_client import SummaryClient


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3] + "..."


def _build_message(
    job_title: str,
    city: str,
    summary: str,
    job_id: str,
    limit: int,
) -> str:
    parts = [
        f"**Title:** {job_title}",
        f"**City:** {city}",
        "",
        summary,
        "",
        f"**Job ID:** {job_id}",
    ]
    text = "\n".join(parts)
    return _truncate(text, limit)


def run() -> None:
    settings = load_settings()
    validate_settings(settings)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    sheets = SheetsClient(
        credentials_b64=settings.google_credentials_base64,
        spreadsheet_id=settings.google_sheet_id,
        jobs_sheet=settings.sheets_jobs_name,
        logs_sheet=settings.sheets_logs_name,
    )
    api = AtsApiClient(settings.ats_url_template, settings.request_timeout_seconds)
    summary_client = SummaryClient()
    telegram = TelegramClient(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        timeout_seconds=settings.request_timeout_seconds,
    )
    seatalk_webhook = None
    if settings.seatalk_webhook_url:
        seatalk_webhook = SeatalkWebhookClient(
            webhook_url=settings.seatalk_webhook_url,
            signature_secret=settings.seatalk_webhook_signature,
            bot_name=settings.seatalk_bot_name,
            timeout_seconds=settings.request_timeout_seconds,
        )

    known_jobs = sheets.get_known_jobs()
    job_statuses = sheets.get_job_statuses()
    current_api_jobs: set[str] = set()
    had_api_error = False

    for city in settings.cities:
        try:
            jobs = api.fetch_jobs(city)
        except Exception as exc:
            logging.exception("ATS request failed for city=%s", city)
            sheets.log_event("ERROR", f"ATS request failed for city={city}", str(exc))
            had_api_error = True
            continue

        for job in jobs:
            job_id = str(job.get("job_id") or job.get("id") or "").strip()
            if not job_id or job_id in known_jobs:
                if job_id:
                    current_api_jobs.add(job_id)
                    if job_statuses.get(job_id) == "closed":
                        sheets.update_job_status(job_id, "active")
                continue

            job_title = str(job.get("job_name") or "Unknown title")
            current_api_jobs.add(job_id)

            try:
                summary = summary_client.summarize_job(job, job_id)
                message = _build_message(
                    job_title,
                    city,
                    summary,
                    job_id,
                    4096,  # limite máximo do Telegram por mensagem
                )
                telegram.send_message(message)
                if seatalk_webhook:
                    seatalk_webhook.send_text_message(message)
                # seatalk.send_markdown_message(message)  # aguardando aprovação SeaTalk
                sheets.save_new_job(job_id, job_title, city, summary, source="ats")
                known_jobs.add(job_id)
                job_statuses[job_id] = "active"
                logging.info("Saved job_id=%s city=%s", job_id, city)
            except Exception as exc:
                logging.exception("Job processing failed job_id=%s", job_id)
                sheets.log_event("ERROR", f"Job processing failed job_id={job_id}", str(exc))

    if had_api_error:
        logging.warning("Skipping closed-job detection because at least one ATS request failed")
        return

    closed_jobs = sheets.get_active_jobs() - current_api_jobs
    for job_id in sorted(closed_jobs):
        if sheets.update_job_status(job_id, "closed"):
            message = f"**Closed job detected**\n\n**Job ID:** {job_id}\n\nA vaga saiu da API e foi marcada como encerrada."
            try:
                telegram.send_message(message)
                if seatalk_webhook:
                    seatalk_webhook.send_text_message(message)
                logging.info("Marked job_id=%s as closed", job_id)
            except Exception as exc:
                logging.exception("Closed job notification failed job_id=%s", job_id)
                sheets.log_event("ERROR", f"Closed job notification failed job_id={job_id}", str(exc))
