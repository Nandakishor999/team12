from fastapi import APIRouter, HTTPException, status

from app.db import get_db
from app.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.deps import require_role
from app.schemas_auth import LoginRequest, LoginResponse, SignupResponse

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    db = get_db()

    user = await db.users.find_one({"email": payload.email})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, user.get("passwordHash") or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    role = user.get("role")
    company_id = user.get("companyId")
    if role not in ("hr_admin", "employee") or not company_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user record")

    token = create_access_token(user_id=str(user.get("_id")), role=role, company_id=company_id)
    return LoginResponse(accessToken=token, role=role, companyId=company_id)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout():
    # Client-side logout (drop token). If we add refresh tokens later,
    # we can blacklist on server.
    return {"message": "logged out"}


