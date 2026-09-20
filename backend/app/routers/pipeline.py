from fastapi import APIRouter, Depends

from agent.graph import get_pipeline
from app.auth import require_analyst_or_admin
from app.schemas import PipelineResultOut, TransactionCreate

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run", response_model=PipelineResultOut)
def run_pipeline(
    payload: TransactionCreate, user=Depends(require_analyst_or_admin)
) -> PipelineResultOut:
    pipeline = get_pipeline()
    final_state = pipeline.invoke({"record": payload.model_dump(), "retry_count": 0})
    return PipelineResultOut(**final_state)
