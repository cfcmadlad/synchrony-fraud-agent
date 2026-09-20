def build_case_text(record: dict, score_result: dict, outcome: bool | None = None) -> str:
    text = (
        f"{record['event_type'].replace('_', ' ')} of {record['amount']:.2f} "
        f"from account {record['origin_account']}. "
        f"Fused risk score {score_result['risk_score']:.2f} "
        f"(supervised {score_result['supervised_score']:.2f}, "
        f"anomaly {score_result['anomaly_score']:.2f}). "
        f"Pattern: {score_result['label']}. {score_result['rationale']}"
    )
    if outcome is not None:
        text += f" Historical outcome: {'confirmed fraud' if outcome else 'legitimate'}."
    return text
