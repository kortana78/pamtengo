"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, AgentRun } from "@/lib/api";
import { Empty, ErrorBox, StatusBadge } from "@/components/ui";

export default function RunsPage() {
  const [items, setItems] = useState<AgentRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.runs({ page_size: "50" });
      setItems(res.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load runs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading agent runs…</p>;
  if (error) return <ErrorBox message={error} onRetry={load} />;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Agent runs</h1>
      <p className="text-sm text-slate-500">
        Every workflow execution is recorded with its steps, durations, inputs, outputs, and errors — the audit trail.
      </p>
      {items.length === 0 ? (
        <Empty title="No agent runs yet" hint="Qualify a lead to create the first run." />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="table">
            <thead><tr><th>Run</th><th>Lead</th><th>Type</th><th>Status</th><th>Started</th><th>Finished</th></tr></thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id}>
                  <td><Link className="text-brand-700 underline" href={`/runs/${r.id}`}>{r.id.slice(0, 8)}…</Link></td>
                  <td><Link className="text-brand-700 underline" href={`/leads/${r.lead_id}`}>{r.lead_id.slice(0, 8)}…</Link></td>
                  <td>{r.workflow_type}</td>
                  <td><StatusBadge status={r.status} /></td>
                  <td className="text-xs">{new Date(r.started_at).toLocaleString()}</td>
                  <td className="text-xs">{r.completed_at ? new Date(r.completed_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
