import json
from functools import lru_cache

import joblib
import numpy as np
import xgboost as xgb

from ml.archetypes import tag_archetype
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

        scores = {
            "supervised_score": supervised_score,
            "anomaly_score": anomaly_score,
            "risk_score": risk_score,
        }
        scores.update(tag_archetype(record, scores))
        return scores

    def top_features(self, record: dict, k: int = 4) -> list[dict]:
        features = build_features_single(record)[self.feature_columns]
        dmatrix = xgb.DMatrix(features)
        booster = self.supervised_model.get_booster()
        contributions = booster.predict(dmatrix, pred_contribs=True)[0]
        pairs = list(zip(self.feature_columns, contributions[:-1], strict=True))
        pairs.sort(key=lambda pair: abs(pair[1]), reverse=True)
        return [{"feature": name, "contribution": float(value)} for name, value in pairs[:k]]


@lru_cache
def get_risk_model() -> RiskModel:
    return RiskModel()
