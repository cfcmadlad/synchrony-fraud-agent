import pandas as pd

from app.db import get_service_client
from ml.case_text import build_case_text
from ml.config import HISTORICAL_SAMPLE_SIZE, PROCESSED_PATH, RANDOM_STATE
from ml.embedder import get_embedder
from ml.scoring import get_risk_model
from ml.vectors import vector_literal

FRAUD_QUOTA = HISTORICAL_SAMPLE_SIZE // 4
INSERT_BATCH_SIZE = 500


def build_case_sample(df: pd.DataFrame) -> pd.DataFrame:
    fraud_rows = df[df["is_fraud_label"]]
    legit_rows = df[~df["is_fraud_label"]]

    fraud_sample = fraud_rows.sample(
        n=min(len(fraud_rows), FRAUD_QUOTA), random_state=RANDOM_STATE
    )
    legit_sample = legit_rows.sample(
        n=min(len(legit_rows), HISTORICAL_SAMPLE_SIZE - len(fraud_sample)),
        random_state=RANDOM_STATE,
    )
    return pd.concat([fraud_sample, legit_sample]).sample(frac=1, random_state=RANDOM_STATE)


def run() -> None:
    if not PROCESSED_PATH.exists():
        raise FileNotFoundError(f"Run ml.data_prep first — {PROCESSED_PATH} does not exist.")

    df = pd.read_csv(PROCESSED_PATH)
    df["is_fraud_label"] = df["is_fraud_label"].astype(bool)
    sample = build_case_sample(df)

    risk_model = get_risk_model()
    embedder = get_embedder()
    client = get_service_client()

    records = sample.to_dict(orient="records")
    total_inserted = 0

    for start in range(0, len(records), INSERT_BATCH_SIZE):
        batch = records[start : start + INSERT_BATCH_SIZE]

        score_results = [risk_model.score(record) for record in batch]
        summaries = [
            build_case_text(record, score_result, outcome=record["is_fraud_label"])
            for record, score_result in zip(batch, score_results, strict=True)
        ]
        embeddings = embedder.encode(summaries, show_progress_bar=False)

        transaction_rows = [
            {
                "event_type": record["event_type"],
                "step": int(record["step"]),
                "amount": float(record["amount"]),
                "origin_account": record["origin_account"],
                "dest_account": record["dest_account"] if pd.notna(record["dest_account"]) else None,
                "origin_balance_before": float(record["origin_balance_before"]),
                "origin_balance_after": float(record["origin_balance_after"]),
                "dest_balance_before": float(record["dest_balance_before"]),
                "dest_balance_after": float(record["dest_balance_after"]),
                "is_fraud_label": bool(record["is_fraud_label"]),
                "risk_score": score_result["risk_score"],
            }
            for record, score_result in zip(batch, score_results, strict=True)
        ]

        inserted = client.table("transactions").insert(transaction_rows).execute().data

        embedding_rows = [
            {
                "transaction_id": row["id"],
                "summary_text": summary,
                "embedding": vector_literal(embedding.tolist()),
            }
            for row, summary, embedding in zip(inserted, summaries, embeddings, strict=True)
        ]
        client.table("case_embeddings").insert(embedding_rows).execute()

        total_inserted += len(inserted)
        print(f"inserted {total_inserted}/{len(records)} historical cases")

    print(f"done: {total_inserted} historical cases embedded and loaded")


if __name__ == "__main__":
    run()
