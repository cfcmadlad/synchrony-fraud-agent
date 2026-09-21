from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_analyst_or_admin
from app.db import get_service_client
from app.schemas import AnalystFeedbackCreate, AnalystFeedbackOut

router = APIRouter(prefix="/api/transactions", tags=["feedback"])


@router.post("/{transaction_id}/feedback", response_model=AnalystFeedbackOut)
def submit_feedback(
    transaction_id: UUID, payload: AnalystFeedbackCreate, user=Depends(require_analyst_or_admin)
) -> AnalystFeedbackOut:
    client = get_service_client()
    result = (
        client.table("analyst_feedback")
        .insert(
            {
                "transaction_id": str(transaction_id),
                "analyst_id": user.user_id,
                "analyst_email": user.email,
                "decision": payload.decision,
                "notes": payload.notes,
            }
        )
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Insert returned no data")
    return AnalystFeedbackOut(**result.data[0])


@router.get("/{transaction_id}/feedback", response_model=list[AnalystFeedbackOut])
def list_feedback(transaction_id: UUID, user=Depends(require_analyst_or_admin)) -> list[AnalystFeedbackOut]:
    client = get_service_client()
    result = (
        client.table("analyst_feedback")
        .select("*")
        .eq("transaction_id", str(transaction_id))
        .order("created_at", desc=True)
        .execute()
    )
    return [AnalystFeedbackOut(**row) for row in result.data]
