import time

import jwt
import pytest
from fastapi import HTTPException

from app.auth import decode_token, get_current_user, require_role
from app.config import get_settings

TEST_SECRET = "unit-test-jwt-secret-value-long-enough"


def make_token(sub="user-1", email="analyst@test.com", expired=False, audience="authenticated"):
    exp = int(time.time()) - 3600 if expired else int(time.time()) + 3600
    payload = {"sub": sub, "email": email, "aud": audience, "exp": exp}
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
def patched_secret(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    yield
    get_settings.cache_clear()


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeTable:
    def __init__(self, role_by_user):
        self.role_by_user = role_by_user
        self._user_id = None

    def select(self, *_args):
        return self

    def eq(self, _column, value):
        self._user_id = value
        return self

    def execute(self):
        role = self.role_by_user.get(self._user_id)
        return FakeResult([{"role": role}] if role else [])


class FakeClient:
    def __init__(self, role_by_user):
        self.role_by_user = role_by_user

    def table(self, _name):
        return FakeTable(self.role_by_user)


def test_decode_token_rejects_missing_header(patched_secret):
    with pytest.raises(HTTPException) as exc_info:
        decode_token(None)
    assert exc_info.value.status_code == 401


def test_decode_token_rejects_non_bearer_header(patched_secret):
    with pytest.raises(HTTPException) as exc_info:
        decode_token("Basic abc123")
    assert exc_info.value.status_code == 401


def test_decode_token_rejects_expired_token(patched_secret):
    token = make_token(expired=True)
    with pytest.raises(HTTPException) as exc_info:
        decode_token(f"Bearer {token}")
    assert exc_info.value.status_code == 401


def test_decode_token_rejects_wrong_signature(patched_secret):
    token = jwt.encode(
        {"sub": "user-1", "aud": "authenticated", "exp": int(time.time()) + 3600},
        "a-completely-different-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_token(f"Bearer {token}")
    assert exc_info.value.status_code == 401


def test_decode_token_accepts_valid_token(patched_secret):
    token = make_token()
    payload = decode_token(f"Bearer {token}")
    assert payload["sub"] == "user-1"


def test_get_current_user_returns_role_from_db(patched_secret, monkeypatch):
    monkeypatch.setattr(
        "app.auth.get_service_client", lambda: FakeClient({"user-1": "analyst"})
    )
    token = make_token(sub="user-1")
    user = get_current_user(f"Bearer {token}")
    assert user.role == "analyst"
    assert user.user_id == "user-1"


def test_get_current_user_rejects_user_with_no_role(patched_secret, monkeypatch):
    monkeypatch.setattr("app.auth.get_service_client", lambda: FakeClient({}))
    token = make_token(sub="user-without-role")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(f"Bearer {token}")
    assert exc_info.value.status_code == 403


def test_require_role_allows_matching_role(patched_secret, monkeypatch):
    monkeypatch.setattr(
        "app.auth.get_service_client", lambda: FakeClient({"user-1": "admin"})
    )
    token = make_token(sub="user-1")
    dependency = require_role("admin")
    user = dependency(f"Bearer {token}")
    assert user.role == "admin"


def test_require_role_rejects_wrong_role(patched_secret, monkeypatch):
    monkeypatch.setattr(
        "app.auth.get_service_client", lambda: FakeClient({"user-1": "analyst"})
    )
    token = make_token(sub="user-1")
    dependency = require_role("admin")
    with pytest.raises(HTTPException) as exc_info:
        dependency(f"Bearer {token}")
    assert exc_info.value.status_code == 403
