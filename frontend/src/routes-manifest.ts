import type { ComponentType } from "react";
import type { LucideIcon } from "lucide-react";

export type WorkloadRouteMeta = {
  path: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
};

type WorkloadRouteModule = {
  default: ComponentType;
  routeMeta: WorkloadRouteMeta;
};

// Auto-discovers pages contributed by the workload repo (bind-mounted /
// present as a sibling checkout at build time) without core frontend/ code
// needing to know about them ahead of time. Each file must default-export
// its page component and named-export a `routeMeta` descriptor. Resolves to
// an empty object (no error) if workload/frontend/src/routes doesn't exist
// or is empty.
const workloadModules = import.meta.glob<WorkloadRouteModule>(
  "../../workload/frontend/src/routes/*.tsx",
  { eager: true },
);

export const workloadRoutes = Object.entries(workloadModules)
  .filter(([, mod]) => mod.default && mod.routeMeta)
  .map(([, mod]) => ({ ...mod.routeMeta, Component: mod.default }));
