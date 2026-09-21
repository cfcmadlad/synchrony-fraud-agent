import json

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ml.config import (
    ARTIFACTS_DIR,
    DECISION_THRESHOLD_BLOCK,
    DECISION_THRESHOLD_ESCALATE,
    EVENT_TYPES,
    FUSION_ALPHA_LABELED,
    FUSION_ALPHA_UNLABELED,
    ISOLATION_FOREST_PATH,
    METRICS_PATH,
    PROCESSED_PATH,
    RANDOM_STATE,
    SCORING_CONFIG_PATH,
    XGB_MODEL_PATH,
    fusion_alpha_for_event_type,
)
from ml.features import FEATURE_COLUMNS, NEAR_DETERMINISTIC_COLUMNS, build_features


def load_dataset() -> pd.DataFrame:
    if not PROCESSED_PATH.exists():
        raise FileNotFoundError(f"Run ml.data_prep first — {PROCESSED_PATH} does not exist.")
    return pd.read_csv(PROCESSED_PATH)


def temporal_split(df: pd.DataFrame, train_fraction: float = 0.8) -> tuple[pd.DataFrame, pd.DataFrame]:
    split_step = df["step"].quantile(train_fraction)
    train_df = df[df["step"] <= split_step]
    test_df = df[df["step"] > split_step]
    return train_df, test_df


def temporal_folds(df: pd.DataFrame, n_folds: int = 5) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    quantiles = np.linspace(0, 1, n_folds + 2)[1:]
    boundaries = df["step"].quantile(quantiles).tolist()
    folds = []
    for i in range(n_folds):
        train_cutoff, test_cutoff = boundaries[i], boundaries[i + 1]
        train_df = df[df["step"] <= train_cutoff]
        test_df = df[(df["step"] > train_cutoff) & (df["step"] <= test_cutoff)]
        folds.append((train_df, test_df))
    return folds


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


def train_logistic_baseline(X_train: pd.DataFrame, y_train: pd.Series):
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE),
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


def train_anomaly_detectors_by_event_type(
    train_df: pd.DataFrame, X_train: pd.DataFrame, y_train: pd.Series
) -> dict[str, IsolationForest]:
    legit_mask = y_train == 0
    detectors = {}
    for event_type in EVENT_TYPES:
        type_mask = legit_mask & (train_df["event_type"] == event_type).values
        detectors[event_type] = train_anomaly_detector(X_train[type_mask])
    return detectors


def anomaly_bounds_by_event_type(
    detectors: dict[str, IsolationForest], train_df: pd.DataFrame, X_train: pd.DataFrame, y_train: pd.Series
) -> dict[str, dict[str, float]]:
    legit_mask = y_train == 0
    bounds = {}
    for event_type, model in detectors.items():
        type_mask = legit_mask & (train_df["event_type"] == event_type).values
        raw_scores = -model.score_samples(X_train[type_mask])
        bounds[event_type] = {
            "low": float(np.percentile(raw_scores, 1)),
            "high": float(np.percentile(raw_scores, 99)),
        }
    return bounds


def score_anomaly_by_event_type(
    detectors: dict[str, IsolationForest],
    bounds: dict[str, dict[str, float]],
    df: pd.DataFrame,
    X: pd.DataFrame,
) -> np.ndarray:
    scores = np.zeros(len(X))
    for event_type, model in detectors.items():
        type_mask = (df["event_type"] == event_type).values
        if not type_mask.any():
            continue
        raw_scores = -model.score_samples(X[type_mask])
        scores[type_mask] = normalize_anomaly_scores(
            raw_scores, bounds[event_type]["low"], bounds[event_type]["high"]
        )
    return scores


def normalize_anomaly_scores(raw_scores: np.ndarray, low: float, high: float) -> np.ndarray:
    span = max(high - low, 1e-9)
    return np.clip((raw_scores - low) / span, 0.0, 1.0)


def fuse_scores(df: pd.DataFrame, supervised_scores: np.ndarray, anomaly_scores: np.ndarray) -> np.ndarray:
    alphas = df["event_type"].map(fusion_alpha_for_event_type).values
    return alphas * supervised_scores + (1 - alphas) * anomaly_scores


def evaluate(y_true: pd.Series, scores: np.ndarray, threshold: float) -> dict:
    preds = (scores >= threshold).astype(int)
    return {
        "precision": float(precision_score(y_true, preds, zero_division=0)),
        "recall": float(recall_score(y_true, preds, zero_division=0)),
        "f1": float(f1_score(y_true, preds, zero_division=0)),
        "auc_pr": float(average_precision_score(y_true, scores)),
    }


