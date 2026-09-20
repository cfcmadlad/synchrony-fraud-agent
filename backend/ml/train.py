import json

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from ml.config import (
    ARTIFACTS_DIR,
    FUSION_ALPHA,
    ISOLATION_FOREST_PATH,
    METRICS_PATH,
    PROCESSED_PATH,
    RANDOM_STATE,
    SCORING_CONFIG_PATH,
    XGB_MODEL_PATH,
)
from ml.features import FEATURE_COLUMNS, build_features


def load_dataset() -> tuple[pd.DataFrame, pd.Series]:
    if not PROCESSED_PATH.exists():
        raise FileNotFoundError(f"Run ml.data_prep first — {PROCESSED_PATH} does not exist.")
    df = pd.read_csv(PROCESSED_PATH)
    X = build_features(df)
    y = df["is_fraud_label"].astype(int)
    return X, y


def train_supervised(X_train: pd.DataFrame, y_train: pd.Series) -> xgb.XGBClassifier:
    negatives = int((y_train == 0).sum())
    positives = int((y_train == 1).sum())
    scale_pos_weight = negatives / max(positives, 1)

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        random_state=RANDOM_STATE,
        tree_method="hist",
    )
    model.fit(X_train, y_train)
    return model


def train_anomaly_detector(X_train_legit: pd.DataFrame) -> IsolationForest:
    model = IsolationForest(
        n_estimators=200,
        contamination="auto",
        random_state=RANDOM_STATE,
    )
    model.fit(X_train_legit)
    return model


def normalize_anomaly_scores(raw_scores: np.ndarray, low: float, high: float) -> np.ndarray:
    span = max(high - low, 1e-9)
    return np.clip((raw_scores - low) / span, 0.0, 1.0)


def evaluate(y_true: pd.Series, scores: np.ndarray, threshold: float) -> dict:
    preds = (scores >= threshold).astype(int)
    return {
        "precision": float(precision_score(y_true, preds, zero_division=0)),
        "recall": float(recall_score(y_true, preds, zero_division=0)),
        "f1": float(f1_score(y_true, preds, zero_division=0)),
        "auc_pr": float(average_precision_score(y_true, scores)),
    }


def run() -> dict:
    X, y = load_dataset()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
    )

    supervised_model = train_supervised(X_train, y_train)
    supervised_test_scores = supervised_model.predict_proba(X_test)[:, 1]

    X_train_legit = X_train[y_train == 0]
    anomaly_model = train_anomaly_detector(X_train_legit)

    legit_raw_scores = -anomaly_model.score_samples(X_train_legit)
    anomaly_low = float(np.percentile(legit_raw_scores, 1))
    anomaly_high = float(np.percentile(legit_raw_scores, 99))

    test_raw_scores = -anomaly_model.score_samples(X_test)
    anomaly_test_scores = normalize_anomaly_scores(test_raw_scores, anomaly_low, anomaly_high)

    fused_scores = FUSION_ALPHA * supervised_test_scores + (1 - FUSION_ALPHA) * anomaly_test_scores

    metrics = {
        "dataset_size": len(X),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "fraud_rate": float(y.mean()),
        "supervised_only": evaluate(y_test, supervised_test_scores, threshold=0.5),
        "fused": evaluate(y_test, fused_scores, threshold=0.5),
        "fusion_alpha": FUSION_ALPHA,
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    supervised_model.save_model(XGB_MODEL_PATH)
    joblib.dump(anomaly_model, ISOLATION_FOREST_PATH)

    scoring_config = {
        "feature_columns": FEATURE_COLUMNS,
        "anomaly_low": anomaly_low,
        "anomaly_high": anomaly_high,
        "fusion_alpha": FUSION_ALPHA,
    }
    SCORING_CONFIG_PATH.write_text(json.dumps(scoring_config, indent=2))
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))

    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    run()
