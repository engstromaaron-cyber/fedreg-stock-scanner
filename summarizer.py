from __future__ import annotations

from datetime import date, datetime
import re

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")

IMPACT_PHRASES = [
    "would",
    "will",
    "proposes",
    "requires",
    "increase",
    "decrease",
    "restrict",
    "expand",
    "tighten",
    "mandate",
    "compliance",
    "cost",
    "standard",
    "investigation",
    "approval",
    "reclassify",
    "delay",
]


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = TAG_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _pick_sentence(sentences: list[str], fallback: str = "") -> str:
    scored = []
    for sentence in sentences:
        lowered = sentence.lower()
        score = sum(1 for phrase in IMPACT_PHRASES if phrase in lowered)
        score += min(len(sentence) // 80, 3)
        scored.append((score, sentence))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1] if scored else fallback


def format_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date().strftime("%b %d, %Y")
    except ValueError:
        try:
            return date.fromisoformat(value).strftime("%b %d, %Y")
        except ValueError:
            return value


def summarize_document(document: dict, industries: list[str], tickers: list[str], why_it_matters: str) -> str:
    abstract = clean_text(document.get("abstract"))
    agency_names = ", ".join(document.get("agency_names") or [])
    doc_type = (document.get("type") or "document").replace("PRORULE", "proposed rule")
    doc_type = doc_type.replace("RULE", "rule").replace("NOTICE", "notice")
    effective = format_date(document.get("effective_on"))
    comments_close = format_date(document.get("comments_close_on"))

    sentences = [s.strip() for s in SENTENCE_RE.split(abstract) if s.strip()]
    lead = _pick_sentence(sentences, fallback=abstract or clean_text(document.get("title")))

    timing_bits = []
    if effective:
        timing_bits.append(f"effective {effective}")
    if comments_close:
        timing_bits.append(f"comments close {comments_close}")
    timing_text = "; ".join(timing_bits)

    industry_text = industries[0] if industries else "the broader market"
    ticker_text = ", ".join(tickers[:3]) if tickers else "related names"

    parts = [
        f"{agency_names or 'A federal agency'} published a {doc_type} tied most closely to {industry_text}.",
        f"What matters: {lead}",
    ]
    if timing_text:
        parts.append(f"Timing: {timing_text}.")
    if why_it_matters and "Mostly administrative" not in why_it_matters:
        parts.append(f"Market angle: {why_it_matters}")
    parts.append(f"Names to review first: {ticker_text}.")
    return " ".join(part.strip() for part in parts if part.strip())
