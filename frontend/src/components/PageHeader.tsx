import { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-slate-100">{title}</h1>
        {description && (
          <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">{description}</p>
        )}
      </div>
      {actions}
    </div>
  );
}
