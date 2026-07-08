import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { apiGet } from "../api/client";
import type { ServiceStatus } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { Card, CardBody } from "../components/ui/Card";
import { Spinner } from "../components/ui/Feedback";

const CATEGORY_LABELS: Record<string, string> = {
  storage: "Storage",
  catalog: "Catalog",
  compute: "Compute",
  streaming: "Streaming",
  ai: "AI",
  bi: "BI / Docs",
  observability: "Observability",
};

const CATEGORY_ORDER = ["storage", "catalog", "compute", "streaming", "ai", "bi", "observability"];

export function ServicesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["services"],
    queryFn: () => apiGet<ServiceStatus[]>("/services"),
    refetchInterval: 15000,
  });

  const grouped = CATEGORY_ORDER.map((category) => ({
    category,
    services: data?.filter((s) => s.category === category) ?? [],
  })).filter((g) => g.services.length > 0);

  return (
    <div>
      <PageHeader
        title="Services"
        description="Every service in the platform, with a live health check and a link to its own UI."
      />

      {isLoading ? (
        <Spinner label="Checking services..." />
      ) : (
        <div className="space-y-6">
          {grouped.map(({ category, services }) => (
            <div key={category}>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-slate-500">
                {CATEGORY_LABELS[category] ?? category}
              </h3>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {services.map((svc) => (
                  <Card key={svc.key}>
                    <CardBody className="flex items-center justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-2">
                        <span
                          className={`h-2 w-2 flex-shrink-0 rounded-full ${
                            svc.status === "ok" ? "bg-emerald-500" : "bg-red-500"
                          }`}
                        />
                        <span className="truncate text-sm font-medium text-gray-900 dark:text-slate-100">
                          {svc.name}
                        </span>
                      </div>
                      <a
                        href={svc.external_url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex-shrink-0 text-gray-400 hover:text-indigo-500 dark:text-slate-500 dark:hover:text-indigo-400"
                        title={`Open ${svc.name}`}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </CardBody>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
