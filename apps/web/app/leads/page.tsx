"use client";
import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, LeadItem } from "@/lib/api";
import { Empty, ErrorBox, ScoreBadge, StatusBadge } from "@/components/ui";

function LeadsInner() {
  const params = useSearchParams();
  const [q, setQ] = useState(params.get("q") || "");
  const [status, setStatus] = useState(params.get("status") || "");
  const [items, setItems] = useState<LeadItem[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [importResult, setImportResult] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.leads({
        ...(q ? { q } : {}),
        ...(status ? { status } : {}),
        page_size: "50",
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load leads");
    } finally {
      setLoading(false);
    }
  }, [q, status]);

  useEffect(() => {
    load();
  }, [load]);

  const onImport = async (file: File | undefined) => {
    if (!file) return;
    setImportResult(null);
    try {
      const r = await api.importCsv(file);
      setImportResult(
        `Imported ${r.created} lead(s), skipped ${r.skipped_duplicates} duplicate(s).` +
          (r.errors.length ? ` Issues: ${r.errors.join(" | ")}` : "")
      );
      load();
    } catch (e) {
      setImportResult(e instanceof Error ? `Import failed: ${e.message}` : "Import failed");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">Leads</h1>
        <div className="flex gap-2">
          <label className="btn-secondary cursor-pointer">
            Import CSV
            <input
              type="file"
              accept=".csv"
              className="hidden"
              aria-label="Import leads from CSV"
              onChange={(e) => onImport(e.target.files?.[0])}
            />
          </label>
          <button className="btn-primary" onClick={() => setShowNew((v) => !v)}>
            New lead
          </button>
        </div>
      </div>
      {showNew && <NewLeadForm onDone={() => { setShowNew(false); load(); }} />}
      <div className="card flex flex-wrap gap-2">
        <input
          className="input max-w-xs"
          placeholder="Search name, email, company…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search leads"
        />
        <select className="input max-w-[200px]" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
          <option value="">All statuses</option>
          {["new", "qualified", "unqualified", "contacted", "converted", "rejected"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <span className="ml-auto self-center text-sm text-slate-500">{total} lead(s)</span>
      </div>
      {importResult && <div className="card text-sm" role="status">{importResult}</div>}
      {loading ? (
        <p className="text-sm text-slate-500">Loading leads…</p>
      ) : error ? (
        <ErrorBox message={error} onRetry={load} />
      ) : items.length === 0 ? (
        <Empty title="No leads found" hint="Create a lead or import a CSV to get started." />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="table">
            <thead>
              <tr>
                <th>Contact</th>
                <th>Company</th>
                <th>Country</th>
                <th>Industry</th>
                <th>Status</th>
                <th>Fit</th>
              </tr>
            </thead>
            <tbody>
              {items.map((l) => (
                <tr key={l.id}>
                  <td>
                    <Link className="font-medium text-brand-700 underline" href={`/leads/${l.id}`}>
                      {l.full_name}
                    </Link>
                    <div className="text-xs text-slate-500">{l.email} · {l.job_title || "—"}</div>
                  </td>
                  <td>{l.company_name || "—"}</td>
                  <td>{l.company_country || "—"}</td>
                  <td>{l.company_industry || "—"}</td>
                  <td><StatusBadge status={l.status} /></td>
                  <td><ScoreBadge score={l.fit_score} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-slate-500">
        CSV columns: company_name, company_country, company_industry, company_size, full_name, job_title, email,
        source, description. Duplicates (same email + company) are skipped. Max 1 MB / 1000 rows.
      </p>
    </div>
  );
}

function NewLeadForm({ onDone }: { onDone: () => void }) {
  const [form, setForm] = useState({ company_name: "", full_name: "", email: "", job_title: "", company_country: "Malawi", company_industry: "agriculture" });
  const [err, setErr] = useState<string | null>(null);
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      await api.createLead(form);
      onDone();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Create failed");
    }
  };
  return (
    <form className="card grid gap-3 md:grid-cols-3" onSubmit={submit}>
      <div><label className="label" htmlFor="nl-company">Company</label><input id="nl-company" className="input" value={form.company_name} onChange={set("company_name")} required /></div>
      <div><label className="label" htmlFor="nl-name">Full name</label><input id="nl-name" className="input" value={form.full_name} onChange={set("full_name")} required /></div>
      <div><label className="label" htmlFor="nl-email">Email</label><input id="nl-email" className="input" type="email" value={form.email} onChange={set("email")} required /></div>
      <div><label className="label" htmlFor="nl-title">Job title</label><input id="nl-title" className="input" value={form.job_title} onChange={set("job_title")} /></div>
      <div><label className="label" htmlFor="nl-country">Country</label><input id="nl-country" className="input" value={form.company_country} onChange={set("company_country")} /></div>
      <div><label className="label" htmlFor="nl-industry">Industry</label><input id="nl-industry" className="input" value={form.company_industry} onChange={set("company_industry")} /></div>
      {err && <p className="text-sm text-red-600 md:col-span-3" role="alert">{err}</p>}
      <div className="md:col-span-3"><button className="btn-primary" type="submit">Create lead</button></div>
    </form>
  );
}

export default function LeadsPage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
      <LeadsInner />
    </Suspense>
  );
}
