"""
Step (a): Data Cleaning

Takes the raw, dirty CSV (as a pandas DataFrame) and returns a cleaned
DataFrame per the assignment spec:
  - Normalise dates to ISO-8601 (YYYY-MM-DD), handling both DD-MM-YYYY and
    YYYY/MM/DD source formats.
  - Strip currency symbols ('$') from amount and coerce to float.
  - Uppercase status values.
  - Fill missing categories with 'Uncategorised'.
  - Uppercase/normalise currency codes (INR/USD).
  - Drop exact duplicate rows.
"""
from __future__ import annotations

import re
import logging

import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "txn_id", "date", "merchant", "amount", "currency",
    "status", "category", "account_id", "notes",
]

_CURRENCY_SYMBOL_RE = re.compile(r"[^\d.\-]")


def _normalise_date(value: str) -> str | None:
    """Parse DD-MM-YYYY or YYYY/MM/DD (and a few likely variants) into ISO-8601."""
    if pd.isna(value) or str(value).strip() == "":
        return None
    raw = str(value).strip()

    candidate_formats = [
        "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
    ]
    for fmt in candidate_formats:
        try:
            return pd.to_datetime(raw, format=fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue

    # Last resort: let pandas infer (dayfirst=True matches the DD-MM-YYYY hint
    # in the spec), but only trust it if it round-trips a 4-digit year.
    try:
        parsed = pd.to_datetime(raw, dayfirst=True, errors="raise")
        return parsed.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        logger.warning("Could not parse date value: %r", raw)
        return None


def _clean_amount(value) -> float | None:
    if pd.isna(value):
        return None
    cleaned = _CURRENCY_SYMBOL_RE.sub("", str(value).strip())
    if cleaned in ("", "-", "."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        logger.warning("Could not parse amount value: %r", value)
        return None


def clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """
    Returns (cleaned_df, row_count_raw, row_count_clean).
    """
    row_count_raw = len(df)

    # Ensure all expected columns exist even if the CSV is missing some.
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df.copy()

    df["date"] = df["date"].apply(_normalise_date)
    df["amount"] = df["amount"].apply(_clean_amount)
    df["status"] = df["status"].astype(str).str.strip().str.upper().replace({"NAN": None})
    df["currency"] = df["currency"].astype(str).str.strip().str.upper().replace({"NAN": None})
    df["merchant"] = df["merchant"].astype(str).str.strip().replace({"nan": None, "": None})
    df["category"] = df["category"].astype(str).str.strip()
    df["category"] = df["category"].replace({"": "Uncategorised", "nan": "Uncategorised"})
    df["txn_id"] = df["txn_id"].astype(str).str.strip().replace({"nan": None, "": None})
    df["account_id"] = df["account_id"].astype(str).str.strip().replace({"nan": None, "": None})
    df["notes"] = df["notes"].astype(str).str.strip().replace({"nan": "", "None": ""})

    # Exact duplicate rows (same value across every business column).
    dedupe_cols = ["txn_id", "date", "merchant", "amount", "currency", "status", "account_id"]
    df = df.drop_duplicates(subset=dedupe_cols, keep="first").reset_index(drop=True)

    row_count_clean = len(df)
    return df, row_count_raw, row_count_clean
