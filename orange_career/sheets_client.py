from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

import gspread
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials


class SheetsClient:
    def __init__(
        self,
        credentials_b64: str,
        spreadsheet_id: str,
        jobs_sheet: str = "Vagas",
        logs_sheet: str = "Logs",
    ) -> None:
        if not credentials_b64:
            raise ValueError("GOOGLE_CREDENTIALS_BASE64 is required")
        if not spreadsheet_id:
            raise ValueError("GOOGLE_SHEET_ID is required")
        creds = self._load_credentials(credentials_b64)
        self._client = gspread.authorize(creds)
        self._spreadsheet = self._client.open_by_key(spreadsheet_id)
        self._jobs_ws = self._get_or_create_worksheet(jobs_sheet, rows=100, cols=7)
        self._logs_ws = self._get_or_create_worksheet(logs_sheet, rows=100, cols=4)
        self._ensure_headers()

    def _load_credentials(self, credentials_b64: str) -> Credentials:
        data = base64.b64decode(credentials_b64)
        payload = json.loads(data.decode("utf-8"))
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        return Credentials.from_service_account_info(payload, scopes=scopes)

    def _get_or_create_worksheet(self, title: str, rows: int, cols: int) -> gspread.Worksheet:
        try:
            return self._spreadsheet.worksheet(title)
        except WorksheetNotFound:
            return self._spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

    def _ensure_headers(self) -> None:
        if not self._jobs_ws.row_values(1):
            self._jobs_ws.update(
                "A1:G1",
                [["job_id", "job_name", "city", "summary_md", "created_at", "source", "status"]],
            )
        elif len(self._jobs_ws.row_values(1)) < 7 or self._jobs_ws.acell("G1").value != "status":
            self._jobs_ws.update("G1", [["status"]])
        if not self._logs_ws.row_values(1):
            self._logs_ws.update(
                "A1:D1",
                [["timestamp", "level", "message", "detail"]],
            )

    def get_known_jobs(self) -> set[str]:
        values = self._jobs_ws.col_values(1)
        if not values:
            return set()
        return {value.strip() for value in values[1:] if value.strip()}

    def get_active_jobs(self) -> set[str]:
        rows = self._jobs_ws.get_all_values()
        if len(rows) <= 1:
            return set()

        active_jobs = set()
        for row in rows[1:]:
            job_id = row[0].strip() if len(row) > 0 and row[0] else ""
            status = row[6].strip().lower() if len(row) > 6 and row[6] else "active"
            if job_id and status != "closed":
                active_jobs.add(job_id)
        return active_jobs

    def get_job_statuses(self) -> dict[str, str]:
        rows = self._jobs_ws.get_all_values()
        statuses: dict[str, str] = {}
        for row in rows[1:]:
            job_id = row[0].strip() if len(row) > 0 and row[0] else ""
            if not job_id:
                continue
            status = row[6].strip().lower() if len(row) > 6 and row[6] else "active"
            statuses[job_id] = status
        return statuses

    def get_job_names(self) -> dict[str, str]:
        rows = self._jobs_ws.get_all_values()
        names: dict[str, str] = {}
        for row in rows[1:]:
            job_id = row[0].strip() if len(row) > 0 and row[0] else ""
            if not job_id:
                continue
            job_name = row[1].strip() if len(row) > 1 and row[1] else "Unknown title"
            names[job_id] = job_name
        return names

    def save_new_job(
        self,
        job_id: str,
        job_name: str,
        city: str,
        summary_md: str,
        source: str = "ats",
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        row = [job_id, job_name, city, summary_md, timestamp, source, "active"]
        self._jobs_ws.append_row(row, value_input_option="RAW")

    def update_job_status(self, job_id: str, status: str) -> bool:
        normalized_status = status.strip().lower()
        if normalized_status not in {"active", "closed"}:
            raise ValueError("status must be active or closed")

        try:
            cell = self._jobs_ws.find(job_id)
        except Exception:
            return False

        self._jobs_ws.update_cell(cell.row, 7, normalized_status)
        return True

    def log_event(self, level: str, message: str, detail: str | None = None) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        row = [timestamp, level, message, detail or ""]
        try:
            self._logs_ws.append_row(row, value_input_option="RAW")
        except Exception:
            pass
