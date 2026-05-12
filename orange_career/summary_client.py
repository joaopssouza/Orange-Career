from __future__ import annotations

import html
import re
from typing import Any
import unicodedata


class SummaryClient:
    def summarize_job(self, job: dict[str, Any], job_id: str) -> str:
        summary_input = self._build_summary_input(job, job_id)
        return self._build_final_summary(summary_input)

    def _build_summary_input(self, job: dict[str, Any], job_id: str) -> dict[str, Any]:
        job_name = str(job.get("job_name") or job.get("job_title") or "Vaga")
        job_url = self._build_job_url(job_id)

        description_html = str(job.get("job_description") or "")
        requirements_html = str(job.get("requirements") or "")

        description_text = self._strip_html(description_html)
        requirements_text = self._strip_html(requirements_html)

        req_items: list[str] = []
        benefit_items: list[str] = []

        if requirements_html:
            req_html, benefits_html = self._split_html_by_label(requirements_html, "beneficios")
            req_items = self._extract_html_list_items(req_html)
            benefit_items = self._extract_html_list_items(benefits_html)

        if not req_items:
            req_text = self._extract_section(
                requirements_text,
                start_label="o que voce precisa para assumir o desafio",
                end_labels=("beneficios",),
            )
            req_items = self._split_items(req_text or requirements_text)

        if not benefit_items:
            benefits_text = self._extract_section(
                requirements_text,
                start_label="beneficios",
                end_labels=(),
            )
            benefit_items = self._split_items(benefits_text)

        return {
            "job_name": job_name,
            "job_id": job_id,
            "requirements": req_items,
            "benefits": benefit_items,
            "job_url": job_url,
        }

    def _build_final_summary(self, summary_input: dict[str, Any]) -> str:
        job_name = str(summary_input.get("job_name") or "Vaga")
        job_url = str(summary_input.get("job_url") or self._build_job_url(""))
        requirements = self._format_list_with_emoji(summary_input.get("requirements"), "✅")
        benefits = self._format_list_with_emoji(summary_input.get("benefits"), "🎁")

        return (
            f"## {job_name}\n\n"
            "**Requisitos**\n"
            f"{requirements}\n\n"
            "**Beneficios**\n"
            f"{benefits}\n\n"
            f"**Link da Vaga:**\n{job_url}"
        )

    @staticmethod
    def _build_job_url(job_id: str) -> str:
        if not job_id:
            return "https://careers.shopee.com.br/job-detail/UNKNOWN/1"
        return f"https://careers.shopee.com.br/job-detail/{job_id}/1"

    @staticmethod
    def _strip_html(raw: str) -> str:
        if not raw:
            return ""
        text = re.sub(r"<(br|/p|/li|/div|/h[1-6])[^>]*>", "\n", raw, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"\s+\n", "\n", text)
        text = re.sub(r"\n\s+", "\n", text)
        text = text.strip()
        return text

    @staticmethod
    def _normalize_with_map(text: str) -> tuple[str, list[int]]:
        normalized_chars: list[str] = []
        index_map: list[int] = []
        for idx, ch in enumerate(text):
            decomposed = unicodedata.normalize("NFKD", ch)
            for part in decomposed:
                if unicodedata.combining(part):
                    continue
                normalized_chars.append(part.lower())
                index_map.append(idx)
        return "".join(normalized_chars), index_map

    def _extract_section(
        self,
        text: str,
        start_label: str,
        end_labels: tuple[str, ...],
    ) -> str:
        if not text:
            return ""
        normalized_text, index_map = self._normalize_with_map(text)
        start_pos = normalized_text.find(start_label)
        if start_pos == -1:
            return ""
        start_end_pos = start_pos + len(start_label)
        if start_end_pos - 1 >= len(index_map):
            return ""
        start_index = index_map[start_end_pos - 1] + 1

        end_index = len(text)
        for label in end_labels:
            end_pos = normalized_text.find(label, start_end_pos)
            if end_pos != -1:
                end_index = min(end_index, index_map[end_pos])
        return text[start_index:end_index].strip()

    @staticmethod
    def _split_items(text: str) -> list[str]:
        if not text:
            return []
        parts = re.split(r"(?:\r?\n|;|\s+-\s+|\s+[\u2022●\*]\s+|\.(?=\s+[A-ZÁÀÃÂÉÈÊÍÌÎÓÒÔÕÚÙÛ]))+", text)
        items = [part.strip(" .") for part in parts if part.strip(" .")]
        return items

    def _split_html_by_label(self, raw_html: str, label: str) -> tuple[str, str]:
        if not raw_html:
            return raw_html, ""
        normalized_text, index_map = self._normalize_with_map(raw_html)
        start_pos = normalized_text.find(label)
        if start_pos == -1:
            return raw_html, ""
        end_pos = start_pos + len(label)
        if end_pos - 1 >= len(index_map):
            return raw_html, ""
        split_index = index_map[end_pos - 1] + 1
        return raw_html[:split_index], raw_html[split_index:]

    def _extract_html_list_items(self, raw_html: str) -> list[str]:
        if not raw_html:
            return []
        items = re.findall(r"<li[^>]*>(.*?)</li>", raw_html, flags=re.I | re.S)
        cleaned: list[str] = []
        for item in items:
            text = self._strip_html(item)
            text = self._clean_benefit_item(text)
            if text:
                cleaned.append(text)
        if cleaned:
            return cleaned

        fallback_text = self._strip_html(raw_html)
        return self._filter_benefit_items(self._split_items(fallback_text))

    @staticmethod
    def _clean_benefit_item(text: str) -> str:
        if not text:
            return ""
        normalized = re.sub(r"\s+", " ", text).strip()
        if SummaryClient._looks_like_boilerplate(normalized):
            return ""
        return normalized

    @staticmethod
    def _looks_like_boilerplate(text: str) -> bool:
        normalized = re.sub(r"\s+", " ", text).strip().lower()
        if not normalized:
            return True
        boilerplate_prefixes = (
            "vem fazer história",
            "o que te faz único",
            "o que te faz unico",
            "sobre a shô",
            "sobre a sho",
            "sobre a empresa",
            "vem fazer historia",
        )
        if any(normalized.startswith(prefix) for prefix in boilerplate_prefixes):
            return True
        if normalized in {"vêm fazer história com a gente", "vem fazer historia com a gente"}:
            return True
        return False

    def _filter_benefit_items(self, items: list[str]) -> list[str]:
        filtered: list[str] = []
        for item in items:
            cleaned = self._clean_benefit_item(item)
            if cleaned:
                filtered.append(cleaned)
        return filtered

    @staticmethod
    def _format_list_with_emoji(items: Any, emoji: str) -> str:
        if isinstance(items, list) and items:
            return "\n".join(f"- {emoji} {item}" for item in items)
        if isinstance(items, str) and items.strip():
            return f"- {emoji} {items.strip()}"
        return f"- {emoji} Nao informado"
