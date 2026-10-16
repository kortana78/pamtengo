"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, AgentRun, AgentStep } from "@/lib/api";
import { Empty, ErrorBox, StatusBadge } from "@/components/ui";

function redact(value: unknown): string {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return text.replace(/([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})/g, "***@***");
}

export default function RunDetailPage({ params }: { params: { id: string } }) {
  const [run, setRun] = useState<AgentRun | null>(null);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      setRun(await api.run(params.id));
      setSteps(await api.runSteps(params.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load run");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  if (loading) return <p className="text-sm text-slate-500">Loading run…</p>;
  if (error) return <ErrorBox message={error} onRetry={load} />;
  if (!run) return <Empty title="Run not found" />;

  const totalMs = steps.reduce((a, s) => a + (s.duration_ms || 0), 0);

  return (
    <div className="space-y-4">
      <Link href="/runs" className="text-sm text-brand-700 underline">← Back to runs</Link>
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-2xl font-bold">Run {run.id.slice(0, 8)}…</h1>
        <StatusBadge status={run.status} />
        <span className="text-sm text-slate-500">total step time {totalMs} ms</span>
      </div>
      {run.error_message && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
          <p className="font-semibold">Run failed</p>
          <p>{run.error_message}</p>
        </div>
      )}
      <div className="card">
        <h2 className="font-semibold">Workflow steps</h2>
        <ol className="mt-2 space-y-2">
          {steps.map((s, i) => (
            <li key={s.id} className="rounded-lg border border-slate-200 p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-slate-500">{i + 1}.</span>
                <span className="font-medium">{s.step_name}</span>
                <StatusBadge status={s.status} />
                <span className="ml-auto text-xs text-slate-500">{s.duration_ms ?? "—"} ms</span>
              </div>
              {s.input_summary && (
                <details className="mt-1"><summary className="cursor-pointer text-xs text-slate-500">input</summary>
                  <pre className="mt-1 overflow-x-auto rounded bg-slate-50 p-2 text-xs">{redact(s.input_summary)}</pre>
                </details>
              )}
              {s.output_summary && (
                <details className="mt-1"><summary className="cursor-pointer text-xs text-slate-500">output</summary>
                  <pre className="mt-1 overflow-x-auto rounded bg-slate-50 p-2 text-xs">{redact(s.output_summary)}</pre>
                </details>
              )}
            </li>
          ))}
        </ol>
      </div>
      <div className="card">
        <h2 className="font-semibold">Structured output (redacted)</h2>
        <pre className="mt-2 overflow-x-auto rounded bg-slate-50 p-3 text-xs">{redact(run.output || {})}</pre>
      </div>
    </div>
  );
}
