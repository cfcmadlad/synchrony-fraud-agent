import pandas as pd

from ml.features import FEATURE_COLUMNS, NEAR_DETERMINISTIC_COLUMNS, build_features
from ml.train import (
    cross_validate_supervised,
    evaluate_reference_with_full_signal,
    summarize_folds,
    temporal_folds,
    temporal_split,
)


def make_df(n=100):
    return pd.DataFrame(
        {
            "step": range(1, n + 1),
            "event_type": ["loan_disbursement"] * n,
            "amount": [100.0] * n,
            "origin_account": [f"C{i}" for i in range(n)],
            "origin_balance_before": [1000.0] * n,
            "origin_balance_after": [900.0] * n,
            "dest_account": [f"M{i}" for i in range(n)],
            "dest_balance_before": [0.0] * n,
            "dest_balance_after": [100.0] * n,
            "is_fraud_label": [i % 10 == 0 for i in range(n)],
        }
    )


def test_temporal_split_respects_chronological_order():
    df = make_df()
    train_df, test_df = temporal_split(df, train_fraction=0.8)
    assert train_df["step"].max() <= test_df["step"].min()
    assert len(train_df) + len(test_df) == len(df)


def test_temporal_split_produces_nonempty_partitions():
    df = make_df()
    train_df, test_df = temporal_split(df, train_fraction=0.8)
    assert len(train_df) > 0
    assert len(test_df) > 0


def test_temporal_folds_are_chronologically_ordered():
    df = make_df(n=600)
    folds = temporal_folds(df, n_folds=5)
    assert len(folds) == 5
    for train_df, test_df in folds:
        if len(train_df) and len(test_df):
            assert train_df["step"].max() <= test_df["step"].min()


def test_summarize_folds_computes_mean_and_std():
    fold_metrics = [
        {"precision": 0.8, "recall": 0.7, "f1": 0.75, "auc_pr": 0.9},
        {"precision": 0.9, "recall": 0.8, "f1": 0.85, "auc_pr": 0.95},
    ]
    summary = summarize_folds(fold_metrics)
    assert abs(summary["precision"]["mean"] - 0.85) < 1e-9
    assert len(summary["precision"]["per_fold"]) == 2


def test_cross_validate_supervised_returns_valid_metrics():
    df = make_df(n=300)
    fold_metrics = cross_validate_supervised(df, n_folds=3)
    for fold in fold_metrics:
        assert set(fold) == {"precision", "recall", "f1", "auc_pr"}


def test_evaluate_reference_with_full_signal_uses_near_deterministic_columns():
    df = make_df(n=200)
    train_df, test_df = temporal_split(df)
    y_train = train_df["is_fraud_label"].astype(int)
    y_test = test_df["is_fraud_label"].astype(int)

    result = evaluate_reference_with_full_signal(train_df, y_train, test_df, y_test)
    assert set(result) == {"precision", "recall", "f1", "auc_pr"}


def test_near_deterministic_columns_excluded_from_default_features():
    for column in NEAR_DETERMINISTIC_COLUMNS:
        assert column not in FEATURE_COLUMNS


def test_build_features_can_include_near_deterministic_columns():
    df = make_df(n=5)
    default_result = build_features(df)
    full_result = build_features(df, include_near_deterministic=True)
    assert not set(NEAR_DETERMINISTIC_COLUMNS).issubset(default_result.columns)
    assert set(NEAR_DETERMINISTIC_COLUMNS).issubset(full_result.columns)
