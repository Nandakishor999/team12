from pydantic import BaseModel, Field
from typing import Optional


class EmployeeImportRow(BaseModel):
    # Expected columns (we'll map case-insensitively)
    email: str = Field(..., min_length=3, max_length=120)
    fullName: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=6, max_length=200)


class EmployeeImportResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0

