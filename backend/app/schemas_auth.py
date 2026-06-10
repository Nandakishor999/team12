from pydantic import BaseModel, Field
from typing import Literal


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    accessToken: str
    role: Literal["hr_admin", "employee"]
    companyId: str


class SignupResponse(BaseModel):
    message: str = "created"

