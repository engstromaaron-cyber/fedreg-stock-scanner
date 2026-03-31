from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import requests

BASE_URL = "https://www.federalregister.gov/api/v1"
DEFAULT_FIELDS = [
    "abstract",
    "action",
    "agencies",
    "agency_names",
    "body_html_url",
    "citation",
    "comments_close_on",
    "document_number",
    "effective_on",
    "html_url",
    "publication_date",
    "raw_text_url",
    "regulation_id_numbers",
    "title",
    "topics",
    "type",
]


@dataclass(slots=True)
class SearchConfig:
    days_ahead: int = 30
    published_since_days: int = 21
    page_size: int = 100
    include_final: bool = True
    include_proposed: bool = True
    include_notice: bool = True
    include_public_inspection: bool = False


class FederalRegisterClient:
    """Small wrapper around the public FederalRegister.gov API."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "fedreg-stock-scanner/1.0",
                "Accept": "application/json",
            }
        )

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self.session.get(
            f"{BASE_URL}/{path}", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def search_documents(
        self,
        *,
        start_date: date,
        end_date: date,
        page: int = 1,
        per_page: int = 100,
        document_types: list[str] | None = None,
    ) -> dict[str, Any]:
        types = document_types or ["RULE", "PRORULE", "NOTICE"]
        params: dict[str, Any] = {
            "conditions[publication_date][gte]": start_date.isoformat(),
            "conditions[publication_date][lte]": end_date.isoformat(),
            "order": "newest",
            "page": page,
            "per_page": per_page,
        }
        for field in DEFAULT_FIELDS:
            params.setdefault("fields[]", [])
            params["fields[]"].append(field)
        for item in types:
            params.setdefault("conditions[type][]", [])
            params["conditions[type][]"].append(item)
        return self._get("documents.json", params)

    def current_public_inspection(self) -> dict[str, Any]:
        params: dict[str, Any] = {"per_page": 1000}
        for field in DEFAULT_FIELDS:
            params.setdefault("fields[]", [])
            params["fields[]"].append(field)
        try:
            return self._get("public-inspection-documents/current.json", params)
        except requests.RequestException:
            return {"results": []}

    def fetch_relevant_documents(self, config: SearchConfig) -> list[dict[str, Any]]:
        today = date.today()
        published_since = today - timedelta(days=config.published_since_days)

        doc_types: list[str] = []
        if config.include_final:
            doc_types.append("RULE")
        if config.include_proposed:
            doc_types.append("PRORULE")
        if config.include_notice:
            doc_types.append("NOTICE")
        if not doc_types:
            doc_types = ["RULE", "PRORULE", "NOTICE"]

        published = self._collect_paged_documents(
            start_date=published_since,
            end_date=today,
            per_page=config.page_size,
            document_types=doc_types,
        )

        public_inspection: list[dict[str, Any]] = []
        if config.include_public_inspection:
            payload = self.current_public_inspection()
            public_inspection = payload.get("results", [])
            if doc_types:
                public_inspection = [
                    item for item in public_inspection if (item.get("type") or "") in doc_types
                ]

        merged = published + public_inspection
        return self._dedupe_documents(merged)

    def _collect_paged_documents(
        self, *, start_date: date, end_date: date, per_page: int, document_types: list[str]
    ) -> list[dict[str, Any]]:
        page = 1
        results: list[dict[str, Any]] = []
        while True:
            payload = self.search_documents(
                start_date=start_date,
                end_date=end_date,
                page=page,
                per_page=per_page,
                document_types=document_types,
            )
            batch = payload.get("results", [])
            results.extend(batch)
            total_pages = payload.get("total_pages", page)
            if page >= total_pages or not batch:
                break
            page += 1
        return results

    @staticmethod
    def _dedupe_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for doc in documents:
            key = doc.get("document_number") or doc.get("html_url") or doc.get("title")
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(doc)
        return deduped
