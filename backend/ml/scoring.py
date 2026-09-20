import json
from functools import lru_cache

import joblib
import numpy as np
import xgboost as xgb

from ml.config import ISOLATION_FOREST_PATH, SCORING_CONFIG_PATH, XGB_MODEL_PATH
from ml.features import build_features_single


class RiskModel:
    def __init__(self):
        self.supervised_model = xgb.XGBClassifier()
        self.supervised_model.load_model(XGB_MODEL_PATH)
        self.anomaly_model = joblib.load(ISOLATION_FOREST_PATH)
        config = json.loads(SCORING_CONFIG_PATH.read_text())
        self.feature_columns = config["feature_columns"]
        self.anomaly_low = config["anomaly_low"]
        self.anomaly_high = config["anomaly_high"]
        self.fusion_alpha = config["fusion_alpha"]

    def score(self, record: dict) -> dict:
        features = build_features_single(record)[self.feature_columns]

        supervised_score = float(self.supervised_model.predict_proba(features)[0, 1])

        raw_anomaly_score = float(-self.anomaly_model.score_samples(features)[0])
        span = max(self.anomaly_high - self.anomaly_low, 1e-9)
        anomaly_score = float(np.clip((raw_anomaly_score - self.anomaly_low) / span, 0.0, 1.0))

        risk_score = self.fusion_alpha * supervised_score + (1 - self.fusion_alpha) * anomaly_score

        return {
            "supervised_score": supervised_score,
            "anomaly_score": anomaly_score,
            "risk_score": risk_score,
        }


@lru_cache
def get_risk_model() -> RiskModel:
    return RiskModel()
