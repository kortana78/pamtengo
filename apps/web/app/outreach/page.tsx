"use client";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, Draft } from "@/lib/api";
import { Empty, ErrorBox, StatusBadge } from "@/components/ui";

function OutreachInner() {
  const params = useSearchParams();
  const [filter, setFilter] = useState(params.get("status") || "");
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [confirming, setConfirming] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.drafts({ ...(filter ? { status: filter } : {}), page_size: "50" });
      setDrafts(res.items);
      if (res.items.length && !selectedId) {
        setSelectedId(res.items[0].id);
        setSubject(res.items[0].subject);
        setBody(res.items[0].body);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load drafts");
    } finally {
      setLoading(false);
    }
  }, [filter, selectedId]);

  useEffect(() => {
    load();
  }, [load]);

  const selected = drafts.find((d) => d.id === selectedId) || null;
  const pick = (d: Draft) => {
    setSelectedId(d.id);
    setSubject(d.subject);
    setBody(d.body);
    setConfirming(false);
    setNotice(null);
  };

  const act = async (fn: () => Promise<unknown>, msg: string) => {
    setNotice(null);
    try {
      await fn();
      setNotice(msg);
      setConfirming(false);
      await load();
    } catch (e) {
      setNotice(e instanceof Error ? `Action failed: ${e.message}` : "Action failed");
    }
  };

  const dirty = selected && (subject !== selected.subject || body !== selected.body);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Outreach review</h1>
      <p className="text-sm text-slate-500">
        Human approval is required before any mock send. The agent drafts — a person decides.
      </p>
      <div className="card flex gap-2">
        <select className="input max-w-[220px]" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter drafts by status">
          <option value="">All statuses</option>
          {["draft", "approved", "rejected", "sent"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>
      {notice && <div className="card text-sm" role="status">{notice}</div>}
      {loading ? (
        <p className="text-sm text-slate-500">Loading drafts…</p>
      ) : error ? (
        <ErrorBox message={error} onRetry={load} />
      ) : drafts.length === 0 ? (
        <Empty title="No drafts" hint="Generate an outreach draft from a lead detail page." />
      ) : (
        <div className="grid gap-4 md:grid-cols-[280px_1fr]">
          <ul className="space-y-2">
            {drafts.map((d) => (
              <li key={d.id}>
                <button
                  onClick={() => pick(d)}
                  className={`w-full rounded-lg border p-3 text-left text-sm ${d.id === selectedId ? "border-brand-600 bg-brand-50" : "border-slate-200 bg-white"}`}
                >
                  <div className="flex items-center gap-2">
                    <span className="truncate font-medium">{d.subject}</span>
                  </div>
                  <div className="mt-1"><StatusBadge status={d.status} /></div>
                </button>
              </li>
            ))}
          </ul>
          {selected && (
            <div className="card space-y-3">
              <div className="flex items-center gap-2">
                <StatusBadge status={selected.status} />
                {selected.approved_by && (
                  <span className="text-xs text-slate-500">
                    approved by {selected.approved_by} at {selected.approved_at ? new Date(selected.approved_at).toLocaleString() : "—"}
                  </span>
                )}
              </div>
              <div>
                <label className="label" htmlFor="or-subject">Subject (editable)</label>
                <input id="or-subject" className="input" value={subject} onChange={(e) => setSubject(e.target.value)} disabled={selected.status === "sent"} />
              </div>
              <div>
                <label className="label" htmlFor="or-body">Body (editable)</label>
                <textarea id="or-body" className="input min-h-[220px]" value={body} onChange={(e) => setBody(e.target.value)} disabled={selected.status === "sent"} />
              </div>
              <div>
                <h3 className="text-sm font-semibold">Supporting evidence</h3>
                {selected.evidence.length === 0 ? (
                  <p className="text-sm text-slate-500">No evidence cited.</p>
                ) : (
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-600">
                    {selected.evidence.map((e, i) => (
                      <li key={i} className="font-mono text-xs">{e}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  className="btn-secondary"
                  disabled={!dirty || selected.status === "sent"}
                  onClick={() => act(() => api.editDraft(selected.id, { subject, body }), "Draft saved.")}
                >
                  Save edits
                </button>
                <button
                  className="btn-primary"
                  disabled={selected.status === "sent" || selected.status === "approved"}
                  onClick={() => act(() => api.approveDraft(selected.id), "Draft approved.")}
                >
                  Approve
                </button>
                <button
                  className="btn-secondary"
                  disabled={selected.status === "sent"}
                  onClick={() => act(() => api.rejectDraft(selected.id), "Draft rejected.")}
                >
                  Reject
                </button>
                {!confirming ? (
                  <button
                    className="btn-danger"
                    disabled={selected.status !== "approved"}
                    title={selected.status !== "approved" ? "Approve the draft first" : "Simulate sending (mock provider)"}
                    onClick={() => setConfirming(true)}
                  >
                    Mock send…
                  </button>
                ) : (
                  <span className="flex items-center gap-2 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm">
                    Confirm mock send? No real email is delivered.
                    <button
                      className="btn-danger"
                      onClick={() =>
                        act(
                          () => api.sendDraft(selected.id, true, `ui:${selected.id}:${Date.now()}`),
                          "Mock send recorded."
                        )
                      }
                    >
                      Yes, send (mock)
                    </button>
                    <button className="btn-secondary" onClick={() => setConfirming(false)}>Cancel</button>
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function OutreachPage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
      <OutreachInner />
    </Suspense>
  );
}
