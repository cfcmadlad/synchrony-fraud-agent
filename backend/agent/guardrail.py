import re

from ml.archetypes import (
    ACCOUNT_TAKEOVER_PATTERN,
    PROMOTIONAL_FINANCING_ABUSE,
    SYNTHETIC_IDENTITY_ORIGINATION,
)

NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\d*")
TRIVIAL_NUMBERS = {0.0, 1.0, 2.0, 3.0}

ARCHETYPE_KEYWORDS = {
    SYNTHETIC_IDENTITY_ORIGINATION: "synthetic identity",
    PROMOTIONAL_FINANCING_ABUSE: "promotional financing",
    ACCOUNT_TAKEOVER_PATTERN: "account takeover",
}


def extract_numbers(text: str) -> list[float]:
    numbers = []
    for match in NUMBER_PATTERN.findall(text):
        cleaned = match.replace(",", "").strip(".")
        if not cleaned:
            continue
        try:
            numbers.append(float(cleaned))
        except ValueError:
            continue
    return numbers


def build_evidence_blob(evidence: dict) -> str:
    record = evidence["record"]
    parts = [
        str(record["amount"]),
        str(evidence["risk_score"]),
        str(evidence["risk_score"] * 100),
        str(evidence["supervised_score"]),
        str(evidence["supervised_score"] * 100),
        str(evidence["anomaly_score"]),
        str(evidence["anomaly_score"] * 100),
        evidence["rationale"],
        evidence["label"],
        str(record.get("origin_account", "")),
        str(record.get("dest_account", "")),
    ]
    for key in (
        "origin_balance_before",
        "origin_balance_after",
        "dest_balance_before",
        "dest_balance_after",
    ):
        value = record.get(key)
        if value is not None:
            parts.append(str(value))
    for feature in evidence["top_features"]:
        parts.append(str(abs(feature["contribution"])))
    for case in evidence["similar_cases"]:
        parts.append(case["summary_text"])
        parts.append(str(case["similarity"]))
        parts.append(str(case["similarity"] * 100))
    return " ".join(parts)


def is_close_to_any(value: float, candidates: list[float], tolerance: float = 0.05) -> bool:
    for candidate in candidates:
        scale = max(abs(candidate), 1.0)
        if abs(value - candidate) <= tolerance * scale:
            return True
    return False


def guardrail_check(explanation: str, evidence: dict) -> tuple[bool, list[str]]:
    violations = []
    candidates = extract_numbers(build_evidence_blob(evidence))

    for number in extract_numbers(explanation):
        if number in TRIVIAL_NUMBERS:
            continue
        if not is_close_to_any(number, candidates):
            violations.append(f"unsupported number: {number}")

    explanation_lower = explanation.lower()
    mentions_other_archetype = any(
        keyword in explanation_lower
        for tag, keyword in ARCHETYPE_KEYWORDS.items()
        if tag != evidence["archetype"]
    )
    if mentions_other_archetype:
        violations.append("mentions a different archetype than the one detected")

    return len(violations) == 0, violations
