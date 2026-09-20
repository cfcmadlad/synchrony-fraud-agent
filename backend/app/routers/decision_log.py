from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth import require_admin
from app.db import get_service_client

router = APIRouter(prefix="/api/decision-log", tags=["decision-log"])


@router.get("/{transaction_id}")
def get_decision_log(transaction_id: UUID, user=Depends(require_admin)) -> list[dict]:
    client = get_service_client()
    result = (
        client.table("agent_decision_log")
        .select("*")
        .eq("transaction_id", str(transaction_id))
        .order("created_at")
        .execute()
    )
    return result.data
