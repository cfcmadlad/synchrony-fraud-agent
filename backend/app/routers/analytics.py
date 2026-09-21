from fastapi import APIRouter, Depends, Query

from app.auth import require_analyst_or_admin
from app.db import get_service_client

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/fraud-flags")
def list_fraud_flags(
    limit: int = Query(default=500, ge=1, le=2000),
    user=Depends(require_analyst_or_admin),
) -> list[dict]:
    client = get_service_client()
    result = (
        client.table("fraud_flags")
        .select("risk_score,supervised_score,anomaly_score,decision,reason_codes,created_at,transactions(event_type)")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = []
    for row in result.data:
        transaction = row.pop("transactions", None) or {}
        reason_codes = row.pop("reason_codes", None) or {}
        rows.append(
            {
                **row,
                "event_type": transaction.get("event_type"),
                "archetype": reason_codes.get("archetype"),
            }
        )
    return rows
