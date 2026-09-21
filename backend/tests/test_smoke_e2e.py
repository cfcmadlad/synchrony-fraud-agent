import pytest

from app.config import get_settings
from ml.config import ISOLATION_FOREST_PATH, SCORING_CONFIG_PATH, XGB_MODEL_PATH


def _integration_ready() -> bool:
    settings = get_settings()
    if not settings.supabase_url or settings.supabase_service_role_key in ("", "replace-me"):
        return False
    return XGB_MODEL_PATH.exists() and ISOLATION_FOREST_PATH.exists() and SCORING_CONFIG_PATH.exists()


@pytest.mark.integration
@pytest.mark.skipif(
    not _integration_ready(),
    reason="requires live Supabase credentials and trained model artifacts",
)
def test_known_fraud_sample_is_blocked_end_to_end():
    from agent.graph import get_pipeline
    from app.db import get_service_client

    known_fraud_sample = {
        "event_type": "loan_disbursement",
        "step": 5,
        "amount": 9500.0,
        "origin_account": "SMOKE_TEST_FRAUD_001",
        "dest_account": "SMOKE_TEST_MERCHANT_001",
        "origin_balance_before": 9500.0,
        "origin_balance_after": 0.0,
        "dest_balance_before": 500.0,
        "dest_balance_after": 10000.0,
    }

    pipeline = get_pipeline()
    result = pipeline.invoke({"record": known_fraud_sample, "retry_count": 0})

    try:
        assert result["risk_score"] > 0.5
        assert result["decision"] in ("block", "escalate")
        assert result["archetype"] == "synthetic_identity_origination"
        assert result["explanation"]
        assert result["guardrail_passed"] is True

        client = get_service_client()
        log_rows = (
            client.table("agent_decision_log")
            .select("node_name")
            .eq("transaction_id", result["transaction_id"])
            .order("created_at")
            .execute()
            .data
        )
        node_sequence = [row["node_name"] for row in log_rows]
        assert node_sequence == ["ingest", "detect", "retrieve", "explain", "guardrail", "decide"]

        transaction = (
            client.table("transactions")
            .select("status")
            .eq("id", result["transaction_id"])
            .execute()
            .data[0]
        )
        assert transaction["status"] in ("blocked", "escalated")
    finally:
        client = get_service_client()
        client.table("transactions").delete().eq(
            "origin_account", "SMOKE_TEST_FRAUD_001"
        ).execute()
