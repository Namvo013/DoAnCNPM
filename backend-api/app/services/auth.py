import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from bson import ObjectId
from fastapi import HTTPException, status

from app.config import Settings, get_settings

COOKIE_NAME = "admin_session"
HASH_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, HASH_ITERATIONS)
    return "$".join(
        (
            "pbkdf2_sha256",
            str(HASH_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations, salt, expected = password_hash.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.urlsafe_b64decode(salt),
            int(iterations),
        )
        return hmac.compare_digest(
            base64.urlsafe_b64encode(digest).decode("ascii"),
            expected,
        )
    except (ValueError, TypeError):
        return False


def admin_response(admin: dict[str, Any]) -> dict[str, Any]:
    created_at = admin.get("created_at", datetime.now(timezone.utc))
    return {
        "id": str(admin["_id"]),
        "email": admin["email"],
        "display_name": admin["display_name"],
        "role": admin["role"],
        "is_active": bool(admin.get("is_active", True)),
        "created_at": created_at.isoformat(),
    }


class AuthService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _encode_token(self, admin: dict[str, Any]) -> tuple[str, int]:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=self.settings.jwt_expire_minutes)
        payload = {
            "sub": str(admin["_id"]),
            "role": admin["role"],
            "jti": secrets.token_urlsafe(24),
            "iat": now,
            "exp": expires,
        }
        return jwt.encode(payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm), int(
            expires.timestamp()
        )

    def decode_token(self, token: str) -> dict[str, Any]:
        return jwt.decode(
            token,
            self.settings.jwt_secret,
            algorithms=[self.settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat", "jti"]},
        )

    async def login(self, database: Any, email: str, password: str) -> tuple[dict[str, Any], str, int]:
        admin = await database.admins.find_one({"email": email.strip().lower()})
        valid_password = verify_password(password, admin["password_hash"]) if admin else False
        if not admin or not admin.get("is_active", True) or not valid_password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        token, expires_at = self._encode_token(admin)
        return admin_response(admin), token, expires_at

    async def get_current_admin(self, database: Any, redis: Any, token: str | None) -> dict[str, Any]:
        unauthorized = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Cookie"},
        )
        if not token:
            raise unauthorized
        try:
            claims = self.decode_token(token)
            if await redis.get(f"auth:revoked:{claims['jti']}"):
                raise unauthorized
            admin_id = ObjectId(claims["sub"])
        except (jwt.InvalidTokenError, ValueError, TypeError):
            raise unauthorized from None
        admin = await database.admins.find_one({"_id": admin_id})
        if not admin or not admin.get("is_active", True):
            raise unauthorized
        return admin

    async def logout(self, redis: Any, token: str | None) -> None:
        if not token:
            return
        try:
            claims = self.decode_token(token)
        except jwt.InvalidTokenError:
            return
        ttl = max(int(claims["exp"] - datetime.now(timezone.utc).timestamp()), 1)
        await redis.setex(f"auth:revoked:{claims['jti']}", ttl, "1")
