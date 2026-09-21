from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

EventType = Literal["loan_disbursement", "installment_repayment", "fee_charge", "account_funding"]
TransactionStatus = Literal["pending", "allowed", "escalated", "blocked"]


class TransactionCreate(BaseModel):
    event_type: EventType
    step: Optional[int] = Field(default=None, ge=0)
    amount: float = Field(gt=0, le=10_000_000)
    origin_account: str = Field(min_length=1, max_length=100)
    dest_account: Optional[str] = Field(default=None, max_length=100)
    origin_balance_before: Optional[float] = Field(default=None, ge=0)
    origin_balance_after: Optional[float] = Field(default=None, ge=0)
    dest_balance_before: Optional[float] = Field(default=None, ge=0)
    dest_balance_after: Optional[float] = Field(default=None, ge=0)
    is_fraud_label: Optional[bool] = None


class RiskScoreOut(BaseModel):
    supervised_score: float
    anomaly_score: float
    risk_score: float
    archetype: str
    label: str
    rationale: str


class PipelineResultOut(BaseModel):
    transaction_id: UUID
    supervised_score: float
    anomaly_score: float
    risk_score: float
    archetype: str
    label: str
    rationale: str
    explanation: str
    explanation_provider: str
    decision: str
    similar_cases: list[dict]


class FraudFlagOut(BaseModel):
    id: UUID
    transaction_id: UUID
    risk_score: float
    supervised_score: Optional[float] = None
    anomaly_score: Optional[float] = None
    decision: str
    reason_codes: Optional[dict] = None
    created_at: datetime


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
