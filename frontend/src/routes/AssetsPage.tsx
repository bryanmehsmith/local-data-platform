import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { PlayCircle } from "lucide-react";
import { apiGet, apiPost } from "../api/client";
import type { DagsterAsset, MaterializeResponse, RunStatus } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { RunStatusBadge } from "../components/ui/Badge";
import { Spinner, EmptyState } from "../components/ui/Feedback";

export function AssetsPage() {
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeAssetKey, setActiveAssetKey] = useState<string | null>(null);

  const assetsQuery = useQuery({
    queryKey: ["assets"],
    queryFn: () => apiGet<DagsterAsset[]>("/dagster/assets"),
  });

  const materializeMutation = useMutation({
    mutationFn: (assetKey: string) =>
      apiPost<MaterializeResponse>(`/dagster/assets/${assetKey}/materialize`, {}),
    onMutate: (assetKey) => setActiveAssetKey(assetKey),
    onSuccess: (data) => setActiveRunId(data.run_id),
  });

  const runQuery = useQuery({
    queryKey: ["run", activeRunId],
    queryFn: () => apiGet<RunStatus>(`/dagster/runs/${activeRunId}`),
    enabled: !!activeRunId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "SUCCESS" || status === "FAILURE" ? false : 2000;
    },
  });

  const isRunning = (assetKey: string) =>
    materializeMutation.isPending && activeAssetKey === assetKey;

  return (
    <div>
      <PageHeader
        title="Dagster Assets"
        description="Inspect and materialize assets in the batch/streaming/AI pipeline."
        actions={
          activeRunId &&
          runQuery.data && (
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              Run {activeRunId.slice(0, 8)}
              <RunStatusBadge status={runQuery.data.status} />
            </div>
          )
        }
      />

      <Card>
        {assetsQuery.isLoading ? (
          <div className="px-5">
            <Spinner label="Loading assets..." />
          </div>
        ) : !assetsQuery.data?.length ? (
          <div className="px-5">
            <EmptyState message="No assets found." />
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-slate-800">
            {assetsQuery.data.map((asset) => (
              <div key={asset.key} className="flex items-start justify-between gap-4 px-5 py-3.5">
                <div className="min-w-0">
                  <p className="font-mono text-sm font-medium text-gray-900 dark:text-slate-100">
                    {asset.key}
                  </p>
                  {asset.description && (
                    <p className="mt-0.5 line-clamp-2 text-xs text-gray-500 dark:text-slate-400">
                      {asset.description.split("\n")[0]}
                    </p>
                  )}
                </div>
                <Button
                  variant="secondary"
                  onClick={() => materializeMutation.mutate(asset.key)}
                  loading={isRunning(asset.key)}
                  className="flex-shrink-0"
                >
                  <PlayCircle className="h-4 w-4" />
                  Materialize
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
