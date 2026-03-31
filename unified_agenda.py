from __future__ import annotations

import pandas as pd
import requests


FALLBACK_ROWS = [
    {
        "Agency": "Office of Information and Regulatory Affairs",
        "Title": "Unified Agenda feed unavailable",
        "Stage": "Reference",
        "Target Date": "",
        "Portfolio Relevance": "Use when the live agenda feed is unavailable.",
        "Abstract": "The Unified Agenda is best used as a twice-yearly forward-looking planning tool for policy monitoring.",
    }
]


def load_unified_agenda() -> pd.DataFrame:
    urls = [
        "https://www.reginfo.gov/public/do/eAgendaJson",
        "https://www.reginfo.gov/public/do/eAgendaMain",
    ]
    for url in urls:
        try:
            response = requests.get(url, timeout=12)
            response.raise_for_status()
            if "json" not in response.headers.get("content-type", ""):
                continue
            payload = response.json()
            rows = []
            results = payload.get("results") or payload.get("Result") or []
            for item in results:
                title = item.get("title") or item.get("ruleTitle") or ""
                stage = item.get("stage") or item.get("stageOfRulemaking") or ""
                abstract = item.get("abstract") or item.get("summary") or ""
                relevance = _portfolio_relevance(f"{title} {abstract}".lower())
                rows.append(
                    {
                        "Agency": item.get("agency") or item.get("agencyName") or "",
                        "Title": title,
                        "Stage": stage,
                        "Target Date": item.get("targetDate") or item.get("timetable") or "",
                        "Portfolio Relevance": relevance,
                        "Abstract": abstract,
                    }
                )
            if rows:
                return pd.DataFrame(rows)
        except Exception:
            continue
    return pd.DataFrame(FALLBACK_ROWS)


def _portfolio_relevance(text: str) -> str:
    if any(k in text for k in ["bank", "capital", "deposit", "financial"]):
        return "Banks & Financials"
    if any(k in text for k in ["chip", "semiconductor", "ai", "compute"]):
        return "Semiconductors & AI"
    if any(k in text for k in ["drug", "device", "health", "medicare", "fda"]):
        return "Healthcare & Pharma"
    if any(k in text for k in ["reactor", "nuclear", "pipeline", "lng", "utility", "energy"]):
        return "Energy & Utilities"
    if any(k in text for k in ["vehicle", "auto", "battery", "ev"]):
        return "Autos & EV"
    return "General policy monitoring"
