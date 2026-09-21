import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.graph import get_pipeline
from ml.config import RANDOM_STATE, RAW_CSV_PATH
from ml.data_prep import RAW_DTYPES, rename_to_lending_schema

FRAUD_SAMPLE_SIZE = 45
NORMAL_SAMPLE_SIZE = 65


def load_seed_rows() -> pd.DataFrame:
    raw = pd.read_csv(RAW_CSV_PATH, dtype=RAW_DTYPES)
    fraud = raw[raw["isFraud"] == 1].sample(
        n=min(FRAUD_SAMPLE_SIZE, (raw["isFraud"] == 1).sum()), random_state=RANDOM_STATE
    )
    normal = raw[raw["isFraud"] == 0].sample(n=NORMAL_SAMPLE_SIZE, random_state=RANDOM_STATE)
    combined = pd.concat([fraud, normal]).sample(frac=1, random_state=RANDOM_STATE)
    lending = rename_to_lending_schema(combined)
    return lending[lending["event_type"].notna()]


def to_record(row: pd.Series) -> dict:
    return {
        "event_type": row["event_type"],
        "step": int(row["step"]),
        "amount": float(row["amount"]),
        "origin_account": f"SEED_{row['origin_account']}",
        "dest_account": f"SEED_{row['dest_account']}" if pd.notna(row["dest_account"]) else None,
        "origin_balance_before": float(row["origin_balance_before"]),
        "origin_balance_after": float(row["origin_balance_after"]),
        "dest_balance_before": float(row["dest_balance_before"]),
        "dest_balance_after": float(row["dest_balance_after"]),
        "is_fraud_label": bool(row["is_fraud_label"]),
    }


def main() -> None:
    rows = load_seed_rows()
    pipeline = get_pipeline()
    total = len(rows)
    counts = {"allow": 0, "escalate": 0, "block": 0}

    for i, (_, row) in enumerate(rows.iterrows(), start=1):
        record = to_record(row)
        started = time.monotonic()
        try:
            result = pipeline.invoke({"record": record, "retry_count": 0})
            counts[result["decision"]] += 1
            print(
                f"[{i}/{total}] {record['event_type']} amount={record['amount']:.2f} "
                f"label={record['is_fraud_label']} -> {result['decision']} "
                f"risk={result['risk_score']:.3f} archetype={result['archetype']} "
                f"({time.monotonic() - started:.1f}s)"
            )
        except Exception as exc:
            print(f"[{i}/{total}] FAILED: {exc}")

    print(f"done. decisions: {counts}")


if __name__ == "__main__":
    main()
