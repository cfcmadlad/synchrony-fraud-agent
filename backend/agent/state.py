import operator
from typing import Annotated, TypedDict


class SimilarCase(TypedDict):
    transaction_id: str
    summary_text: str
    similarity: float


class AgentState(TypedDict):
    record: dict
    transaction_id: str
    supervised_score: float
    anomaly_score: float
    risk_score: float
    archetype: str
    label: str
    rationale: str
    top_features: list[dict]
    similar_cases: list[SimilarCase]
    explanation: str
    explanation_provider: str
    guardrail_passed: bool
    guardrail_violations: list[str]
    retry_count: int
    decision: str
    log_entries: Annotated[list[dict], operator.add]
