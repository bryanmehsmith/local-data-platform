import { NavLink } from "react-router-dom";
import { Database, LayoutGrid, MessageSquare, Search, Home, Server } from "lucide-react";
import { workloadRoutes } from "../routes-manifest";

const NAV_ITEMS = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/query", label: "Query", icon: Database, end: false },
  { to: "/assets", label: "Assets", icon: LayoutGrid, end: false },
  { to: "/chat", label: "Chat", icon: MessageSquare, end: false },
  { to: "/search", label: "Search", icon: Search, end: false },
  { to: "/services", label: "Services", icon: Server, end: false },
  ...workloadRoutes.map(({ path, label, icon, end }) => ({ to: path, label, icon, end: end ?? false })),
];

export function Sidebar() {
  return (
    <aside className="flex h-screen w-56 flex-shrink-0 flex-col border-r border-slate-800 bg-slate-900 text-slate-200">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-indigo-500 text-sm font-bold text-white">
          L
        </div>
        <span className="text-sm font-semibold text-white">Local Data Platform</span>
      </div>
      <nav className="flex flex-1 flex-col gap-1 px-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-slate-800 text-white"
                  : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100"
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-slate-800 px-5 py-4 text-xs text-slate-500">
        Backend API v0.1
      </div>
    </aside>
  );
}
