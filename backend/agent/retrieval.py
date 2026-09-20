from app.db import get_service_client
from ml.config import SIMILAR_CASES_LIMIT
from ml.embedder import get_embedder
from ml.vectors import vector_literal


def retrieve_similar_cases(query_text: str, exclude_transaction_id: str | None = None) -> list[dict]:
    embedder = get_embedder()
    client = get_service_client()

    query_embedding = embedder.encode([query_text], show_progress_bar=False)[0]
    result = client.rpc(
        "match_case_embeddings",
        {
            "query_embedding": vector_literal(query_embedding.tolist()),
            "match_count": SIMILAR_CASES_LIMIT + 1,
        },
    ).execute()

    matches = [
        row
        for row in result.data
        if row["transaction_id"] != exclude_transaction_id
    ][:SIMILAR_CASES_LIMIT]

    return matches
