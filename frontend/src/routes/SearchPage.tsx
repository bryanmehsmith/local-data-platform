import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { SearchIcon } from "lucide-react";
import { apiPost } from "../api/client";
import type { SearchResult } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { Card, CardBody } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { EmptyState, ErrorBanner } from "../components/ui/Feedback";

export function SearchPage() {
  const [text, setText] = useState("");
  const [topK, setTopK] = useState(5);
  const mutation = useMutation({
    mutationFn: () => apiPost<{ results: SearchResult[] }>("/search/query", { text, top_k: topK }),
  });

  const search = () => {
    if (text.trim()) mutation.mutate();
  };

  return (
    <div>
      <PageHeader title="Vector Search" description="Run similarity search directly against Qdrant." />

      <Card>
        <CardBody className="flex items-center gap-2">
          <div className="relative flex-1">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              placeholder="Search the lakehouse..."
              className="pl-9"
            />
          </div>
          <Input
            type="number"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="w-20"
            min={1}
            max={50}
          />
          <Button onClick={search} loading={mutation.isPending}>
            Search
          </Button>
        </CardBody>
      </Card>

      {mutation.isError && (
        <div className="mt-4">
          <ErrorBanner message={(mutation.error as Error).message} />
        </div>
      )}

      {mutation.data && (
        <div className="mt-4 space-y-2">
          {mutation.data.results.length === 0 ? (
            <Card>
              <EmptyState message="No results." />
            </Card>
          ) : (
            mutation.data.results.map((r, i) => (
              <Card key={i}>
                <CardBody className="flex items-start justify-between gap-4">
                  <p className="text-sm text-gray-700 dark:text-slate-300">
                    {String(r.payload.text ?? JSON.stringify(r.payload))}
                  </p>
                  <Badge tone="info">{r.score.toFixed(3)}</Badge>
                </CardBody>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  );
}
