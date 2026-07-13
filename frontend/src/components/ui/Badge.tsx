type Tone = "success" | "error" | "pending" | "neutral" | "info";

const toneClasses: Record<Tone, string> = {
  success:
    "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/30",
  error:
    "bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/30",
  pending:
    "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/30",
  neutral:
    "bg-gray-100 text-gray-700 ring-gray-500/20 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-600/40",
  info: "bg-indigo-50 text-indigo-700 ring-indigo-600/20 dark:bg-indigo-500/10 dark:text-indigo-400 dark:ring-indigo-500/30",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${toneClasses[tone]}`}
    >
      {children}
    </span>
  );
}

const RUN_STATUS_TONE: Record<string, Tone> = {
  SUCCESS: "success",
  FAILURE: "error",
  CANCELED: "error",
  STARTED: "info",
  STARTING: "pending",
  QUEUED: "pending",
};

export function RunStatusBadge({ status }: { status: string }) {
  return <Badge tone={RUN_STATUS_TONE[status] ?? "neutral"}>{status}</Badge>;
}
