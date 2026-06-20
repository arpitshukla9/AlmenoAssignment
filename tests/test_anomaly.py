import pandas as pd

from app.pipeline.anomaly import detect_anomalies


def test_statistical_outlier_flagged():
    df = pd.DataFrame({
        "account_id": ["ACC1", "ACC1", "ACC1", "ACC1"],
        "amount": [100.0, 110.0, 90.0, 1000.0],
        "currency": ["INR"] * 4,
        "merchant": ["A", "B", "C", "D"],
    })
    out = detect_anomalies(df)
    assert out.loc[3, "is_anomaly"] is True or out.loc[3, "is_anomaly"] == True
    assert "median" in out.loc[3, "anomaly_reason"]
    assert out.loc[0, "is_anomaly"] == False


def test_domestic_merchant_usd_mismatch_flagged():
    df = pd.DataFrame({
        "account_id": ["ACC1", "ACC1"],
        "amount": [100.0, 100.0],
        "currency": ["USD", "INR"],
        "merchant": ["Swiggy", "Swiggy"],
    })
    out = detect_anomalies(df)
    assert out.loc[0, "is_anomaly"] == True
    assert "domestic-only" in out.loc[0, "anomaly_reason"]
    assert out.loc[1, "is_anomaly"] == False


def test_non_domestic_usd_not_flagged():
    df = pd.DataFrame({
        "account_id": ["ACC1"],
        "amount": [100.0],
        "currency": ["USD"],
        "merchant": ["Netflix"],
    })
    out = detect_anomalies(df)
    assert out.loc[0, "is_anomaly"] == False
