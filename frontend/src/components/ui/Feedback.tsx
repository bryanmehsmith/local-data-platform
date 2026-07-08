import { Loader2, AlertTriangle, Inbox } from "lucide-react";

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-6 text-sm text-gray-500 dark:text-slate-400">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label ?? "Loading..."}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
      <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
      <span className="break-words">{message}</span>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-sm text-gray-400 dark:text-slate-500">
      <Inbox className="h-6 w-6" />
      {message}
    </div>
  );
}
