from functools import lru_cache

import jwt
from fastapi import Header, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.db import get_service_client


class CurrentUser(BaseModel):
    user_id: str
    email: str | None
    role: str


@lru_cache
def get_jwks_client() -> jwt.PyJWKClient:
    settings = get_settings()
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    return jwt.PyJWKClient(jwks_url)


def decode_token(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    payload = decode_token(authorization)
    user_id = payload["sub"]

    client = get_service_client()
    result = client.table("user_roles").select("role").eq("user_id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=403, detail="No role assigned to this account")

    return CurrentUser(user_id=user_id, email=payload.get("email"), role=result.data[0]["role"])


def require_role(*allowed_roles: str):
    def dependency(authorization: str | None = Header(default=None)) -> CurrentUser:
        user = get_current_user(authorization)
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient role for this action")
        return user

    return dependency


require_analyst_or_admin = require_role("analyst", "admin")
require_admin = require_role("admin")
