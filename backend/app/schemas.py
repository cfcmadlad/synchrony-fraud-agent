from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

EventType = Literal["loan_disbursement", "installment_repayment", "fee_charge", "account_funding"]
TransactionStatus = Literal["pending", "allowed", "escalated", "blocked"]


class TransactionCreate(BaseModel):
    event_type: EventType
    step: Optional[int] = None
    amount: float = Field(gt=0)
    origin_account: str
    dest_account: Optional[str] = None
    origin_balance_before: Optional[float] = None
    origin_balance_after: Optional[float] = None
    dest_balance_before: Optional[float] = None
    dest_balance_after: Optional[float] = None
    is_fraud_label: Optional[bool] = None


class RiskScoreOut(BaseModel):
    supervised_score: float
    anomaly_score: float
    risk_score: float


class TransactionOut(BaseModel):
    id: UUID
    event_type: EventType
    step: Optional[int] = None
    amount: float
    origin_account: str
    dest_account: Optional[str] = None
    origin_balance_before: Optional[float] = None
    origin_balance_after: Optional[float] = None
    dest_balance_before: Optional[float] = None
    dest_balance_after: Optional[float] = None
    is_fraud_label: Optional[bool] = None
    risk_score: Optional[float] = None
    status: TransactionStatus
    created_at: datetime
