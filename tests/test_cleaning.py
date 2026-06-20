import pandas as pd

from app.pipeline.cleaning import clean_transactions


def test_date_normalisation_both_formats():
    df = pd.DataFrame({
        "txn_id": ["A", "B"],
        "date": ["12-01-2024", "2024/01/13"],
        "merchant": ["X", "Y"],
        "amount": ["100", "200"],
        "currency": ["INR", "USD"],
        "status": ["success", "SUCCESS"],
        "category": ["", "Food"],
        "account_id": ["ACC1", "ACC1"],
        "notes": ["", ""],
    })
    cleaned, _, _ = clean_transactions(df)
    assert cleaned.loc[0, "date"] == "2024-01-12"
    assert cleaned.loc[1, "date"] == "2024-01-13"


def test_amount_currency_symbol_stripped():
    df = pd.DataFrame({
        "txn_id": ["A"], "date": ["01-01-2024"], "merchant": ["X"],
        "amount": ["$45.50"], "currency": ["usd"], "status": ["success"],
        "category": [""], "account_id": ["ACC1"], "notes": [""],
    })
    cleaned, _, _ = clean_transactions(df)
    assert cleaned.loc[0, "amount"] == 45.50
    assert cleaned.loc[0, "currency"] == "USD"


def test_status_uppercased_and_missing_category_filled():
    df = pd.DataFrame({
        "txn_id": ["A"], "date": ["01-01-2024"], "merchant": ["X"],
        "amount": ["10"], "currency": ["inr"], "status": ["pending"],
        "category": [""], "account_id": ["ACC1"], "notes": [""],
    })
    cleaned, _, _ = clean_transactions(df)
    assert cleaned.loc[0, "status"] == "PENDING"
    assert cleaned.loc[0, "category"] == "Uncategorised"


def test_exact_duplicates_removed():
    row = {
        "txn_id": "A", "date": "12-01-2024", "merchant": "X", "amount": "100",
        "currency": "INR", "status": "SUCCESS", "category": "Food",
        "account_id": "ACC1", "notes": "",
    }
    df = pd.DataFrame([row, row, row])
    cleaned, raw, clean = clean_transactions(df)
    assert raw == 3
    assert clean == 1
