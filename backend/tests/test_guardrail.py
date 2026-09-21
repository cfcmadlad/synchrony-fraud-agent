from agent.guardrail import guardrail_check


def make_evidence(**overrides):
    evidence = {
        "record": {
            "event_type": "loan_disbursement",
            "amount": 5000.0,
            "origin_account": "C1",
            "origin_balance_before": 5000.0,
            "origin_balance_after": 0.0,
            "dest_balance_before": 1000.0,
            "dest_balance_after": 6000.0,
        },
        "supervised_score": 0.86,
        "anomaly_score": 0.99,
        "risk_score": 0.90,
        "archetype": "synthetic_identity_origination",
        "label": "Synthetic identity at loan origination",
        "rationale": "Loan disbursement of 5000.00 was followed by the origin account balance dropping from 5000.00 to zero.",
        "top_features": [{"feature": "origin_balance_after_zero", "contribution": 1.83}],
        "similar_cases": [],
    }
    evidence.update(overrides)
    return evidence


def test_grounded_explanation_passes():
    explanation = (
        "This loan disbursement of 5000.00 shows a synthetic identity pattern, with a "
        "fused risk score of 0.90 driven mainly by the account balance dropping to zero."
    )
    passed, violations = guardrail_check(explanation, make_evidence())
    assert passed
    assert violations == []


def test_fabricated_numbers_are_rejected():
    explanation = (
        "The fraudster called support 47 times using a stolen SSN ending in 8842 and "
        "moved $92,341 out of the account."
    )
    passed, violations = guardrail_check(explanation, make_evidence())
    assert not passed
    assert any("47" in v for v in violations)
    assert any("8842" in v for v in violations)
    assert any("92341" in v for v in violations)


def test_mismatched_archetype_mention_is_rejected():
    explanation = "This looks like account takeover on the servicing app, with a risk score of 0.90."
    passed, violations = guardrail_check(explanation, make_evidence())
    assert not passed
    assert any("different archetype" in v for v in violations)


def test_trivial_small_numbers_do_not_trigger_false_positive():
    explanation = "In the top 2 or 3 contributing features, this stands out as high risk."
    passed, violations = guardrail_check(explanation, make_evidence())
    assert passed
    assert violations == []


def test_percentage_of_risk_score_is_grounded():
    explanation = "This transaction has a 90% fused risk score."
    passed, violations = guardrail_check(explanation, make_evidence())
    assert passed


def test_account_id_digits_in_explanation_are_grounded():
    evidence = make_evidence(record={**make_evidence()["record"], "origin_account": "C956959892"})
    explanation = (
        "The loan disbursement from origin account C956959892 matches the synthetic "
        "identity pattern, with a fused risk score of 0.90."
    )
    passed, violations = guardrail_check(explanation, evidence)
    assert passed
    assert violations == []
