from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user


def test_me_endpoint_returns_current_user():
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="test-user", email="admin@test.com", role="admin"
    )

    client = TestClient(app)
    response = client.get("/api/me")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body == {"user_id": "test-user", "email": "admin@test.com", "role": "admin"}


def test_me_endpoint_rejects_missing_token():
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/me")
    assert response.status_code == 401
