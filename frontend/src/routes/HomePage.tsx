import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle } from "lucide-react";
import { apiGet } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { Card, CardBody } from "../components/ui/Card";
import { Spinner } from "../components/ui/Feedback";

const SERVICE_LABELS: Record<string, string> = {
  trino: "Trino",
  dagster: "Dagster",
  qdrant: "Qdrant",
  pipelines: "Pipelines",
};

export function HomePage() {
  const { data, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<Record<string, string>>("/health"),
    refetchInterval: 10000,
  });

  return (
    <div>
      <PageHeader
        title="Overview"
        description="Live health of the platform services this app depends on."
      />

      {isLoading ? (
        <Spinner label="Checking service health..." />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {data &&
            Object.entries(data).map(([service, status]) => {
              const ok = status === "ok";
              return (
                <Card key={service}>
                  <CardBody className="flex items-center gap-3">
                    {ok ? (
                      <CheckCircle2 className="h-8 w-8 flex-shrink-0 text-emerald-500" />
                    ) : (
                      <XCircle className="h-8 w-8 flex-shrink-0 text-red-500" />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-slate-100">
                        {SERVICE_LABELS[service] ?? service}
                      </p>
                      <p
                        className={`truncate text-xs ${
                          ok ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
                        }`}
                        title={status}
                      >
                        {ok ? "Healthy" : status}
                      </p>
                    </div>
                  </CardBody>
                </Card>
              );
            })}
        </div>
      )}

      <Card className="mt-6">
        <CardBody>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">
            Getting started
          </h3>
          <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-gray-500 dark:text-slate-400">
            <li>
              <strong className="text-gray-700 dark:text-slate-300">Query</strong> — run read-only
              SQL against the Iceberg lakehouse via Trino.
            </li>
            <li>
              <strong className="text-gray-700 dark:text-slate-300">Assets</strong> — inspect and
              materialize Dagster assets, and watch runs complete.
            </li>
            <li>
              <strong className="text-gray-700 dark:text-slate-300">Chat</strong> — ask questions
              answered by RAG or live text-to-SQL.
            </li>
            <li>
              <strong className="text-gray-700 dark:text-slate-300">Search</strong> — run vector
              similarity search directly against Qdrant.
            </li>
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
