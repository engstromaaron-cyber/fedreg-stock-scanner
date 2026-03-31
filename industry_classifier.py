from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import re

from ticker_map import get_tickers
from why_map import get_why


@dataclass(slots=True)
class MatchResult:
    industries: list[str]
    tickers: list[str]
    score: int
    priority_label: str
    impact_score: int
    confidence_label: str
    confidence_score: int
    front_run: str
    trade_bias: str
    why_it_matters: str
    sentiment: int
    is_actionable: bool
    tradeable_signal: bool
    signal_strength: float
    skip_reason: str


CATEGORY_RULES: list[dict] = [
    {
        "name": "Semiconductors & AI",
        "high_weight": {
            "semiconductor": 7,
            "semiconductors": 7,
            "nand": 10,
            "dram": 10,
            "memory chip": 10,
            "memory chips": 10,
            "gpu": 6,
            "foundry": 7,
            "wafer": 6,
            "chip": 3,
            "chips": 3,
            "export control": 8,
            "advanced computing": 7,
            "ai accelerator": 7,
        },
        "medium_weight": {"server": 2, "data center": 2, "compute": 2},
    },
    {
        "name": "Big Tech & Internet",
        "high_weight": {
            "broadband": 6,
            "online platform": 7,
            "social media": 7,
            "cloud": 5,
            "data privacy": 6,
            "cybersecurity": 6,
            "digital platform": 6,
            "internet service": 6,
            "electronic signatures": 4,
        },
        "medium_weight": {"privacy": 2, "software": 2, "digital service": 3},
    },
    {
        "name": "Banks & Financials",
        "high_weight": {
            "bank": 4,
            "banks": 4,
            "financial stability": 8,
            "capital requirement": 9,
            "capital requirements": 9,
            "capital rules": 9,
            "risk-weighted assets": 10,
            "deposit insurance": 9,
            "nonbank financial": 9,
            "broker-dealer": 6,
            "treasury securities": 7,
            "buyback operations": 7,
            "credit union": 5,
            "fdic": 7,
            "federal reserve": 7,
        },
        "medium_weight": {"credit": 2, "securities": 2, "lending": 3, "payment": 2},
    },
    {
        "name": "Energy & Utilities",
        "high_weight": {
            "lng": 9,
            "pipeline": 9,
            "natural gas": 6,
            "power plant": 8,
            "electric utility": 8,
            "grid": 7,
            "solar": 8,
            "nuclear": 8,
            "reactor": 9,
            "ferc": 8,
            "transmission": 5,
        },
        "medium_weight": {"oil": 3, "gas": 3, "renewable": 3, "environmental review": 4},
    },
    {
        "name": "Healthcare & Pharma",
        "high_weight": {
            "fda": 8,
            "medical device": 8,
            "medical devices": 8,
            "device": 3,
            "drug": 4,
            "pharmaceutical": 6,
            "medicare": 7,
            "medicaid": 7,
            "tuberculosis": 8,
            "claims attachments": 7,
            "schedule i": 7,
            "color additive": 7,
            "diagnosis": 4,
        },
        "medium_weight": {"health care": 3, "healthcare": 3, "clinical": 3, "hospital": 2},
    },
    {
        "name": "Defense & Aerospace",
        "high_weight": {
            "airworthiness directive": 8,
            "airworthiness directives": 8,
            "aircraft": 5,
            "aerospace": 6,
            "boeing": 8,
            "airbus": 7,
            "pratt & whitney": 8,
            "helicopter": 5,
            "satellite": 6,
            "defense": 6,
            "export administration": 6,
        },
        "medium_weight": {"faa": 2, "aviation": 2, "air force": 2, "military": 3},
    },
    {
        "name": "Autos & EV",
        "high_weight": {
            "in-vehicle": 9,
            "motor vehicle": 9,
            "vehicles": 4,
            "vehicle": 4,
            "automobile": 6,
            "electric vehicle": 8,
            "battery": 7,
            "infotainment": 10,
            "tesla": 10,
            "nhtsa": 9,
            "fuel economy": 7,
        },
        "medium_weight": {"charging": 4, "recall": 4, "autonomous": 4, "ev": 3},
    },
    {
        "name": "Industrials & Transport",
        "high_weight": {
            "railroad": 7,
            "maritime": 7,
            "trucking": 6,
            "logistics": 5,
            "freight": 6,
            "shipping": 5,
            "air carrier": 6,
            "supply chain": 5,
            "simulator": 4,
        },
        "medium_weight": {"transportation": 2, "warehouse": 2, "aviation": 2, "helicopter": 2},
    },
    {
        "name": "Consumer & Retail",
        "high_weight": {
            "consumer product": 7,
            "product safety": 6,
            "safety standard": 7,
            "portable hook-on chairs": 10,
            "labeling": 4,
            "retail": 4,
            "recall": 5,
        },
        "medium_weight": {"household": 2, "infant": 3},
    },
]

