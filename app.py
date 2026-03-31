from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd
import streamlit as st

from comments_analyzer import build_comment_analysis
from federal_register_client import FederalRegisterClient, SearchConfig
from industry_classifier import classify_document
from summarizer import summarize_document
from ticker_map import get_tickers
from unified_agenda import load_unified_agenda
from validator import validate_summary
from why_map import get_why


@dataclass(slots=True)
class ScreenedDocument:
    title: str
    agency: str
    document_type: str
    stage_label: str
    publication_date: str
    effective_on: str
    comments_close_on: str
    primary_industry: str
    industries: str
    tickers: str
    summary: str
    why_it_matters: str
    url: str
    relevance_score: int
    impact_score: int
    significance_label: str
    confidence_label: str
    confidence_score: int
    priority_label: str
    front_run: str
    market_stance: str
    sentiment: int
    actionable: bool
    regulatory_signal: bool
    signal_strength: float
    skip_reason: str
    validation_label: str
    validation_notes: str
    source_anchor: str
    has_comments: bool
    comment_summary: str
    comment_pros: str
    comment_cons: str
    comment_count_estimate: int


def stage_label_for(doc_type: str) -> str:
    if doc_type == "RULE":
        return "Rule"
    if doc_type == "PRORULE":
        return "Proposed Rule"
    if doc_type == "NOTICE":
        return "Notice"
    return doc_type or "Unknown"


def significance_label_for(impact: int) -> str:
    if impact >= 8:
        return "High"
    if impact >= 5:
        return "Medium"
    return "Low"


