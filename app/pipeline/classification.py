"""
Step (c): LLM Classification

Only transactions with category == 'Uncategorised' are sent to the LLM.
Calls are batched (settings.llm_batch_size per call) rather than one-per-row.
If a batch ultimately fails after retries, every transaction in that batch
is marked llm_failed=True and falls back to category 'Other' rather than
failing the whole job.
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from app.config import settings
from app.pipeline.llm_client import call_llm, VALID_CATEGORIES

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """You are a financial transaction classifier.
Classify each transaction below into exactly one of these categories:
{categories}

Respond ONLY with a JSON object: {{"categories": ["<category for row 1>", "<category for row 2>", ...]}}
The list must have exactly {n} entries, in the same order as the rows below.

Transactions:
{rows}
"""


def _build_prompt(batch: pd.DataFrame) -> str:
    rows_text = "\n".join(
        f"{i+1}. merchant={row.merchant or 'Unknown'}, notes={row.notes or ''}"
        for i, row in enumerate(batch.itertuples())
    )
    return _PROMPT_TEMPLATE.format(
        categories=", ".join(VALID_CATEGORIES),
        n=len(batch),
        rows=rows_text,
    )


def classify_uncategorised(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["llm_category"] = None
    df["llm_raw_response"] = None
    df["llm_failed"] = False

    mask = df["category"] == "Uncategorised"
    to_classify = df[mask]

    if to_classify.empty:
        return df

    batch_size = settings.llm_batch_size
    indices = to_classify.index.tolist()

    for start in range(0, len(indices), batch_size):
        batch_idx = indices[start:start + batch_size]
        batch = df.loc[batch_idx]

        prompt = _build_prompt(batch)
        raw, failed = call_llm(prompt)

        if failed:
            df.loc[batch_idx, "llm_failed"] = True
            df.loc[batch_idx, "llm_category"] = "Other"
            continue

        df.loc[batch_idx, "llm_raw_response"] = raw
        try:
            parsed = json.loads(raw)
            categories = parsed.get("categories", [])
            if len(categories) != len(batch_idx):
                raise ValueError("category count mismatch")
            for idx, cat in zip(batch_idx, categories):
                df.at[idx, "llm_category"] = cat if cat in VALID_CATEGORIES else "Other"
        except (json.JSONDecodeError, ValueError, AttributeError) as exc:
            logger.warning("Failed to parse LLM classification response: %s", exc)
            df.loc[batch_idx, "llm_failed"] = True
            df.loc[batch_idx, "llm_category"] = "Other"

    # Promote llm_category into the working category column where it was set.
    classified_mask = df["llm_category"].notna()
    df.loc[classified_mask, "category"] = df.loc[classified_mask, "llm_category"]

    return df