LOW_SIGNAL_PHRASES = [
    "information collection",
    "request for comments",
    "comment request",
    "submission to the office of management and budget",
    "clearance of a renewed approval",
    "renewal of a previously approved information collection",
    "solicitation of nominations",
    "delegated authority",
    "system of records",
    "matching program",
    "amendment of class d airspace",
    "amendment of class e airspace",
    "administrative change",
    "renaming of restricted areas",
    "geographic coordinates",
    "airport/facility directory",
    "chart supplement",
    "privacy act of 1974",
]

MEDIUM_SIGNAL_PHRASES = [
    "guidance for industry",
    "availability",
    "delay of effective date",
    "notice of revised schedule",
    "application for limited amendment",
    "application for final commitment",
    "clarification of deposit insurance",
]

HIGH_SIGNAL_PHRASES = [
    "institution of investigation",
    "notice of institution of investigation",
    "interim final rule",
    "final rule",
    "proposed rule",
    "reclassification",
    "export control",
    "capital requirement",
    "capital rules",
    "risk-weighted assets",
    "supervision and regulation",
    "safety standard",
    "placement in schedule i",
    "deposit insurance",
    "defect petition",
    "liquefied natural gas",
    "airworthiness directive",
    "airworthiness directives",
]

NEGATIVE_HINTS = [
    "investigation",
    "violation",
    "restrict",
    "restriction",
    "penalty",
    "defect",
    "recall",
    "withdrawal",
    "denial",
    "schedule i",
]

POSITIVE_HINTS = [
    "streamlining",
    "approval",
    "guarantee",
    "commitment",
    "expanded",
    "eligibility",
    "efficiency",
    "modernization",
    "technology-inclusive",
    "clarification",
]

WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(parts: Iterable[str | None]) -> str:
    text = " ".join(part for part in parts if part)
    return WHITESPACE_RE.sub(" ", text.lower()).strip()


def _count_weighted(text: str, mapping: dict[str, int]) -> int:
    return sum(weight for phrase, weight in mapping.items() if phrase in text)


def _sentiment(text: str) -> int:
    score = 0
    for phrase in POSITIVE_HINTS:
        if phrase in text:
            score += 1
    for phrase in NEGATIVE_HINTS:
        if phrase in text:
            score -= 1
    return max(-5, min(5, score))


def _materiality_bucket(text: str, doc_type: str) -> str:
    if any(phrase in text for phrase in LOW_SIGNAL_PHRASES):
        return "low"
    if any(phrase in text for phrase in HIGH_SIGNAL_PHRASES):
        return "high"
    if doc_type in {"RULE", "PRORULE"}:
        return "medium"
    if any(phrase in text for phrase in MEDIUM_SIGNAL_PHRASES):
        return "medium"
    return "low"


def _is_actionable(text: str, doc_type: str, top_score: int, bucket: str) -> bool:
    if bucket == "low" or top_score < 6:
        return False
    if doc_type == "RULE" and top_score >= 7:
        return True
    if doc_type == "PRORULE" and top_score >= 8:
        return True
    return bucket == "high" and top_score >= 8


def _front_run(doc_type: str, text: str, actionable: bool) -> str:
    if not actionable:
        return "Monitor"
    if "institution of investigation" in text:
        return "Monitor"
    if doc_type == "RULE":
        return "Immediate"
    if doc_type == "PRORULE":
        return "1-3 weeks"
    return "Monitor"


def _market_stance(sentiment: int, impact: int, actionable: bool, front_run: str, text: str) -> str:
    if not actionable or impact < 6:
        return "Neutral watch"
    if sentiment <= -2 and impact >= 7:
        return "Bearish watch"
    if sentiment >= 2 and impact >= 7 and front_run in {"Immediate", "1-3 weeks"}:
        return "Bullish watch"
    if "investigation" in text or "defect" in text or "schedule i" in text:
        return "Bearish watch"
    return "Neutral watch"


def _confidence_label(confidence_score: int) -> str:
    if confidence_score >= 8:
        return "High"
    if confidence_score >= 5:
        return "Medium"
    return "Low"


def _priority_label(impact: int, confidence: int, actionable: bool, regulatory_signal: bool) -> str:
    if regulatory_signal and impact >= 8 and confidence >= 7:
        return "Critical"
    if actionable and impact >= 6 and confidence >= 5:
        return "High"
    if impact >= 4:
        return "Medium"
    return "Low"


def _significance_label(impact: int) -> str:
    if impact >= 8:
        return "High"
    if impact >= 5:
        return "Medium"
    return "Low"


def _signal_strength(impact: int, confidence: int, sentiment: int, actionable: bool) -> float:
    score = (impact * 0.55) + (confidence * 0.3) + (abs(sentiment) * 0.2)
    if actionable:
        score += 0.4
    return round(min(10.0, score), 1)


