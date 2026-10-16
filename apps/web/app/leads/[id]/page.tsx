"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, LeadDetail, Activity } from "@/lib/api";
import { Empty, ErrorBox, ScoreBadge, StatusBadge } from "@/components/ui";

export default function LeadDetailPage({ params }: { params: { id: string } }) {
  const [detail, setDetail] = useState<LeadDetail | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await api.leadDetail(params.id);
      setDetail(d);
      setActivities(await api.activities(params.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load lead");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  const qualify = async () => {
    setBusy(true);
    setNotice(null);
    try {
      await api.qualify(params.id);
      setNotice("Qualification workflow completed. Trace recorded below.");
      await load();
    } catch (e) {
      setNotice(e instanceof Error ? `Qualify failed: ${e.message}` : "Qualify failed");
    } finally {
      setBusy(false);
    }
  };

  const draft = async () => {
    setBusy(true);
    setNotice(null);
    try {
      await api.draftOutreach(params.id);
      setNotice("Outreach draft generated. Review it under Outreach review.");
      await load();
    } catch (e) {
      setNotice(e instanceof Error ? `Draft failed: ${e.message}` : "Draft failed");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <p className="text-sm text-slate-500">Loading lead…</p>;
  if (error) return <ErrorBox message={error} onRetry={load} />;
  if (!detail) return <Empty title="Lead not found" />;

  const { lead, company } = detail;
  const co = (company || {}) as Record<string, string | null>;

  return (
    <div className="space-y-4">
      <Link href="/leads" className="text-sm text-brand-700 underline">← Back to leads</Link>
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-2xl font-bold">{lead.full_name}</h1>
        <StatusBadge status={lead.status} />
        <ScoreBadge score={lead.fit_score} />
      </div>
      {notice && <div className="card text-sm" role="status">{notice}</div>}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card">
          <h2 className="font-semibold">Contact &amp; company</h2>
          <dl className="mt-2 space-y-1 text-sm">
            <div><dt className="inline font-medium">Email: </dt><dd className="inline">{lead.email}</dd></div>
            <div><dt className="inline font-medium">Title: </dt><dd className="inline">{lead.job_title || "Unknown"}</dd></div>
            <div><dt className="inline font-medium">Company: </dt><dd className="inline">{lead.company_name || co.name || "—"}</dd></div>
            <div><dt className="inline font-medium">Country: </dt><dd className="inline">{lead.company_country || co.country || "Unknown"}</dd></div>
            <div><dt className="inline font-medium">Industry: </dt><dd className="inline">{lead.company_industry || co.industry || "Unknown"}</dd></div>
            <div><dt className="inline font-medium">Size: </dt><dd className="inline">{co.employee_range || "Unknown"}</dd></div>
            {co.description && <div><dt className="font-medium">About: </dt><dd className="text-slate-600">{co.description}</dd></div>}
          </dl>
          <p className="mt-3 text-xs text-slate-500">Demo record — all companies and contacts are fictional.</p>
        </div>
        <div className="card">
          <h2 className="font-semibold">Qualification</h2>
          {lead.fit_score === null ? (
            <p className="mt-2 text-sm text-slate-500">Not yet scored. Run the AI qualification workflow.</p>
          ) : (
            <div className="mt-2 text-sm">
              <p><span className="font-medium">Score:</span> {lead.fit_score}/100 (rule-based fit, not a conversion probability)</p>
              <p className="mt-1 text-slate-600">{lead.fit_explanation}</p>
            </div>
          )}
          <div className="mt-3 flex gap-2">
            <button className="btn-primary" disabled={busy} onClick={qualify}>
              {busy ? "Running…" : "Run AI qualification"}
            </button>
            <button className="btn-secondary" disabled={busy} onClick={draft}>
              Generate outreach draft
            </button>
          </div>
        </div>
      </div>
      <div className="card">
        <h2 className="font-semibold">Agent execution history</h2>
        {detail.agent_runs.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No runs yet.</p>
        ) : (
          <table className="table mt-2">
            <thead><tr><th>Run</th><th>Type</th><th>Status</th><th>Error</th><th>Started</th></tr></thead>
            <tbody>
              {detail.agent_runs.map((r) => (
                <tr key={r.id}>
                  <td><Link className="text-brand-700 underline" href={`/runs/${r.id}`}>{r.id.slice(0, 8)}…</Link></td>
                  <td>{r.workflow_type}</td>
                  <td><StatusBadge status={r.status} /></td>
                  <td className="max-w-[300px] truncate text-xs text-red-600">{r.error_message || "—"}</td>
                  <td className="text-xs">{new Date(r.started_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="card">
        <h2 className="font-semibold">Outreach drafts</h2>
        {detail.drafts.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No drafts yet.</p>
        ) : (
          <ul className="mt-2 space-y-2 text-sm">
            {detail.drafts.map((d) => (
              <li key={d.id} className="rounded-lg border border-slate-200 p-3">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{d.subject}</span>
                  <StatusBadge status={d.status} />
                </div>
                <p className="mt-1 line-clamp-2 text-slate-600">{d.body}</p>
                <Link className="text-brand-700 underline" href="/outreach">Open in outreach review →</Link>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="card">
        <h2 className="font-semibold">Activity timeline</h2>
        {activities.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No activity recorded.</p>
        ) : (
          <ol className="mt-2 space-y-2 text-sm">
            {activities.map((a) => (
              <li key={a.id} className="border-l-2 border-slate-200 pl-3">
                <p className="font-medium">{a.activity_type}</p>
                <p className="text-slate-600">{a.description}</p>
                <p className="text-xs text-slate-400">{new Date(a.created_at).toLocaleString()}</p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
