from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

import requests


class AtsApiClient:
    def __init__(self, url_template: str, timeout_seconds: int = 20) -> None:
        self._url_template = url_template
        self._timeout = timeout_seconds
        self._session = requests.Session()

    def fetch_jobs(self, city: str) -> list[dict[str, Any]]:
        url = self._url_template.format(city=quote_plus(city))
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return []
        data = payload.get("data", {})
        if not isinstance(data, dict):
            return []
        jobs = data.get("job_list", [])
        if not isinstance(jobs, list):
            return []
        return jobs
