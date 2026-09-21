from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

RAW_CSV_PATH = REPO_ROOT / "data" / "raw" / "paysim.csv"
PROCESSED_PATH = REPO_ROOT / "data" / "processed" / "lending_transactions.csv"
SAMPLE_CSV_PATH = REPO_ROOT / "data" / "sample" / "lending_transactions_sample.csv"

ARTIFACTS_DIR = BACKEND_ROOT / "artifacts"
XGB_MODEL_PATH = ARTIFACTS_DIR / "xgb_model.json"
ISOLATION_FOREST_PATH = ARTIFACTS_DIR / "isolation_forest.joblib"
SCORING_CONFIG_PATH = ARTIFACTS_DIR / "scoring_config.json"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"

EVENT_TYPE_MAP = {
    "TRANSFER": "loan_disbursement",
    "CASH_OUT": "loan_disbursement",
    "PAYMENT": "installment_repayment",
    "DEBIT": "fee_charge",
    "CASH_IN": "account_funding",
}

EVENT_TYPES = ["loan_disbursement", "installment_repayment", "fee_charge", "account_funding"]

SUBSAMPLE_SIZE = 300_000
HISTORICAL_SAMPLE_SIZE = 3_000
RANDOM_STATE = 42

LABELED_EVENT_TYPES = ["loan_disbursement"]
FUSION_ALPHA_LABELED = 0.7
FUSION_ALPHA_UNLABELED = 0.6


def fusion_alpha_for_event_type(event_type: str) -> float:
    return FUSION_ALPHA_LABELED if event_type in LABELED_EVENT_TYPES else FUSION_ALPHA_UNLABELED


DECISION_THRESHOLD_ESCALATE = 0.4
DECISION_THRESHOLD_BLOCK = 0.75
SIMILAR_CASES_LIMIT = 5
MAX_GUARDRAIL_RETRIES = 2
GROQ_MIN_INTERVAL_SECONDS = 2.0
