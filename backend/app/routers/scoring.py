from fastapi import APIRouter

from app.schemas import RiskScoreOut, TransactionCreate
from ml.scoring import get_risk_model

router = APIRouter(prefix="/api/score", tags=["scoring"])


@router.post("", response_model=RiskScoreOut)
def score_transaction(payload: TransactionCreate) -> RiskScoreOut:
    model = get_risk_model()
    result = model.score(payload.model_dump())
    return RiskScoreOut(**result)
