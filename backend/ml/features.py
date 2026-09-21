import pandas as pd

from ml.config import EVENT_TYPES

FEATURE_COLUMNS = [
    "amount",
    "origin_balance_before",
    "origin_balance_after",
    "dest_balance_before",
    "dest_balance_after",
    "dest_balance_delta",
    "dest_balance_error",
    "hour_of_day",
] + [f"event_type_{event_type}" for event_type in EVENT_TYPES]

NEAR_DETERMINISTIC_COLUMNS = [
    "origin_balance_delta",
    "origin_balance_error",
    "amount_to_origin_balance_ratio",
    "origin_balance_after_zero",
]


def build_features(df: pd.DataFrame, include_near_deterministic: bool = False) -> pd.DataFrame:
    frame = pd.DataFrame(index=df.index)

    amount = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    origin_before = pd.to_numeric(df["origin_balance_before"], errors="coerce").fillna(0.0)
    origin_after = pd.to_numeric(df["origin_balance_after"], errors="coerce").fillna(0.0)
    dest_before = pd.to_numeric(df["dest_balance_before"], errors="coerce").fillna(0.0)
    dest_after = pd.to_numeric(df["dest_balance_after"], errors="coerce").fillna(0.0)
    step = pd.to_numeric(df["step"], errors="coerce").fillna(0).astype(int)

    frame["amount"] = amount
    frame["origin_balance_before"] = origin_before
    frame["origin_balance_after"] = origin_after
    frame["dest_balance_before"] = dest_before
    frame["dest_balance_after"] = dest_after
    frame["dest_balance_delta"] = dest_after - dest_before
    frame["dest_balance_error"] = dest_before + amount - dest_after
    frame["hour_of_day"] = step % 24

    for event_type in EVENT_TYPES:
        frame[f"event_type_{event_type}"] = (df["event_type"] == event_type).astype(int)

    columns = FEATURE_COLUMNS
    if include_near_deterministic:
        frame["origin_balance_delta"] = origin_after - origin_before
        frame["origin_balance_error"] = origin_before - amount - origin_after
        frame["amount_to_origin_balance_ratio"] = amount / (origin_before + 1.0)
        frame["origin_balance_after_zero"] = (origin_after == 0.0).astype(int)
        columns = FEATURE_COLUMNS + NEAR_DETERMINISTIC_COLUMNS

    return frame[columns]


def build_features_single(record: dict, include_near_deterministic: bool = False) -> pd.DataFrame:
    return build_features(pd.DataFrame([record]), include_near_deterministic=include_near_deterministic)
