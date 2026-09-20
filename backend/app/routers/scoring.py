from fastapi import APIRouter, Depends

from app.auth import require_analyst_or_admin
from app.schemas import RiskScoreOut, TransactionCreate
from ml.scoring import get_risk_model

router = APIRouter(prefix="/api/score", tags=["scoring"])


@router.post("", response_model=RiskScoreOut)
def score_transaction(
    payload: TransactionCreate, user=Depends(require_analyst_or_admin)
) -> RiskScoreOut:
    model = get_risk_model()
    result = model.score(payload.model_dump())
    return RiskScoreOut(**result)
