import { scoreColor } from "@/lib/api";

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    new: "bg-slate-200 text-slate-700",
    qualified: "bg-green-100 text-green-800",
    unqualified: "bg-red-100 text-red-800",
    contacted: "bg-blue-100 text-blue-800",
    converted: "bg-emerald-100 text-emerald-800",
    rejected: "bg-zinc-200 text-zinc-600",
    draft: "bg-amber-100 text-amber-800",
    approved: "bg-green-100 text-green-800",
    sent: "bg-blue-100 text-blue-800",
    running: "bg-amber-100 text-amber-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${map[status] || "bg-slate-200"}`}>
      {status}
    </span>
  );
}

export function ScoreBadge({ score }: { score: number | null }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${scoreColor(score)}`}>
      {score === null || score === undefined ? "not scored" : `${score}/100`}
    </span>
  );
}

export function Empty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
      <p className="font-medium">{title}</p>
      {hint && <p className="mt-1 text-sm text-slate-500">{hint}</p>}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
      <p className="font-semibold">Something went wrong</p>
      <p className="mt-1">{message}</p>
      {onRetry && (
        <button className="btn-secondary mt-3" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
