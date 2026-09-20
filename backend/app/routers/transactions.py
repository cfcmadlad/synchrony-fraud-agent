from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.db import get_service_client
from app.schemas import TransactionCreate, TransactionOut

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.post("", response_model=TransactionOut)
def create_transaction(payload: TransactionCreate) -> TransactionOut:
    client = get_service_client()
    result = client.table("transactions").insert(payload.model_dump(exclude_none=True)).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Insert returned no data")
    return TransactionOut(**result.data[0])


@router.get("", response_model=list[TransactionOut])
def list_transactions(limit: int = 50) -> list[TransactionOut]:
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
def get_transaction(transaction_id: UUID) -> TransactionOut:
    client = get_service_client()
    result = client.table("transactions").select("*").eq("id", str(transaction_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionOut(**result.data[0])


@router.post("/dummy", response_model=TransactionOut)
def create_dummy_transaction() -> TransactionOut:
    dummy = TransactionCreate(
        event_type="loan_disbursement",
        step=1,
        amount=2500.00,
        origin_account="applicant-demo-0001",
        dest_account="merchant-demo-pos-77",
        origin_balance_before=0.0,
        origin_balance_after=2500.0,
        dest_balance_before=10000.0,
        dest_balance_after=12500.0,
        is_fraud_label=False,
    )
    return create_transaction(dummy)
