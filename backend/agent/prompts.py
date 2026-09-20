def format_feature_line(feature: dict) -> str:
    direction = "increased" if feature["contribution"] > 0 else "decreased"
    return f"- {feature['feature']} {direction} the risk score by {abs(feature['contribution']):.3f}"


def format_similar_case_line(case: dict) -> str:
    return f"- {case['summary_text']} (similarity {case['similarity']:.2f})"


def build_explain_prompt(evidence: dict) -> str:
    record = evidence["record"]
    feature_lines = "\n".join(format_feature_line(f) for f in evidence["top_features"])
    case_lines = "\n".join(format_similar_case_line(c) for c in evidence["similar_cases"]) or (
        "- No similar historical cases were found."
    )

    return f"""You are a fraud analyst assistant writing a short explanation for a flagged
transaction in Synchrony's digital lending platform. Use ONLY the facts listed below.
Do not invent account details, dollar amounts, or outcomes that are not listed here.
Do not mention any archetype other than the one given. Write 2-3 concise sentences for
a human fraud analyst.

Transaction:
- event type: {record['event_type']}
- amount: {record['amount']:.2f}
- origin account: {record['origin_account']}

Model output:
- fused risk score: {evidence['risk_score']:.2f}
- supervised model score: {evidence['supervised_score']:.2f}
- anomaly detector score: {evidence['anomaly_score']:.2f}
- matched pattern: {evidence['label']}
- pattern rationale: {evidence['rationale']}

Top contributing features:
{feature_lines}

Similar historical cases:
{case_lines}

Write the explanation now."""


def build_fallback_explanation(evidence: dict) -> str:
    record = evidence["record"]
    top_feature = evidence["top_features"][0] if evidence["top_features"] else None
    feature_clause = (
        f" The strongest contributing factor was {top_feature['feature']}."
        if top_feature
        else ""
    )
    return (
        f"This {record['event_type'].replace('_', ' ')} of {record['amount']:.2f} received a "
        f"fused risk score of {evidence['risk_score']:.2f}, matching the pattern "
        f"'{evidence['label']}': {evidence['rationale']}{feature_clause}"
    )
