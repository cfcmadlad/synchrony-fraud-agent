import json

import joblib
import numpy as np
import pandas as pd
import pytest

from ml.features import FEATURE_COLUMNS, build_features
from ml.train import train_anomaly_detector, train_supervised


def make_synthetic_dataset(n=400, seed=7):
    rng = np.random.default_rng(seed)
    event_types = rng.choice(
        ["loan_disbursement", "installment_repayment", "fee_charge", "account_funding"],
        size=n,
    )
    amount = rng.exponential(500, size=n).round(2)
    origin_before = rng.exponential(2000, size=n).round(2)
    origin_after = np.maximum(origin_before - amount, 0).round(2)
    dest_before = rng.exponential(3000, size=n).round(2)
    dest_after = (dest_before + amount).round(2)

    is_fraud = np.zeros(n, dtype=bool)
    eligible = np.where(event_types == "loan_disbursement")[0]
    fraud_idx = rng.choice(eligible, size=max(1, len(eligible) // 10), replace=False)
    is_fraud[fraud_idx] = True
    origin_after[fraud_idx] = 0.0

    return pd.DataFrame(
        {
            "step": rng.integers(1, 743, size=n),
            "event_type": event_types,
            "amount": amount,
            "origin_account": [f"C{i}" for i in range(n)],
            "origin_balance_before": origin_before,
            "origin_balance_after": origin_after,
            "dest_account": [f"M{i}" for i in range(n)],
            "dest_balance_before": dest_before,
            "dest_balance_after": dest_after,
            "is_fraud_label": is_fraud,
        }
    )


@pytest.fixture
def trained_risk_model(tmp_path, monkeypatch):
    import ml.scoring as scoring_module

    df = make_synthetic_dataset()
    X = build_features(df)
    y = df["is_fraud_label"].astype(int)

    supervised_model = train_supervised(X, y)
    anomaly_model = train_anomaly_detector(X[y == 0])

    legit_raw_scores = -anomaly_model.score_samples(X[y == 0])
    anomaly_low = float(np.percentile(legit_raw_scores, 1))
    anomaly_high = float(np.percentile(legit_raw_scores, 99))

    xgb_path = tmp_path / "xgb_model.json"
    isoforest_path = tmp_path / "isolation_forest.joblib"
    config_path = tmp_path / "scoring_config.json"

    supervised_model.save_model(xgb_path)
    joblib.dump(anomaly_model, isoforest_path)

    config_path.write_text(
        json.dumps(
            {
                "feature_columns": FEATURE_COLUMNS,
                "anomaly_low": anomaly_low,
                "anomaly_high": anomaly_high,
                "fusion_alpha": 0.7,
            }
        )
    )

    monkeypatch.setattr(scoring_module, "XGB_MODEL_PATH", xgb_path)
    monkeypatch.setattr(scoring_module, "ISOLATION_FOREST_PATH", isoforest_path)
    monkeypatch.setattr(scoring_module, "SCORING_CONFIG_PATH", config_path)

    scoring_module.get_risk_model.cache_clear()
    yield scoring_module.get_risk_model()
    scoring_module.get_risk_model.cache_clear()
