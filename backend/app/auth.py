import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        # fallback: allow using settings if user later adds it
        secret = getattr(settings, "JWT_SECRET", "")
    if not secret:
        raise RuntimeError("JWT_SECRET is not set")
    return secret


def _jwt_exp_minutes() -> int:
    val = os.getenv("JWT_EXP_MINUTES")
    if not val:
        val = str(getattr(settings, "JWT_EXP_MINUTES", 1440))
    try:
        return int(val)
    except ValueError:
        return 1440


def hash_password(password: str) -> str:
    try:
        from passlib.context import CryptContext
    except ImportError as exc:
        raise RuntimeError("passlib[bcrypt] is not installed") from exc

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        from passlib.context import CryptContext
    except ImportError as exc:
        raise RuntimeError("passlib[bcrypt] is not installed") from exc

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return bool(pwd_context.verify(password, hashed))


def create_access_token(*, user_id: str, role: str, company_id: str) -> str:
    try:
        import jwt
    except ImportError as exc:
        raise RuntimeError("pyjwt is not installed") from exc

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=_jwt_exp_minutes())

    payload = {
        "sub": user_id,
        "role": role,
        "companyId": company_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    token = jwt.encode(payload, _jwt_secret(), algorithm="HS256")
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        import jwt
    except ImportError as exc:
        raise RuntimeError("pyjwt is not installed") from exc

    try:
        return jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

