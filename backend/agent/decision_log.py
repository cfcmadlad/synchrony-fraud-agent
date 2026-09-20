from app.db import get_service_client


def log_step(transaction_id: str, node_name: str, input_snapshot: dict, output_snapshot: dict) -> None:
    client = get_service_client()
    client.table("agent_decision_log").insert(
        {
            "transaction_id": transaction_id,
            "node_name": node_name,
            "input_snapshot": input_snapshot,
            "output_snapshot": output_snapshot,
        }
    ).execute()