def _trim_top_matches(matches: list[tuple[str, int]]) -> list[tuple[str, int]]:
    if not matches:
        return []
    top = matches[0][1]
    trimmed = [m for m in matches if m[1] >= max(5, top - 3)]
    return trimmed[:2]


def _primary_industry(top_matches: list[tuple[str, int]]) -> str:
    return top_matches[0][0] if top_matches else ""


def classify_document(document: dict) -> MatchResult:
    text = normalize_text(
        [
            document.get("title"),
            document.get("abstract"),
            document.get("action"),
            document.get("dates"),
            " ".join(document.get("agency_names") or []),
            " ".join(document.get("topics") or []),
        ]
    )
    title_text = normalize_text([document.get("title")])
    doc_type = (document.get("type") or "").upper()
    bucket = _materiality_bucket(text, doc_type)

    matches: list[tuple[str, int]] = []
    for rule in CATEGORY_RULES:
        high = _count_weighted(text, rule["high_weight"])
        medium = _count_weighted(text, rule["medium_weight"])
        total = high + medium
        if total > 0:
            matches.append((rule["name"], total))

    matches.sort(key=lambda item: item[1], reverse=True)
    top_matches = _trim_top_matches(matches)
    industries = [name for name, _score in top_matches]
    top_score = top_matches[0][1] if top_matches else 0
    base_score = sum(score for _, score in top_matches)

    sentiment = _sentiment(text)
    actionable = _is_actionable(text, doc_type, top_score, bucket)

    impact_base = 6 if bucket == "high" else 4 if bucket == "medium" else 1
    if doc_type == "RULE":
        impact_base += 1
    elif doc_type == "NOTICE":
        impact_base -= 1

    if top_score >= 12:
        impact_base += 2
    elif top_score >= 9:
        impact_base += 1

    # boosters
    if "institution of investigation" in text:
        impact_base += 1
    if "risk-weighted assets" in text or "capital rules" in text or "systemic risk" in text:
        impact_base += 2
    if "import" in text or "trade restriction" in text or "export control" in text:
        impact_base += 1

    # penalties
    if "airworthiness directive" in text or "airworthiness directives" in text:
        impact_base -= 1
    if "delay of effective date" in text:
        impact_base -= 2
    if "system of records" in title_text or "matching program" in title_text or "privacy act of 1974" in title_text:
        impact_base = min(3, impact_base)
    if "airspace" in title_text or "restricted area" in title_text or "geographic coordinates" in text or "chart supplement" in text:
        impact_base = min(2, impact_base)
    if "information collection" in text or "request for comments" in text:
        impact_base = min(3, impact_base)
    if "renaming" in title_text:
        impact_base = min(2, impact_base)

    impact_score = max(1, min(10, impact_base))

    confidence_score = 2
    if top_matches:
        confidence_score += 2
    if len(top_matches) == 1:
        confidence_score += 2
    if top_score >= 9:
        confidence_score += 2
    elif top_score >= 7:
        confidence_score += 1
    if doc_type in {"RULE", "PRORULE"}:
        confidence_score += 1
    if bucket == "low":
        confidence_score -= 2
    if impact_score <= 3:
        confidence_score = min(confidence_score, 4)
    confidence_score = max(1, min(10, confidence_score))

    primary = _primary_industry(top_matches)
    tickers = get_tickers(primary)
    why_it_matters = get_why(primary) if primary else "Mostly administrative or too broad to cleanly map to a specific public-market industry."

    front_run = _front_run(doc_type, text, actionable)
    trade_bias = _market_stance(sentiment, impact_score, actionable, front_run, text)
    signal_strength = _signal_strength(impact_score, confidence_score, sentiment, actionable)
    regulatory_signal = actionable and impact_score >= 7 and confidence_score >= 6 and signal_strength >= 6.5

    skip_reason = ""
    if impact_score <= 2:
        skip_reason = "Low relevance — mostly administrative and unlikely to move public stocks directly."
    elif not actionable:
        skip_reason = "Low relevance — useful context, but not a strong monitoring signal yet."

    priority_label = _priority_label(impact_score, confidence_score, actionable, regulatory_signal)
    confidence_label = _confidence_label(confidence_score)

    return MatchResult(
        industries=industries,
        tickers=tickers,
        score=base_score,
        priority_label=priority_label,
        impact_score=impact_score,
        confidence_label=confidence_label,
        confidence_score=confidence_score,
        front_run=front_run,
        trade_bias=trade_bias,
        why_it_matters=why_it_matters,
        sentiment=sentiment,
        is_actionable=actionable,
        tradeable_signal=regulatory_signal,
        signal_strength=signal_strength,
        skip_reason=skip_reason,
    )