def cross_validate_supervised(df: pd.DataFrame, n_folds: int = 5) -> list[dict]:
    fold_metrics = []
    for train_df, test_df in temporal_folds(df, n_folds):
        y_train = train_df["is_fraud_label"].astype(int)
        y_test = test_df["is_fraud_label"].astype(int)
        if y_train.sum() == 0 or y_test.sum() == 0:
            continue

        X_train = build_features(train_df)
        X_test = build_features(test_df)
        model = train_supervised(X_train, y_train)
        scores = model.predict_proba(X_test)[:, 1]
        fold_metrics.append(evaluate(y_test, scores, threshold=0.5))
    return fold_metrics


def summarize_folds(fold_metrics: list[dict]) -> dict:
    summary = {}
    for key in ("precision", "recall", "f1", "auc_pr"):
        values = [fold[key] for fold in fold_metrics]
        summary[key] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "per_fold": values,
        }
    return summary


def evaluate_reference_with_full_signal(
    train_df: pd.DataFrame, y_train: pd.Series, test_df: pd.DataFrame, y_test: pd.Series
) -> dict:
    X_train_full = build_features(train_df, include_near_deterministic=True)
    X_test_full = build_features(test_df, include_near_deterministic=True)
    model = train_supervised(X_train_full, y_train)
    scores = model.predict_proba(X_test_full)[:, 1]
    return evaluate(y_test, scores, threshold=0.5)


def run() -> dict:
    df = load_dataset()
    train_df, test_df = temporal_split(df)

    X_train = build_features(train_df)
    y_train = train_df["is_fraud_label"].astype(int)
    X_test = build_features(test_df)
    y_test = test_df["is_fraud_label"].astype(int)

    supervised_model = train_supervised(X_train, y_train)
    supervised_test_scores = supervised_model.predict_proba(X_test)[:, 1]

    logistic_model = train_logistic_baseline(X_train, y_train)
    logistic_test_scores = logistic_model.predict_proba(X_test)[:, 1]

    anomaly_detectors = train_anomaly_detectors_by_event_type(train_df, X_train, y_train)
    anomaly_bounds = anomaly_bounds_by_event_type(anomaly_detectors, train_df, X_train, y_train)
    anomaly_test_scores = score_anomaly_by_event_type(anomaly_detectors, anomaly_bounds, test_df, X_test)

    fused_scores = fuse_scores(test_df, supervised_test_scores, anomaly_test_scores)

    cv_folds = cross_validate_supervised(df)

    metrics = {
        "dataset_size": len(df),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "split_method": "temporal (train on earlier steps, test on later steps)",
        "fraud_rate": float(df["is_fraud_label"].astype(int).mean()),
        "feature_columns": FEATURE_COLUMNS,
        "supervised_only": evaluate(y_test, supervised_test_scores, threshold=0.5),
        "fused_at_standard_threshold_0.5": evaluate(y_test, fused_scores, threshold=0.5),
        "fused_at_deployed_escalate_threshold": evaluate(
            y_test, fused_scores, threshold=DECISION_THRESHOLD_ESCALATE
        ),
        "fused_at_deployed_block_threshold": evaluate(
            y_test, fused_scores, threshold=DECISION_THRESHOLD_BLOCK
        ),
        "fusion_alpha_labeled_event_types": FUSION_ALPHA_LABELED,
        "fusion_alpha_unlabeled_event_types": FUSION_ALPHA_UNLABELED,
        "cross_validation_5_fold_temporal": summarize_folds(cv_folds),
        "algorithm_comparison": {
            "xgboost": evaluate(y_test, supervised_test_scores, threshold=0.5),
            "logistic_regression_baseline": evaluate(y_test, logistic_test_scores, threshold=0.5),
        },
        "anomaly_detector_standalone": {
            "note": (
                "AUC-PR only computable for loan_disbursement, since PaySim never labels "
                "fraud on the other three event types — this detector's real job is "
                "catching anomalies there, where no ground truth exists to score against."
            ),
            "auc_pr_overall": float(average_precision_score(y_test, anomaly_test_scores)),
            "auc_pr_loan_disbursement_only": float(
                average_precision_score(
                    y_test[test_df["event_type"].values == "loan_disbursement"],
                    anomaly_test_scores[test_df["event_type"].values == "loan_disbursement"],
                )
            ),
        },
        "reference_with_near_deterministic_features_included": {
            "included_features": NEAR_DETERMINISTIC_COLUMNS,
            "metrics": evaluate_reference_with_full_signal(train_df, y_train, test_df, y_test),
        },
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    supervised_model.save_model(XGB_MODEL_PATH)
    joblib.dump(anomaly_detectors, ISOLATION_FOREST_PATH)

    scoring_config = {
        "feature_columns": FEATURE_COLUMNS,
        "anomaly_bounds": anomaly_bounds,
    }
    SCORING_CONFIG_PATH.write_text(json.dumps(scoring_config, indent=2))
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))

    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    run()
