from app.db import get_service_client


def build_log_entry(transaction_id: str, node_name: str, input_snapshot: dict, output_snapshot: dict) -> dict:
    return {
        "transaction_id": transaction_id,
        "node_name": node_name,
        "input_snapshot": input_snapshot,
        "output_snapshot": output_snapshot,
    }


def flush_decision_log(entries: list[dict]) -> None:
    if not entries:
        return
    client = get_service_client()
    client.table("agent_decision_log").insert(entries).execute()
