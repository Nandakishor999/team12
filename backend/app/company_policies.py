import json
import logging
from functools import lru_cache
from typing import Any, Optional

from app.db import get_db

logger = logging.getLogger(__name__)


async def get_company_policy_document(company_id: str) -> dict[str, Any]:
    """Fetch the policy JSON document for a specific company.

    Collection: policies
    { _id: companyId, content: <json> }

    We store the complete policy JSON under 'content' to reuse existing
    prompt logic (policies are injected as JSON text).
    """
    db = get_db()
    # allow either a dedicated policies collection or embedded in companies.
    doc = await db.policies.find_one({"companyId": company_id})
    if doc and "content" in doc:
        return doc["content"]

    # fallback: companies collection
    company = await db.companies.find_one({"companyId": company_id})
    if company and "policies" in company:
        return company["policies"]

    raise KeyError(f"Policy document not found for companyId={company_id}")


async def get_company_policy_document_text(company_id: str) -> str:
    data = await get_company_policy_document(company_id)
    return json.dumps(data, indent=2, ensure_ascii=False)

