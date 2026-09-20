import pandas as pd
from sklearn.model_selection import train_test_split

from ml.config import (
    EVENT_TYPE_MAP,
    PROCESSED_PATH,
    RANDOM_STATE,
    RAW_CSV_PATH,
    SAMPLE_CSV_PATH,
    SUBSAMPLE_SIZE,
)

RAW_DTYPES = {
    "step": "int32",
    "type": "category",
    "amount": "float64",
    "nameOrig": "string",
    "oldbalanceOrg": "float64",
    "newbalanceOrig": "float64",
    "nameDest": "string",
    "oldbalanceDest": "float64",
    "newbalanceDest": "float64",
    "isFraud": "int8",
    "isFlaggedFraud": "int8",
}

RENAME_MAP = {
    "nameOrig": "origin_account",
    "oldbalanceOrg": "origin_balance_before",
    "newbalanceOrig": "origin_balance_after",
    "nameDest": "dest_account",
    "oldbalanceDest": "dest_balance_before",
    "newbalanceDest": "dest_balance_after",
    "isFraud": "is_fraud_label",
}


def load_raw() -> pd.DataFrame:
    if not RAW_CSV_PATH.exists():
        raise FileNotFoundError(
            f"Expected the PaySim CSV at {RAW_CSV_PATH}. Download it from Kaggle "
            "(ealaxi/paysim1) and place it there before running this script."
        )
    return pd.read_csv(RAW_CSV_PATH, dtype=RAW_DTYPES)


def subsample_stratified(df: pd.DataFrame, size: int) -> pd.DataFrame:
    if len(df) <= size:
        return df
    sampled, _ = train_test_split(
        df,
        train_size=size,
        stratify=df["isFraud"],
        random_state=RANDOM_STATE,
    )
    return sampled


def rename_to_lending_schema(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["type"] = df["type"].map(EVENT_TYPE_MAP)
    df = df.drop(columns=["isFlaggedFraud"])
    df = df.rename(columns=RENAME_MAP)
    df = df.rename(columns={"type": "event_type"})
    df["is_fraud_label"] = df["is_fraud_label"].astype(bool)
    return df


def run() -> pd.DataFrame:
    raw = load_raw()
    subsampled = subsample_stratified(raw, SUBSAMPLE_SIZE)
    lending = rename_to_lending_schema(subsampled)

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    lending.to_csv(PROCESSED_PATH, index=False)

    SAMPLE_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    lending.sample(n=min(500, len(lending)), random_state=RANDOM_STATE).to_csv(
        SAMPLE_CSV_PATH, index=False
    )

    fraud_rate = lending["is_fraud_label"].mean()
    print(f"rows: {len(lending)}")
    print(f"fraud_rate: {fraud_rate:.6f}")
    print(f"event_type counts:\n{lending['event_type'].value_counts()}")
    print(f"saved processed dataset to {PROCESSED_PATH}")
    print(f"saved sample dataset to {SAMPLE_CSV_PATH}")
    return lending


if __name__ == "__main__":
    run()
