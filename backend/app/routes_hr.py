from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.db import get_db
from app.deps import require_role
from app.schemas_company import CompanyCreateRequest, PoliciesUpsertRequest
from app.schemas_hr_import import EmployeeImportResult



router = APIRouter(prefix="/api/hr", tags=["HR"])


@router.post(
    "/companies",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(role="hr_admin"))],
)
async def create_company(payload: CompanyCreateRequest):
    """Create a company window (workspace) for an HR admin."""
    company_name = payload.companyName.strip()
    company_id = company_name.lower().replace(" ", "-")

    db = get_db()
    await db.companies.update_one(
        {"companyId": company_id},
        {"$setOnInsert": {"companyId": company_id, "name": company_name}},
        upsert=True,
    )

    return {"companyId": company_id, "name": company_name}



@router.put(
    "/companies/{company_id}/policies",
    dependencies=[Depends(require_role(role="hr_admin"))],
)
async def upsert_policies(company_id: str, payload: PoliciesUpsertRequest):
    """Upsert full policy JSON for a company."""
    db = get_db()
    await db.policies.update_one(
        {"companyId": company_id},
        {"$set": {"companyId": company_id, "content": payload.policies}},
        upsert=True,
    )
    return {"status": "ok"}



@router.post(
    "/companies/{company_id}/employees/import",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(role="hr_admin"))],
)
async def import_employees(company_id: str, file: UploadFile = File(...)):
    """Import employees from CSV/XLSX.

    Expected columns (case-insensitive):
    - email
    - fullName (or name)
    - password

    This endpoint upserts users in `users` collection with:
      role='employee', companyId=company_id
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="file required")

    content_type = (file.content_type or "").lower()
    filename = file.filename.lower()

    raw = await file.read()

    # Lazy imports to avoid dependency issues when not used.
    if filename.endswith(".csv") or "csv" in content_type:
        import csv
        from io import StringIO

        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(StringIO(text))

        def _norm(k: str) -> str:
            return (k or "").strip().lower()

        results = EmployeeImportResult()
        db = get_db()

        for row in reader:
            row_norm = {_norm(k): (v or "").strip() for k, v in row.items() if k is not None}
            email = row_norm.get("email")
            full_name = row_norm.get("fullname") or row_norm.get("name") or row_norm.get("full_name")
            password = row_norm.get("password")
            if not email or not full_name or not password:
                results.skipped += 1
                continue

            existing = await db.users.find_one({"email": email, "companyId": company_id})
            password_hash = None
            from app.auth import hash_password

            password_hash = hash_password(password)

            payload = {
                "email": email,
                "fullName": full_name,
                "passwordHash": password_hash,
                "role": "employee",
                "companyId": company_id,
            }

            if existing:
                await db.users.update_one({"_id": existing["_id"]}, {"$set": payload})
                results.updated += 1
            else:
                await db.users.insert_one(payload)
                results.created += 1

        return results.model_dump()

    if filename.endswith(".xlsx") or filename.endswith(".xls") or "sheet" in content_type:
        # XLSX parsing
        try:
            import pandas as pd
        except ImportError as exc:
            raise HTTPException(
                status_code=400,
                detail="XLSX import requires pandas. Please install pandas in backend.",
            ) from exc

        import io

        df = pd.read_excel(io.BytesIO(raw))
        results = EmployeeImportResult()
        db = get_db()

        # Normalize column names
        col_map = {str(c).strip().lower(): c for c in df.columns}
        for _, r in df.iterrows():
            email = str(r.get(col_map.get("email", ""), "") or "").strip()
            full_name = (
                str(r.get(col_map.get("fullname", ""), "") or "").strip()
                or str(r.get(col_map.get("name", ""), "") or "").strip()
            )
            password = str(r.get(col_map.get("password", ""), "") or "").strip()

            if not email or not full_name or not password:
                results.skipped += 1
                continue

            existing = await db.users.find_one({"email": email, "companyId": company_id})
            from app.auth import hash_password

            payload = {
                "email": email,
                "fullName": full_name,
                "passwordHash": hash_password(password),
                "role": "employee",
                "companyId": company_id,
            }

            if existing:
                await db.users.update_one({"_id": existing["_id"]}, {"$set": payload})
                results.updated += 1
            else:
                await db.users.insert_one(payload)
                results.created += 1

        return results.model_dump()

    raise HTTPException(
        status_code=400,
        detail="Unsupported file type. Upload CSV or XLSX.",
    )


