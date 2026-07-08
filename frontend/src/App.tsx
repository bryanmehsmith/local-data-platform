import { Route, Routes } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { HomePage } from "./routes/HomePage";
import { QueryPage } from "./routes/QueryPage";
import { AssetsPage } from "./routes/AssetsPage";
import { ChatPage } from "./routes/ChatPage";
import { SearchPage } from "./routes/SearchPage";
import { ServicesPage } from "./routes/ServicesPage";
import { workloadRoutes } from "./routes-manifest";

export function App() {
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-slate-950">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl px-8 py-8">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/query" element={<QueryPage />} />
            <Route path="/assets" element={<AssetsPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/services" element={<ServicesPage />} />
            {workloadRoutes.map(({ path, Component }) => (
              <Route key={path} path={path} element={<Component />} />
            ))}
          </Routes>
        </div>
      </main>
    </div>
  );
}
