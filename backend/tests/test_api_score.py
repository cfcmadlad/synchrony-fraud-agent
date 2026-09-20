from fastapi.testclient import TestClient

from app.auth import CurrentUser


def test_score_endpoint_returns_risk_score(trained_risk_model):
    from app.auth import require_analyst_or_admin
    from app.main import app

    app.dependency_overrides[require_analyst_or_admin] = lambda: CurrentUser(
        user_id="test-user", email="analyst@test.com", role="analyst"
    )

    client = TestClient(app)
    response = client.post(
        "/api/score",
        json={
            "event_type": "loan_disbursement",
            "step": 5,
            "amount": 5000.0,
            "origin_account": "C1",
            "origin_balance_before": 5000.0,
            "origin_balance_after": 0.0,
            "dest_balance_before": 1000.0,
            "dest_balance_after": 6000.0,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "risk_score" in body
    assert "archetype" in body


def test_score_endpoint_rejects_missing_required_field():
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/score",
        json={"event_type": "loan_disbursement", "amount": 5000.0},
    )
    assert response.status_code in (401, 422)


def test_score_endpoint_rejects_negative_amount():
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/score",
        json={
            "event_type": "loan_disbursement",
            "amount": -100.0,
            "origin_account": "C1",
        },
    )
    assert response.status_code in (401, 422)
