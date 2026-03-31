from __future__ import annotations

import argparse
import csv
from pathlib import Path

from federal_register_client import FederalRegisterClient, SearchConfig
from industry_classifier import classify_document
from summarizer import summarize_document


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan the Federal Register for market-relevant items.")
    parser.add_argument("--days", type=int, default=21, help="Published lookback window")
    parser.add_argument("--min-impact", type=int, default=4, help="Minimum impact score")
    parser.add_argument("--actionable-only", action="store_true")
    parser.add_argument("--include-public-inspection", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("fedreg_scan.csv"))
    args = parser.parse_args()

    client = FederalRegisterClient()
    config = SearchConfig(
        published_since_days=args.days,
        include_public_inspection=args.include_public_inspection,
    )
    docs = client.fetch_relevant_documents(config)

    rows = []
    for doc in docs:
        match = classify_document(doc)
        if match.impact_score < args.min_impact:
            continue
        if args.actionable_only and not match.is_actionable:
            continue
        rows.append(
            {
                "title": doc.get("title", ""),
                "agency": ", ".join(doc.get("agency_names") or []),
                "type": doc.get("type", ""),
                "publication_date": doc.get("publication_date", ""),
                "effective_on": doc.get("effective_on", ""),
                "comments_close_on": doc.get("comments_close_on", ""),
                "industries": ", ".join(match.industries),
                "tickers": ", ".join(match.tickers),
                "relevance_score": match.score,
                "impact_score": match.impact_score,
                "confidence_label": match.confidence_label,
                "signal_strength": match.signal_strength,
                "tradeable_signal": match.tradeable_signal,
                "summary": summarize_document(doc, match.industries, match.tickers, match.why_it_matters),
                "url": doc.get("html_url") or doc.get("body_html_url") or "",
            }
        )

    rows.sort(key=lambda item: (item["tradeable_signal"], item["signal_strength"], item["publication_date"]), reverse=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["title"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
