from fastapi import APIRouter

from agent.graph import get_pipeline
from app.schemas import PipelineResultOut, TransactionCreate

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run", response_model=PipelineResultOut)
def run_pipeline(payload: TransactionCreate) -> PipelineResultOut:
    pipeline = get_pipeline()
    final_state = pipeline.invoke({"record": payload.model_dump(), "retry_count": 0})
    return PipelineResultOut(**final_state)
