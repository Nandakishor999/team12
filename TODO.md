# TODO — HR Window Auth + Role-Based UI (HR + Employees)

## Backend (FastAPI)
- [ ] Add MongoDB Atlas integration (motor) and DB layer (db.py)
- [ ] Add JWT auth endpoints: /api/auth/login and /api/auth/logout
- [ ] Add role-based dependency/guard (HR admin vs Employee)
- [ ] Add HR workspace (company window) endpoints:
  - [ ] POST /api/hr/companies
  - [ ] PUT /api/hr/companies/{companyId}/policies
  - [ ] POST /api/hr/companies/{companyId}/employees/import (Excel/CSV)
- [ ] Update /api/chat to be company-aware using JWT claim (companyId)
- [ ] Update policy search to load from MongoDB per company (with caching)
- [ ] Update Pydantic schemas for auth/company/chat/import
- [ ] Add env vars: MONGODB_URI, JWT_SECRET, JWT_EXP_MINUTES

## Frontend (Next.js)
- [ ] Add auth pages: /login, /logout
- [ ] Add HR dashboard page: /hr (create company window + upload policies + import employees)
- [ ] Add Employee page: /employees (chat UI + role-based redirect)
- [ ] Implement role-based routing/layout using stored JWT
- [ ] Update chat calls to send Authorization header

## Verification
- [ ] Run backend + frontend
- [ ] Test flow:
  - [ ] HR login -> create company window -> upload policies -> import employees -> employee login
  - [ ] Employee asks questions -> responses grounded in that company’s policies

