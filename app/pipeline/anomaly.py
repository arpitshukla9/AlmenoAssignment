"""
Step (b): Anomaly Detection

Two rules, per spec:
  1. Statistical outlier: amount > 3x the account's median amount.
  2. Domestic-mismatch: currency == USD but merchant is a known
     domestic-only brand (Swiggy, Ola, IRCTC, ...).

A row can be flagged by both rules; reasons are joined with '; '.
"""
from __future__ import annotations

import pandas as pd

from app.config import settings


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_anomaly"] = False
    df["anomaly_reason"] = ""

    # --- Rule 1: statistical outlier vs. account median ---
    medians = df.groupby("account_id")["amount"].median()
    threshold_multiplier = settings.outlier_median_multiplier

    def _outlier_reason(row):
        acct_median = medians.get(row["account_id"])
        amount = row["amount"]
        if acct_median and acct_median > 0 and amount is not None:
            if amount > threshold_multiplier * acct_median:
                return f"amount {amount} exceeds {threshold_multiplier}x account median ({acct_median:.2f})"
        return None

    outlier_reasons = df.apply(_outlier_reason, axis=1)

    # --- Rule 2: USD currency on a domestic-only merchant ---
    domestic_brands = {m.lower() for m in settings.domestic_only_merchants}

    def _domestic_mismatch_reason(row):
        merchant = (row.get("merchant") or "").lower()
        currency = (row.get("currency") or "").upper()
        if currency == "USD" and merchant in domestic_brands:
            return f"USD currency on domestic-only merchant '{row['merchant']}'"
        return None

    mismatch_reasons = df.apply(_domestic_mismatch_reason, axis=1)

    reasons = []
    flags = []
    for o, m in zip(outlier_reasons, mismatch_reasons):
        parts = [r for r in (o, m) if r]
        reasons.append("; ".join(parts))
        flags.append(bool(parts))

    df["is_anomaly"] = flags
    df["anomaly_reason"] = reasons
    return df
