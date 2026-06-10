from pydantic import BaseModel, Field
from typing import Any


class CompanyCreateRequest(BaseModel):
    companyName: str = Field(..., min_length=2, max_length=120)


class PoliciesUpsertRequest(BaseModel):
    # full policy document JSON
    policies: dict[str, Any]

