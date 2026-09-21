import functools
import logging
import time
from functools import lru_cache

from langgraph.graph import END, StateGraph

from agent.guardrail import guardrail_check
from agent.llm_client import generate_explanation
from agent.decision_log import build_log_entry
from agent.pii import scrub_record
from agent.prompts import build_explain_prompt, build_fallback_explanation
from agent.retrieval import retrieve_similar_cases
from agent.state import AgentState
from app.db import get_service_client
from ml.case_text import build_case_text
from ml.config import DECISION_THRESHOLD_BLOCK, DECISION_THRESHOLD_ESCALATE, MAX_GUARDRAIL_RETRIES
from ml.scoring import get_risk_model

perf_logger = logging.getLogger("agent.perf")


def timed_node(name):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(state):
            started = time.perf_counter()
            result = fn(state)
            elapsed_ms = (time.perf_counter() - started) * 1000
            perf_logger.info("node=%s duration_ms=%.2f", name, elapsed_ms)
            return result

        return wrapper

    return decorator


@timed_node("ingest")
def ingest_node(state: AgentState) -> dict:
    record = state["record"]
    client = get_service_client()
    inserted = (
        client.table("transactions")
        .insert(
            {
                "event_type": record["event_type"],
                "step": record.get("step"),
                "amount": record["amount"],
                "origin_account": record["origin_account"],
                "dest_account": record.get("dest_account"),
                "origin_balance_before": record.get("origin_balance_before"),
                "origin_balance_after": record.get("origin_balance_after"),
                "dest_balance_before": record.get("dest_balance_before"),
                "dest_balance_after": record.get("dest_balance_after"),
            }
        )
        .execute()
        .data[0]
    )
    transaction_id = inserted["id"]
    entry = build_log_entry(transaction_id, "ingest", record, inserted)
    return {"transaction_id": transaction_id, "log_entries": [entry]}


@timed_node("detect")
def detect_node(state: AgentState) -> dict:
    model = get_risk_model()
    result = model.score(state["record"])
    top_features = model.top_features(state["record"])

    client = get_service_client()
    client.table("transactions").update({"risk_score": result["risk_score"]}).eq(
        "id", state["transaction_id"]
    ).execute()

    entry = build_log_entry(
        state["transaction_id"], "detect", state["record"], {**result, "top_features": top_features}
    )

    return {
        "supervised_score": result["supervised_score"],
        "anomaly_score": result["anomaly_score"],
        "risk_score": result["risk_score"],
        "archetype": result["archetype"],
        "label": result["label"],
        "rationale": result["rationale"],
        "top_features": top_features,
        "log_entries": [entry],
    }


@timed_node("retrieve")
def retrieve_node(state: AgentState) -> dict:
    score_result = {
        "supervised_score": state["supervised_score"],
        "anomaly_score": state["anomaly_score"],
        "risk_score": state["risk_score"],
        "label": state["label"],
        "rationale": state["rationale"],
    }
    query_text = build_case_text(state["record"], score_result, outcome=None)
    matches = retrieve_similar_cases(query_text, exclude_transaction_id=state["transaction_id"])

    entry = build_log_entry(state["transaction_id"], "retrieve", {"query_text": query_text}, {"matches": matches})

    return {"similar_cases": matches, "log_entries": [entry]}


def build_evidence(state: AgentState) -> dict:
    return {
        "record": scrub_record(state["record"]),
        "supervised_score": state["supervised_score"],
        "anomaly_score": state["anomaly_score"],
        "risk_score": state["risk_score"],
        "archetype": state["archetype"],
        "label": state["label"],
        "rationale": state["rationale"],
        "top_features": state["top_features"],
        "similar_cases": state["similar_cases"],
    }


@timed_node("explain")
def explain_node(state: AgentState) -> dict:
    evidence = build_evidence(state)
    prompt = build_explain_prompt(evidence)
    explanation, provider = generate_explanation(prompt)

    if explanation is None:
        explanation = build_fallback_explanation(evidence)
        provider = "template_fallback"

    entry = build_log_entry(
        state["transaction_id"],
        "explain",
        {"prompt": prompt},
        {"explanation": explanation, "provider": provider},
    )

    return {"explanation": explanation, "explanation_provider": provider, "log_entries": [entry]}


@timed_node("guardrail")
def guardrail_node(state: AgentState) -> dict:
    evidence = build_evidence(state)
    passed, violations = guardrail_check(state["explanation"], evidence)
    retry_count = state.get("retry_count", 0)

    if passed:
        entry = build_log_entry(
            state["transaction_id"],
            "guardrail",
            {"explanation": state["explanation"]},
            {"passed": True, "violations": []},
        )
        return {"guardrail_passed": True, "guardrail_violations": [], "log_entries": [entry]}

    if retry_count < MAX_GUARDRAIL_RETRIES:
        entry = build_log_entry(
            state["transaction_id"],
            "guardrail",
            {"explanation": state["explanation"]},
            {"passed": False, "violations": violations, "action": "retry"},
        )
        return {
            "guardrail_passed": False,
            "guardrail_violations": violations,
            "retry_count": retry_count + 1,
            "log_entries": [entry],
        }

    fallback = build_fallback_explanation(evidence)
    entry = build_log_entry(
        state["transaction_id"],
        "guardrail",
        {"explanation": state["explanation"]},
        {"passed": False, "violations": violations, "action": "fallback_to_template"},
    )
    return {
        "guardrail_passed": True,
        "guardrail_violations": violations,
        "explanation": fallback,
        "explanation_provider": "template_fallback",
        "log_entries": [entry],
    }


def route_after_guardrail(state: AgentState) -> str:
    return "decide" if state["guardrail_passed"] else "explain"


@timed_node("decide")
def decide_node(state: AgentState) -> dict:
    risk_score = state["risk_score"]

    if risk_score >= DECISION_THRESHOLD_BLOCK:
        decision, status = "block", "blocked"
    elif risk_score >= DECISION_THRESHOLD_ESCALATE:
        decision, status = "escalate", "escalated"
    else:
        decision, status = "allow", "allowed"

    client = get_service_client()
    client.table("transactions").update({"status": status}).eq("id", state["transaction_id"]).execute()
    client.table("fraud_flags").insert(
        {
            "transaction_id": state["transaction_id"],
            "risk_score": risk_score,
            "supervised_score": state["supervised_score"],
            "anomaly_score": state["anomaly_score"],
            "decision": decision,
            "reason_codes": {
                "archetype": state["archetype"],
                "label": state["label"],
                "top_features": state["top_features"],
            },
        }
    ).execute()

    entry = build_log_entry(
        state["transaction_id"],
        "decide",
        {"risk_score": risk_score},
        {"decision": decision, "status": status},
    )

    return {"decision": decision, "log_entries": [entry]}


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("ingest", ingest_node)
    builder.add_node("detect", detect_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("explain", explain_node)
    builder.add_node("guardrail", guardrail_node)
    builder.add_node("decide", decide_node)

    builder.set_entry_point("ingest")
    builder.add_edge("ingest", "detect")
    builder.add_edge("detect", "retrieve")
    builder.add_edge("retrieve", "explain")
    builder.add_edge("explain", "guardrail")
    builder.add_conditional_edges(
        "guardrail", route_after_guardrail, {"explain": "explain", "decide": "decide"}
    )
    builder.add_edge("decide", END)

    return builder.compile()


@lru_cache
def get_pipeline():
    return build_graph()
