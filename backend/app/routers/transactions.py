from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_analyst_or_admin
from app.db import get_service_client
from app.schemas import FraudFlagOut, TransactionCreate, TransactionOut, TransactionStatus

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
    offset: int = Query(default=0, ge=0),
    status: Optional[TransactionStatus] = None,
    order_by: Literal["created_at", "risk_score"] = "created_at",
    user=Depends(require_analyst_or_admin),
) -> list[TransactionOut]:
    client = get_service_client()
    query = client.table("transactions").select("*")
    if status is not None:
        query = query.eq("status", status)
    result = (
        query.order(order_by, desc=True, nullsfirst=False)
        .range(offset, offset + limit - 1)
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


@router.get("/{transaction_id}/flag", response_model=FraudFlagOut)
def get_transaction_flag(
    transaction_id: UUID, user=Depends(require_analyst_or_admin)
) -> FraudFlagOut:
    client = get_service_client()
    result = (
        client.table("fraud_flags")
        .select("*")
        .eq("transaction_id", str(transaction_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No fraud flag for this transaction")
    return FraudFlagOut(**result.data[0])
