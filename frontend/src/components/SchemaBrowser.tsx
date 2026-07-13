import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, ChevronDown, Table2, Play } from "lucide-react";
import { apiGet } from "../api/client";
import type { ColumnInfo, TableList } from "../api/types";
import { Spinner, ErrorBanner } from "./ui/Feedback";

function TableRow({
  schema,
  table,
  onPreview,
}: {
  schema: string;
  table: string;
  onPreview: (schema: string, table: string) => void;
}) {
  const [open, setOpen] = useState(false);

  const columnsQuery = useQuery({
    queryKey: ["columns", schema, table],
    queryFn: () => apiGet<ColumnInfo[]>(`/trino/tables/${schema}/${table}/columns`),
    enabled: open,
  });

  return (
    <div>
      <div className="group flex items-center justify-between gap-1 rounded-md px-2 py-1 hover:bg-gray-100 dark:hover:bg-slate-800">
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex min-w-0 flex-1 items-center gap-1.5 text-left text-sm text-gray-700 dark:text-slate-300"
        >
          {open ? (
            <ChevronDown className="h-3.5 w-3.5 flex-shrink-0 text-gray-400" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 flex-shrink-0 text-gray-400" />
          )}
          <Table2 className="h-3.5 w-3.5 flex-shrink-0 text-gray-400" />
          <span className="truncate font-mono text-[13px]">{table}</span>
        </button>
        <button
          onClick={() => onPreview(schema, table)}
          className="flex-shrink-0 rounded p-1 text-gray-400 opacity-0 hover:bg-gray-200 hover:text-indigo-600 group-hover:opacity-100 dark:hover:bg-slate-700 dark:hover:text-indigo-400"
          title={`Preview ${schema}.${table}`}
        >
          <Play className="h-3 w-3" />
        </button>
      </div>
      {open && (
        <div className="ml-8 border-l border-gray-200 pl-2 dark:border-slate-800">
          {columnsQuery.isLoading && (
            <p className="py-1 text-xs text-gray-400 dark:text-slate-500">Loading columns...</p>
          )}
          {columnsQuery.data?.map((col) => (
            <div key={col.name} className="flex items-baseline justify-between gap-2 py-0.5">
              <span className="truncate font-mono text-xs text-gray-600 dark:text-slate-400">
                {col.name}
              </span>
              <span className="flex-shrink-0 font-mono text-[11px] text-gray-400 dark:text-slate-500">
                {col.type}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function SchemaBrowser({
  onPreview,
}: {
  onPreview: (schema: string, table: string) => void;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(["marts"]));

  const tablesQuery = useQuery({
    queryKey: ["tables"],
    queryFn: () => apiGet<TableList>("/trino/tables"),
  });

  const toggle = (schema: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(schema)) {
        next.delete(schema);
      } else {
        next.add(schema);
      }
      return next;
    });
  };

  if (tablesQuery.isLoading) return <Spinner label="Loading schemas..." />;
  if (tablesQuery.isError) return <ErrorBanner message={(tablesQuery.error as Error).message} />;

  return (
    <div className="space-y-1">
      {Object.entries(tablesQuery.data ?? {}).map(([schema, tables]) => (
        <div key={schema}>
          <button
            onClick={() => toggle(schema)}
            className="flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-left text-sm font-semibold text-gray-800 hover:bg-gray-100 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {expanded.has(schema) ? (
              <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-gray-400" />
            )}
            {schema}
            <span className="ml-auto text-xs font-normal text-gray-400 dark:text-slate-500">
              {tables.length}
            </span>
          </button>
          {expanded.has(schema) && (
            <div className="ml-2">
              {tables.map((table) => (
                <TableRow key={table} schema={schema} table={table} onPreview={onPreview} />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
