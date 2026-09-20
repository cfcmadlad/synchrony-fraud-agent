from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_analyst_or_admin
from app.db import get_service_client
from app.schemas import TransactionCreate, TransactionOut

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.post("", response_model=TransactionOut)
def create_transaction(
    payload: TransactionCreate, user=Depends(require_analyst_or_admin)
) -> TransactionOut:
    client = get_service_client()
    result = client.table("transactions").insert(payload.model_dump(exclude_none=True)).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Insert returned no data")
    return TransactionOut(**result.data[0])


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(require_analyst_or_admin),
) -> list[TransactionOut]:
    client = get_service_client()
    result = (
        client.table("transactions")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [TransactionOut(**row) for row in result.data]


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: UUID, user=Depends(require_analyst_or_admin)
) -> TransactionOut:
    client = get_service_client()
    result = client.table("transactions").select("*").eq("id", str(transaction_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionOut(**result.data[0])