def confidence_breakdown(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if row.get("primary_industry"):
        reasons.append("Clear industry impact")
    if row.get("effective_on") or row.get("comments_close_on"):
        reasons.append("Timeline defined")
    if row.get("document_type") in {"RULE", "PRORULE"}:
        reasons.append("Direct regulatory change")
    if row.get("validation_label", "").startswith("Verified"):
        reasons.append("Summary passed verifier")
    return reasons[:4]


st.set_page_config(page_title="Federal Register Market Scanner", layout="wide")
st.title("Federal Register Market Scanner")
st.caption("For research and monitoring only. Not investment, legal, or tax advice.")
st.caption("Scan recent Federal Register activity for potentially market-relevant regulatory developments.")

with st.sidebar:
    st.header("Version 6 settings")
    published_since_days = st.slider("Days back", min_value=1, max_value=30, value=7)
    min_impact = st.slider("Minimum impact score", min_value=1, max_value=10, value=4)
    include_final = st.checkbox("Final Rules", value=True)
    include_proposed = st.checkbox("Proposed Rules (NPRM)", value=True)
    include_notices = st.checkbox("Notices", value=True)
    include_public_inspection = st.checkbox("Public Inspection", value=False)
    show_actionable_only = st.checkbox("Show only actionable items", value=True)
    max_rows = st.slider("Max rows to display", min_value=10, max_value=200, value=40)
    show_low_relevance = st.checkbox("Show low-relevance / skip items", value=False)


@st.cache_data(ttl=60 * 60)
def run_scan(
    published_since_days: int,
    include_final: bool,
    include_proposed: bool,
    include_notices: bool,
    include_public_inspection: bool,
) -> list[dict[str, Any]]:
    client = FederalRegisterClient(timeout=30)
    config = SearchConfig(
        published_since_days=published_since_days,
        include_final=include_final,
        include_proposed=include_proposed,
        include_notice=include_notices,
        include_public_inspection=include_public_inspection,
    )
    documents = client.fetch_relevant_documents(config)
    screened: list[ScreenedDocument] = []

    for doc in documents:
        match = classify_document(doc)
        if not match.industries and match.impact_score <= 2:
            continue

        primary_industry = match.industries[0] if match.industries else ""
        tickers = get_tickers(primary_industry)
        why_it_matters = get_why(primary_industry) if primary_industry else match.why_it_matters
        summary = summarize_document(doc, [primary_industry] if primary_industry else [], tickers, why_it_matters)
        validation = validate_summary(doc, summary)
        comments = build_comment_analysis(doc)

        screened.append(
            ScreenedDocument(
                title=doc.get("title", "Untitled"),
                agency=", ".join(doc.get("agency_names") or []),
                document_type=doc.get("type", ""),
                stage_label=stage_label_for(doc.get("type", "")),
                publication_date=doc.get("publication_date", ""),
                effective_on=doc.get("effective_on", ""),
                comments_close_on=doc.get("comments_close_on", ""),
                primary_industry=primary_industry,
                industries=", ".join(match.industries),
                tickers=", ".join(tickers),
                summary=summary,
                why_it_matters=why_it_matters,
                url=doc.get("html_url") or doc.get("body_html_url") or "",
                relevance_score=match.score,
                impact_score=match.impact_score,
                significance_label=significance_label_for(match.impact_score),
                confidence_label=match.confidence_label,
                confidence_score=match.confidence_score,
                priority_label=match.priority_label,
                front_run=match.front_run,
                market_stance=match.trade_bias,
                sentiment=match.sentiment,
                actionable=match.is_actionable,
                regulatory_signal=match.tradeable_signal,
                signal_strength=match.signal_strength,
                skip_reason=match.skip_reason,
                validation_label=validation.label,
                validation_notes=" | ".join(validation.notes),
                source_anchor=validation.source_anchor,
                has_comments=comments["has_comments"],
                comment_summary=comments["comment_summary"],
                comment_pros=" | ".join(comments["comment_pros"]),
                comment_cons=" | ".join(comments["comment_cons"]),
                comment_count_estimate=comments["comment_count_estimate"],
            )
        )

    priority_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    screened.sort(
        key=lambda item: (
            item.regulatory_signal,
            priority_order.get(item.priority_label, 0),
            item.signal_strength,
            item.impact_score,
            item.confidence_score,
            item.publication_date,
        ),
        reverse=True,
    )
    return [asdict(item) for item in screened]


tab_daily, tab_agenda = st.tabs(["Daily Signals", "Unified Agenda (Forward Look)"])

with tab_daily:
    try:
        rows = run_scan(
            published_since_days,
            include_final,
            include_proposed,
            include_notices,
            include_public_inspection,
        )
    except Exception as exc:  # pragma: no cover
        st.error("The scan could not complete right now.")
        st.exception(exc)
        st.stop()

    filtered = [row for row in rows if row["impact_score"] >= min_impact]
    if show_actionable_only:
        filtered = [row for row in filtered if row["actionable"]]
    if not show_low_relevance:
        filtered = [row for row in filtered if row["priority_label"] != "Low"]
    filtered = filtered[:max_rows]

    if not filtered:
        st.warning("No documents met the current filters.")
        st.stop()

    st.subheader("Top 3 Signals That Actually Matter Today")
    top_signals = [row for row in filtered if row["regulatory_signal"]][:3]
    if not top_signals:
        top_signals = [row for row in filtered if row["priority_label"] in {"Critical", "High"}][:3]

    for idx, row in enumerate(top_signals, start=1):
        emoji = "🔴" if row["sentiment"] < 0 else "🟢" if row["sentiment"] > 0 else "🟡"
        signal_tag = "📌 High regulatory significance" if row["regulatory_signal"] else "👀 Watchlist candidate"
        st.markdown(
            f"**{idx}. {emoji} {row['title']}**  \n"
            f"{signal_tag} | Stage: {row['stage_label']} | {row['front_run']} | "
            f"Impact {row['impact_score']}/10 | Confidence {row['confidence_label']} | "
            f"Signal strength {row['signal_strength']}/10"
        )
        st.markdown(f"**Regulatory Significance:** {row['significance_label']}")
        st.markdown(f"**Market Stance:** {row['market_stance']}")
        st.caption(row["why_it_matters"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Results", len(filtered))
    with col2:
        st.metric("High significance", sum(1 for row in filtered if row["regulatory_signal"]))
    with col3:
        avg_sentiment = round(sum(row["sentiment"] for row in filtered) / len(filtered), 2)
        st.metric("Average sentiment", avg_sentiment)
    with col4:
        st.metric("Critical / High", sum(1 for row in filtered if row["priority_label"] in {"Critical", "High"}))

    chart_df = pd.DataFrame(filtered)
    priority_counts = chart_df["priority_label"].value_counts().reindex(["Critical", "High", "Medium", "Low"], fill_value=0)
    st.bar_chart(priority_counts)

    st.subheader("Detailed cards")
    for row in filtered:
        with st.container(border=True):
            title = row["title"]
            if row["url"]:
                st.markdown(f"### [{title}]({row['url']})")
            else:
                st.markdown(f"### {title}")

            badge = (
                "📌 HIGH REGULATORY SIGNIFICANCE"
                if row["regulatory_signal"]
                else ("🟡 Low relevance — skip" if row["priority_label"] == "Low" else "👀 Watch")
            )
            st.markdown(
                f"**{badge}** | **Priority:** {row['priority_label']} | **Impact:** {row['impact_score']}/10 | "
                f"**Confidence:** {row['confidence_label']} | **Signal strength:** {row['signal_strength']}/10 | "
                f"**Front-run:** {row['front_run']}"
            )
            st.markdown(f"**Regulatory Significance:** {row['significance_label']}")
            st.markdown(f"**Market Stance:** {row['market_stance']}")
            st.markdown(
                f"**Agency:** {row['agency'] or 'N/A'} | **Stage:** {row['stage_label'] or 'N/A'} | "
                f"**Type:** {row['document_type'] or 'N/A'} | **Published:** {row['publication_date'] or 'N/A'}"
            )
            st.markdown(f"**Industries:** {row['industries'] or 'None mapped'}")
            st.markdown(f"**Tickers:** {row['tickers'] or 'None mapped'}")
            st.markdown(f"**Why this matters:** {row['why_it_matters']}")
            st.write(row["summary"])

            st.markdown(f"**Validation:** {row['validation_label']} | {row['source_anchor']}")
            if row["validation_notes"]:
                st.caption(row["validation_notes"])

            breakdown = confidence_breakdown(row)
            if breakdown:
                st.markdown("**Confidence breakdown**")
                for reason in breakdown:
                    st.markdown(f"- {reason}")

            if row["has_comments"]:
                st.markdown("**Estimated comment themes (not actual comments)**")
                st.caption(row["comment_summary"])
                if row["comment_pros"]:
                    st.markdown(f"**Pros raised or likely to be raised:** {row['comment_pros']}")
                if row["comment_cons"]:
                    st.markdown(f"**Cons raised or likely to be raised:** {row['comment_cons']}")

    st.subheader("Exportable table")
    export_df = chart_df[
        [
            "title",
            "agency",
            "stage_label",
            "publication_date",
            "impact_score",
            "significance_label",
            "market_stance",
            "confidence_label",
            "primary_industry",
            "tickers",
            "front_run",
            "url",
        ]
    ].rename(
        columns={
            "stage_label": "stage",
            "significance_label": "regulatory_significance",
            "market_stance": "market_stance",
            "primary_industry": "primary_industry",
        }
    )
    st.dataframe(export_df, width="stretch")
    st.download_button(
        "Download CSV",
        data=export_df.to_csv(index=False).encode("utf-8"),
        file_name="fedreg_market_scanner_v6.csv",
        mime="text/csv",
    )

with tab_agenda:
    st.subheader("Unified Agenda (Forward Look)")
    st.caption("Use this view for twice-yearly portfolio alignment with upcoming policy shifts.")
    agenda_df = load_unified_agenda()
    st.dataframe(agenda_df, width="stretch")
