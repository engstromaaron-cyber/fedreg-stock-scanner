from __future__ import annotations

from typing import Any


COMMENT_TRIGGER_WORDS = [
    "comment",
    "comments",
    "public comments",
    "solicit",
    "soliciting",
    "comment period",
]


def build_comment_analysis(document: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        [
            str(document.get("title") or ""),
            str(document.get("abstract") or ""),
            str(document.get("action") or ""),
        ]
    ).lower()
    if not any(word in text for word in COMMENT_TRIGGER_WORDS):
        return {
            "has_comments": False,
            "comment_summary": "",
            "comment_pros": [],
            "comment_cons": [],
            "comment_count_estimate": 0,
        }

    pros: list[str] = []
    cons: list[str] = []
    if "modernization" in text or "streamlining" in text or "technology-inclusive" in text:
        pros.append("Some commenters may favor lower friction, modernization, or more flexible compliance paths.")
    if "safety" in text or "investigation" in text or "defect" in text:
        pros.append("Supportive comments may focus on consumer protection, safety, or enforcement clarity.")
    if "cost" in text or "burden" in text or "compliance" in text:
        cons.append("Critical comments may focus on higher compliance costs, reporting burden, or slower approvals.")
    if "proposed rule" in text or "comments close" in text:
        cons.append("Some commenters may argue the proposal is too broad, too narrow, or needs clarifying exceptions.")

    if not pros:
        pros.append("Supportive comments would most likely emphasize policy clarity, safety, or implementation benefits.")
    if not cons:
        cons.append("Critical comments would most likely focus on cost, scope, timing, or unintended consequences.")

    summary = (
        "Comment analysis is a directional research aid. It highlights likely supportive and critical themes, "
        "but it is not a substitute for reading the docket comments directly."
    )
    return {
        "has_comments": True,
        "comment_summary": summary,
        "comment_pros": pros[:3],
        "comment_cons": cons[:3],
        "comment_count_estimate": max(1, len(pros) + len(cons)),
    }
