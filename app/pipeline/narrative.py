"""
Step (d): LLM Narrative Summary

A single LLM call producing structured JSON: total spend by currency,
top 3 merchants, anomaly count, a short narrative, and a risk_level.

We compute the hard numbers (totals, top merchants, anomaly count)
deterministically in Python first - the LLM is only trusted for the
narrative prose and risk_level judgment call, not for arithmetic. This is
both more reliable and cheaper than asking the LLM to do the math itself.
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from app.pipeline.llm_client import call_llm

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """You are a financial analyst summarising a batch of transactions.

Facts:
- Total spend INR: {total_inr}
- Total spend USD: {total_usd}
- Top merchants by spend: {top_merchants}
- Anomaly count: {anomaly_count}
- Category breakdown: {category_breakdown}

Respond ONLY with a JSON object of this exact shape:
{{
  "narrative": "<2-3 sentence plain-English summary of spending patterns and any risk signals>",
  "risk_level": "<low|medium|high>"
}}
"""


def compute_deterministic_stats(df: pd.DataFrame) -> dict:
    total_inr = df.loc[df["currency"] == "INR", "amount"].fillna(0).sum()
    total_usd = df.loc[df["currency"] == "USD", "amount"].fillna(0).sum()

    top_merchants = (
        df.groupby("merchant")["amount"]
        .sum()
        .fillna(0)
        .sort_values(ascending=False)
        .head(3)
    )
    top_merchants_list = [
        {"merchant": m, "total_amount": round(float(a), 2)} for m, a in top_merchants.items() if m
    ]

    anomaly_count = int(df["is_anomaly"].sum())
    category_breakdown = (
        df.groupby("category")["amount"].sum().fillna(0).round(2).to_dict()
    )

    return {
        "total_spend_inr": round(float(total_inr), 2),
        "total_spend_usd": round(float(total_usd), 2),
        "top_merchants": top_merchants_list,
        "anomaly_count": anomaly_count,
        "category_breakdown": category_breakdown,
    }


def generate_narrative_summary(df: pd.DataFrame) -> dict:
    stats = compute_deterministic_stats(df)

    prompt = _PROMPT_TEMPLATE.format(
        total_inr=stats["total_spend_inr"],
        total_usd=stats["total_spend_usd"],
        top_merchants=stats["top_merchants"],
        anomaly_count=stats["anomaly_count"],
        category_breakdown=stats["category_breakdown"],
    )

    raw, failed = call_llm(prompt)

    narrative = None
    risk_level = None

    if not failed:
        try:
            parsed = json.loads(raw)
            narrative = parsed.get("narrative")
            risk_level = parsed.get("risk_level")
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.warning("Failed to parse LLM narrative response: %s", exc)
            failed = True

    if failed or not narrative:
        # Deterministic fallback so the job still completes meaningfully.
        narrative = (
            f"Processed {len(df)} transactions totalling INR {stats['total_spend_inr']} "
            f"and USD {stats['total_spend_usd']}, with {stats['anomaly_count']} flagged "
            "as anomalies. (LLM narrative generation failed; this is a fallback summary.)"
        )
        risk_level = "medium" if stats["anomaly_count"] > 0 else "low"

    return {**stats, "narrative": narrative, "risk_level": risk_level, "llm_failed": failed}
