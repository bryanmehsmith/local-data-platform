// Template: drop scenario-specific pages here.
//
// Every *.tsx file in this directory is auto-discovered by the infra
// repo's frontend/src/routes-manifest.ts (via import.meta.glob) and
// registered into both the router and the sidebar nav — no changes to
// core frontend/ code required.
//
// Convention: default-export the page component, and named-export a
// `routeMeta` descriptor (path, label, icon, optional `end`).
//
// Copy this file, rename it, and replace the example content with your
// own. Delete it once you no longer need the example.
import { Sparkles } from "lucide-react";

export const routeMeta = {
  path: "/workload-example",
  label: "Workload Example",
  icon: Sparkles,
};

export default function ExamplePage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-slate-100">
          Workload Example
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">
          A page contributed by the workload repo, auto-registered into this app.
        </p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm text-gray-700 dark:text-slate-300">
          This page lives in <code>workload/frontend/src/routes/ExamplePage.tsx</code>, a
          separate git repo from this app's core code. It's built into the same frontend
          bundle and picked up by the sidebar automatically.
        </p>
      </div>
    </div>
  );
}
