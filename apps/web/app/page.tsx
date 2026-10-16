"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, Overview } from "@/lib/api";
import { Empty, ErrorBox, StatusBadge } from "@/components/ui";

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.overview());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load overview");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading overview…</p>;
  if (error) return <ErrorBox message={error} onRetry={load} />;
  if (!data) return <Empty title="No data yet" hint="Import leads to get started." />;

  const cards = [
    { label: "Total leads", value: data.total_leads, href: "/leads" },
    { label: "Qualified leads", value: data.qualified_leads, href: "/leads?status=qualified" },
    { label: "Drafts awaiting approval", value: data.drafts_awaiting_approval, href: "/outreach?status=draft" },
    { label: "Mock emails sent", value: data.emails_mock_sent, href: "/outreach?status=sent" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Sales overview</h1>
        <p className="text-sm text-slate-500">
          Evidence-backed pipeline for Malawi &amp; AfCFTA markets. All figures below are fictional demo data.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {cards.map((c) => (
          <Link key={c.label} href={c.href} className="card hover:border-brand-600">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{c.label}</p>
            <p className="mt-1 text-3xl font-bold">{c.value}</p>
          </Link>
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card">
          <h2 className="font-semibold">Leads by status</h2>
          <div className="mt-2 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.leads_by_status}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="status" fontSize={12} />
                <YAxis allowDecimals={false} fontSize={12} />
                <Tooltip />
                <Bar dataKey="count" fill="#0e7c4a" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card">
          <h2 className="font-semibold">Leads by country</h2>
          <div className="mt-2 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.leads_by_country} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" allowDecimals={false} fontSize={12} />
                <YAxis type="category" dataKey="country" width={110} fontSize={12} />
                <Tooltip />
                <Bar dataKey="count" fill="#0b633c" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      <div className="card">
        <h2 className="font-semibold">Recent agent runs</h2>
        {data.recent_runs.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No agent runs yet. Qualify a lead to see the audit trail.</p>
        ) : (
          <table className="table mt-2">
            <thead>
              <tr>
                <th>Run</th>
                <th>Type</th>
                <th>Status</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_runs.map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link className="text-brand-700 underline" href={`/runs/${r.id}`}>
                      {r.id.slice(0, 8)}…
                    </Link>
                  </td>
                  <td>{r.workflow_type}</td>
                  <td>
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="text-xs">{new Date(r.started_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <details className="card text-sm">
        <summary className="cursor-pointer font-semibold">How are these metrics calculated?</summary>
        <p className="mt-2 text-slate-600">{data.how_calculated}</p>
      </details>
    </div>
  );
}
