import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { apiPost } from "../api/client";
import type { QueryResponse } from "../api/types";
import { JsonTable } from "../components/JsonTable";
import { PageHeader } from "../components/PageHeader";
import { SchemaBrowser } from "../components/SchemaBrowser";
import { Card, CardBody, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Textarea } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { ErrorBanner } from "../components/ui/Feedback";

export function QueryPage() {
  const [sql, setSql] = useState("SELECT * FROM iceberg.marts.curated_events LIMIT 10");
  const mutation = useMutation({
    mutationFn: (sql: string) => apiPost<QueryResponse>("/trino/query", { sql }),
  });

  const runSql = (query: string) => {
    setSql(query);
    mutation.mutate(query);
  };

  const previewTable = (schema: string, table: string) => {
    runSql(`SELECT * FROM iceberg.${schema}.${table} LIMIT 50`);
  };

  return (
    <div>
      <PageHeader
        title="SQL Query Runner"
        description="Read-only queries against the Iceberg lakehouse via Trino."
      />

      <div className="grid grid-cols-4 gap-6">
        <Card className="col-span-1 h-fit">
          <CardHeader title="Schemas" />
          <CardBody>
            <SchemaBrowser onPreview={previewTable} />
          </CardBody>
        </Card>

        <div className="col-span-3">
          <Card>
            <CardHeader
              title="Query"
              actions={
                <Button onClick={() => mutation.mutate(sql)} loading={mutation.isPending}>
                  <Play className="h-4 w-4" />
                  Run
                </Button>
              }
            />
            <CardBody>
              <Textarea
                value={sql}
                onChange={(e) => setSql(e.target.value)}
                rows={5}
                spellCheck={false}
                onKeyDown={(e) => {
                  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") mutation.mutate(sql);
                }}
              />
              <p className="mt-1.5 text-xs text-gray-400 dark:text-slate-500">
                Only SELECT / WITH / SHOW / DESCRIBE / EXPLAIN statements are allowed. Press
                ⌘/Ctrl+Enter to run, or click a table on the left to preview it.
              </p>
            </CardBody>
          </Card>

          {mutation.isError && (
            <div className="mt-4">
              <ErrorBanner message={(mutation.error as Error).message} />
            </div>
          )}

          {mutation.data && (
            <Card className="mt-4">
              <CardHeader
                title="Results"
                actions={
                  <div className="flex items-center gap-2">
                    <Badge tone="info">{mutation.data.row_count} row(s)</Badge>
                    {mutation.data.truncated && <Badge tone="pending">truncated</Badge>}
                  </div>
                }
              />
              <CardBody>
                <JsonTable columns={mutation.data.columns} rows={mutation.data.rows} />
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
