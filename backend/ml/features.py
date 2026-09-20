import pandas as pd

from ml.config import EVENT_TYPES

FEATURE_COLUMNS = [
    "amount",
    "origin_balance_before",
    "origin_balance_after",
    "dest_balance_before",
    "dest_balance_after",
    "origin_balance_delta",
    "dest_balance_delta",
    "origin_balance_error",
    "dest_balance_error",
    "amount_to_origin_balance_ratio",
    "origin_balance_after_zero",
    "hour_of_day",
] + [f"event_type_{event_type}" for event_type in EVENT_TYPES]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    frame = pd.DataFrame(index=df.index)

    amount = df["amount"].astype(float)
    origin_before = df["origin_balance_before"].fillna(0.0).astype(float)
    origin_after = df["origin_balance_after"].fillna(0.0).astype(float)
    dest_before = df["dest_balance_before"].fillna(0.0).astype(float)
    dest_after = df["dest_balance_after"].fillna(0.0).astype(float)
    step = df["step"].fillna(0).astype(int)

    frame["amount"] = amount
    frame["origin_balance_before"] = origin_before
    frame["origin_balance_after"] = origin_after
    frame["dest_balance_before"] = dest_before
    frame["dest_balance_after"] = dest_after
    frame["origin_balance_delta"] = origin_after - origin_before
    frame["dest_balance_delta"] = dest_after - dest_before
    frame["origin_balance_error"] = origin_before - amount - origin_after
    frame["dest_balance_error"] = dest_before + amount - dest_after
    frame["amount_to_origin_balance_ratio"] = amount / (origin_before + 1.0)
    frame["origin_balance_after_zero"] = (origin_after == 0.0).astype(int)
    frame["hour_of_day"] = step % 24

    for event_type in EVENT_TYPES:
        frame[f"event_type_{event_type}"] = (df["event_type"] == event_type).astype(int)

    return frame[FEATURE_COLUMNS]


def build_features_single(record: dict) -> pd.DataFrame:
    return build_features(pd.DataFrame([record]))
