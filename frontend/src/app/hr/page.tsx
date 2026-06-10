"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:9000";

export default function HrDashboard() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [companyId, setCompanyId] = useState<string>("");
  const [companyName, setCompanyName] = useState<string>("");
  const [policiesJson, setPoliciesJson] = useState<string>("{\n  \"leave\": {}\n}");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const cId = localStorage.getItem("companyId");

    if (!t || role !== "hr_admin") {
      router.push("/login");
      return;
    }

    // setState only after we know we should stay on this page
    // eslint-disable-next-line react-hooks/rules-of-hooks
    setToken(t);
    if (cId) setCompanyId(cId);

  }, [router]);


  async function createOrEnsureCompany() {
    if (!token) return;
    if (!companyName.trim()) {
      setStatus("companyName is required");
      return;
    }

    const res = await fetch(`${BACKEND_URL}/api/hr/companies`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ companyName }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? data.error ?? "Failed to create company");

    setCompanyId(data.companyId);
    setStatus("Company window created/ensured.");
  }

  async function upsertPolicies() {

    if (!token) return;
    if (!companyId) {
      setStatus("Create company window first.");
      return;
    }

    let parsed: Record<string, unknown>;

    try {
      parsed = JSON.parse(policiesJson);
    } catch {
      setStatus("Policies JSON is invalid");
      return;
    }

    const res = await fetch(`${BACKEND_URL}/api/hr/companies/${companyId}/policies`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ policies: parsed }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? data.error ?? "Failed to upload policies");
    setStatus("Policies updated.");
  }

  async function importEmployees() {
    if (!token) return;
    if (!companyId) {
      setStatus("Create company window first.");
      return;
    }
    if (!importFile) {
      setStatus("Select CSV/XLSX file");
      return;
    }

    const form = new FormData();
    form.append("file", importFile);

    const res = await fetch(`${BACKEND_URL}/api/hr/companies/${companyId}/employees/import`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? data.error ?? "Import failed");

    setStatus(`Import done: created=${data.created ?? 0}, updated=${data.updated ?? 0}, skipped=${data.skipped ?? 0}`);
  }

  async function logout() {
    router.push("/logout");
  }

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="max-w-3xl mx-auto px-5 py-8 flex flex-col gap-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm uppercase tracking-widest text-slate-400">HR Studio</div>
            <div className="text-xl font-semibold">Company Window</div>
          </div>
          <button
            onClick={logout}
            className="text-sm px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white/5 hover:bg-white/10"
          >
            Logout
          </button>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-sm">Company name</label>
            <input
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              placeholder="e.g. TechNovance"
            />
          </div>

          <div className="text-sm text-slate-500">companyId: {companyId || "(none)"}</div>

          <div className="flex gap-2">
            <button onClick={createOrEnsureCompany} className="px-4 py-2 rounded-lg bg-slate-900 text-white">
              Create / Ensure
            </button>
            <button onClick={upsertPolicies} className="px-4 py-2 rounded-lg bg-slate-900 text-white">
              Save Policies
            </button>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-sm">Policies JSON (paste or upload text)</label>
            <textarea
              value={policiesJson}
              onChange={(e) => setPoliciesJson(e.target.value)}
              className="min-h-[200px] px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-sm">Import employees (CSV/XLSX)</label>
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={(e) => setImportFile(e.target.files?.[0] ?? null)}
              className="text-sm"
            />
            <button onClick={importEmployees} className="px-4 py-2 rounded-lg bg-slate-900 text-white">
              Import Employees
            </button>
          </div>

          {status && <div className="text-sm text-slate-700 dark:text-slate-200">{status}</div>}
        </div>

        <div className="text-xs text-slate-400">
          CSV columns expected: <b>email</b>, <b>fullName</b>, <b>password</b>.
        </div>
      </div>
    </div>
  );
}

