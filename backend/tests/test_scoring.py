def test_risk_model_returns_expected_score_shape(trained_risk_model):
    record = {
        "event_type": "loan_disbursement",
        "step": 5,
        "amount": 5000.0,
        "origin_account": "C1",
        "origin_balance_before": 5000.0,
        "origin_balance_after": 0.0,
        "dest_balance_before": 1000.0,
        "dest_balance_after": 6000.0,
    }
    result = trained_risk_model.score(record)
    assert set(result) == {
        "supervised_score",
        "anomaly_score",
        "risk_score",
        "archetype",
        "label",
        "rationale",
    }
    assert 0.0 <= result["supervised_score"] <= 1.0
    assert 0.0 <= result["anomaly_score"] <= 1.0
    assert 0.0 <= result["risk_score"] <= 1.0


def test_risk_model_fuses_scores_with_event_type_alpha(trained_risk_model):
    from ml.config import fusion_alpha_for_event_type

    record = {
        "event_type": "loan_disbursement",
        "step": 5,
        "amount": 5000.0,
        "origin_account": "C1",
        "origin_balance_before": 5000.0,
        "origin_balance_after": 0.0,
        "dest_balance_before": 1000.0,
        "dest_balance_after": 6000.0,
    }
    result = trained_risk_model.score(record)
    alpha = fusion_alpha_for_event_type(record["event_type"])
    expected = alpha * result["supervised_score"] + (1 - alpha) * result["anomaly_score"]
    assert abs(result["risk_score"] - expected) < 1e-9


def test_unlabeled_event_type_weighs_anomaly_score_more_heavily(trained_risk_model):
    from ml.config import FUSION_ALPHA_LABELED, FUSION_ALPHA_UNLABELED

    assert FUSION_ALPHA_UNLABELED < FUSION_ALPHA_LABELED


def test_top_features_returns_k_entries_sorted_by_magnitude(trained_risk_model):
    record = {
        "event_type": "loan_disbursement",
        "step": 5,
        "amount": 5000.0,
        "origin_account": "C1",
        "origin_balance_before": 5000.0,
        "origin_balance_after": 0.0,
        "dest_balance_before": 1000.0,
        "dest_balance_after": 6000.0,
    }
    features = trained_risk_model.top_features(record, k=3)
    assert len(features) == 3
    magnitudes = [abs(f["contribution"]) for f in features]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_drained_disbursement_scores_higher_than_normal_repayment(trained_risk_model):
    drained = {
        "event_type": "loan_disbursement",
        "step": 5,
        "amount": 5000.0,
        "origin_account": "C1",
        "origin_balance_before": 5000.0,
        "origin_balance_after": 0.0,
        "dest_balance_before": 1000.0,
        "dest_balance_after": 6000.0,
    }
    normal = {
        "event_type": "installment_repayment",
        "step": 5,
        "amount": 150.0,
        "origin_account": "C2",
        "origin_balance_before": 2000.0,
        "origin_balance_after": 1850.0,
        "dest_balance_before": 0.0,
        "dest_balance_after": 0.0,
    }
    drained_score = trained_risk_model.score(drained)["risk_score"]
    normal_score = trained_risk_model.score(normal)["risk_score"]
    assert drained_score > normal_score
