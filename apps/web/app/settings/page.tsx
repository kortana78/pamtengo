"use client";
import { useEffect, useState } from "react";
import { api, AiStatus, Icp } from "@/lib/api";
import { ErrorBox } from "@/components/ui";

export default function SettingsPage() {
  const [status, setStatus] = useState<AiStatus | null>(null);
  const [icps, setIcps] = useState<Icp[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", target_industries: "", target_countries: "", company_size_preferences: "" });

  const load = async () => {
    try {
      setStatus(await api.aiStatus());
      setIcps(await api.icp());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load settings");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setNotice(null);
    try {
      await api.saveIcp({
        name: form.name,
        target_industries: form.target_industries.split(",").map((s) => s.trim()).filter(Boolean),
        target_countries: form.target_countries.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean),
        company_size_preferences: form.company_size_preferences.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setNotice("Ideal customer profile saved. New qualifications will use it.");
      setForm({ name: "", target_industries: "", target_countries: "", company_size_preferences: "" });
      await load();
    } catch (ex) {
      setNotice(ex instanceof Error ? `Save failed: ${ex.message}` : "Save failed");
    }
  };

  if (error) return <ErrorBox message={error} onRetry={load} />;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Settings</h1>
      <div className="card">
        <h2 className="font-semibold">AI provider</h2>
        {status ? (
          <dl className="mt-2 space-y-1 text-sm">
            <div>
              <dt className="inline font-medium">Mode: </dt>
              <dd className={`inline rounded-full px-2 py-0.5 text-xs font-semibold ${status.mock_mode ? "bg-amber-100 text-amber-800" : "bg-green-100 text-green-800"}`}>
                {status.mock_mode ? "MOCK (deterministic, no API key)" : `LIVE (${status.active_provider})`}
              </dd>
            </div>
            <div><dt className="inline font-medium">Timeout: </dt><dd className="inline">{status.timeout_seconds}s</dd></div>
            <div><dt className="inline font-medium">Max retries: </dt><dd className="inline">{status.max_retries}</dd></div>
            <div><dt className="inline font-medium">Token budget: </dt><dd className="inline">{status.token_budget}</dd></div>
          </dl>
        ) : (
          <p className="text-sm text-slate-500">Loading…</p>
        )}
        <p className="mt-2 text-xs text-slate-500">
          Mock mode is the default: set AI_PROVIDER=openai_compatible and OPENAI_API_KEY to use a live model.
        </p>
      </div>
      <div className="card">
        <h2 className="font-semibold">Ideal customer profiles</h2>
        <ul className="mt-2 space-y-2 text-sm">
          {icps.map((p) => (
            <li key={p.id} className="rounded-lg border border-slate-200 p-3">
              <p className="font-medium">{p.name}</p>
              <p className="text-xs text-slate-500">
                Industries: {p.target_industries.join(", ") || "—"} · Countries: {p.target_countries.join(", ") || "—"} · Sizes: {p.company_size_preferences.join(", ") || "—"}
              </p>
            </li>
          ))}
        </ul>
        <form className="mt-4 grid gap-3 md:grid-cols-2" onSubmit={save}>
          <div className="md:col-span-2"><label className="label" htmlFor="icp-name">Profile name</label><input id="icp-name" className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required placeholder="e.g. AfCFTA agri-SME" /></div>
          <div><label className="label" htmlFor="icp-ind">Target industries (comma-separated)</label><input id="icp-ind" className="input" value={form.target_industries} onChange={(e) => setForm({ ...form, target_industries: e.target.value })} placeholder="agriculture, logistics" /></div>
          <div><label className="label" htmlFor="icp-ctry">Target countries (comma-separated)</label><input id="icp-ctry" className="input" value={form.target_countries} onChange={(e) => setForm({ ...form, target_countries: e.target.value })} placeholder="malawi, zambia" /></div>
          <div className="md:col-span-2"><label className="label" htmlFor="icp-size">Company sizes (comma-separated)</label><input id="icp-size" className="input" value={form.company_size_preferences} onChange={(e) => setForm({ ...form, company_size_preferences: e.target.value })} placeholder="11-50, 51-200" /></div>
          <div className="md:col-span-2"><button className="btn-primary" type="submit">Save profile</button></div>
        </form>
        {notice && <p className="mt-2 text-sm" role="status">{notice}</p>}
      </div>
      <div className="card text-sm">
        <h2 className="font-semibold">Development authentication</h2>
        <p className="mt-1 text-slate-600">
          This demo identifies the acting user with the <code>X-User-Email</code> header (default{" "}
          <code>admin@pamtengo.demo</code>). It is not production authentication — see the threat model before
          handling real data.
        </p>
      </div>
    </div>
  );
}
