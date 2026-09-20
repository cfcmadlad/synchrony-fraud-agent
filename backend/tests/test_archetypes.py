from ml.archetypes import (
    ACCOUNT_TAKEOVER_PATTERN,
    NORMAL_ACTIVITY,
    PROMOTIONAL_FINANCING_ABUSE,
    SYNTHETIC_IDENTITY_ORIGINATION,
    tag_archetype,
)


def test_drained_disbursement_is_synthetic_identity():
    record = {
        "event_type": "loan_disbursement",
        "amount": 5000.0,
        "origin_balance_before": 5000.0,
        "origin_balance_after": 0.0,
    }
    scores = {"supervised_score": 0.9, "anomaly_score": 0.9, "risk_score": 0.9}
    result = tag_archetype(record, scores)
    assert result["archetype"] == SYNTHETIC_IDENTITY_ORIGINATION


def test_token_repayment_is_promotional_financing_abuse():
    record = {
        "event_type": "installment_repayment",
        "amount": 2.0,
        "origin_balance_before": 5000.0,
        "origin_balance_after": 4998.0,
    }
    scores = {"supervised_score": 0.01, "anomaly_score": 0.8, "risk_score": 0.25}
    result = tag_archetype(record, scores)
    assert result["archetype"] == PROMOTIONAL_FINANCING_ABUSE


def test_near_full_drain_fee_is_account_takeover():
    record = {
        "event_type": "fee_charge",
        "amount": 4990.0,
        "origin_balance_before": 5000.0,
        "origin_balance_after": 10.0,
    }
    scores = {"supervised_score": 0.01, "anomaly_score": 0.9, "risk_score": 0.3}
    result = tag_archetype(record, scores)
    assert result["archetype"] == ACCOUNT_TAKEOVER_PATTERN


def test_ordinary_payment_is_normal_activity():
    record = {
        "event_type": "installment_repayment",
        "amount": 150.0,
        "origin_balance_before": 2000.0,
        "origin_balance_after": 1850.0,
    }
    scores = {"supervised_score": 0.001, "anomaly_score": 0.2, "risk_score": 0.07}
    result = tag_archetype(record, scores)
    assert result["archetype"] == NORMAL_ACTIVITY


def test_disbursement_not_drained_does_not_match_synthetic_identity():
    record = {
        "event_type": "loan_disbursement",
        "amount": 500.0,
        "origin_balance_before": 5000.0,
        "origin_balance_after": 4500.0,
    }
    scores = {"supervised_score": 0.9, "anomaly_score": 0.1, "risk_score": 0.6}
    result = tag_archetype(record, scores)
    assert result["archetype"] != SYNTHETIC_IDENTITY_ORIGINATION
