from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ValidationResult:
    passed: bool
    label: str
    notes: list[str]
    source_anchor: str


def validate_summary(document: dict, summary: str) -> ValidationResult:
    text = " ".join(
        [
            str(document.get("title") or ""),
            str(document.get("abstract") or ""),
            str(document.get("action") or ""),
        ]
    ).lower()
    doc_type = (document.get("type") or "").upper()
    notes: list[str] = []
    passed = True

    if doc_type == "PRORULE" and " requires " in f" {summary.lower()} ":
        notes.append("Summary may overstate a proposal as a current requirement.")
        passed = False
    if doc_type == "NOTICE" and "effective" in summary.lower() and not document.get("effective_on"):
        notes.append("Summary mentions an effective date for a notice without a listed effective date.")
        passed = False
    if "exception" in text and "exception" not in summary.lower():
        notes.append("Source mentions exceptions; review the source text before relying on the summary.")
    if not summary.strip():
        notes.append("Summary is empty.")
        passed = False

    anchor_bits = [
        f"Type: {document.get('type') or 'N/A'}",
        f"Effective: {document.get('effective_on') or 'N/A'}",
        f"Comments close: {document.get('comments_close_on') or 'N/A'}",
    ]
    return ValidationResult(
        passed=passed,
        label="Verified ✔" if passed else "Needs Review ⚠",
        notes=notes,
        source_anchor=" | ".join(anchor_bits),
    )
