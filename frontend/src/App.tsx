import { useEffect, useEffectEvent, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { Activity, Bot, Boxes, CheckSquare, CircuitBoard, FolderKanban, PanelLeftClose, PanelLeftOpen, Radio, Settings } from "lucide-react";
import { api, ApiError } from "./api";
import { EventClient, type ConnectionState } from "./events";
import type { RuntimeEvent } from "./contracts";
import { AgentsPage, DashboardPage, EventsPage, ProjectPage, ProjectsPage, ProvidersPage, RunPage, ApprovalsPage, SettingsPage } from "./pages";

const maxEvents = 500;

export type AppState = {
  events: RuntimeEvent[];
  connection: ConnectionState;
  apiError: ApiError | null;
  refresh: () => void;
};

const nav = [
  ["/", "Dashboard", CircuitBoard],
  ["/projects", "Projects", FolderKanban],
  ["/agents", "Agents", Bot],
  ["/approvals", "Approvals", CheckSquare],
  ["/providers", "Providers", Boxes],
  ["/events", "Events", Activity],
  ["/settings", "Settings", Settings],
] as const;

export function App() {
  const [events, setEvents] = useState<RuntimeEvent[]>([]);
  const [connection, setConnection] = useState<ConnectionState>("disconnected");
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const receiveEvent = useEffectEvent((event: RuntimeEvent) => {
    setEvents((previous) => [event, ...previous.filter((item) => item.event_id !== event.event_id)].slice(0, maxEvents));
  });
  const refresh = useEffectEvent(() => {
    api.events().then((items) => setEvents(items.reverse().slice(0, maxEvents))).catch((error: unknown) => {
      if (error instanceof ApiError) setApiError(error);
    });
  });

  useEffect(() => {
    refresh();
    const client = new EventClient(receiveEvent, setConnection);
    client.connect();
    return () => client.disconnect();
  }, [receiveEvent, refresh]);

  const state: AppState = { events, connection, apiError, refresh };
  return (
    <div className={`app-shell ${sidebarOpen ? "sidebar-open" : ""}`}>
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand"><span className="brand-mark">AG</span><span>AgentGraph <b>OS</b></span></div>
        <nav>{nav.map(([to, label, Icon]) => <NavLink end={to === "/"} to={to} key={to}><Icon size={17} /><span>{label}</span></NavLink>)}</nav>
        <button className="sidebar-toggle" onClick={() => setSidebarOpen(false)} aria-label="Collapse navigation"><PanelLeftClose size={18} /></button>
      </aside>
      <main>
        <header className="topbar">
          <button className="icon-button mobile-menu" onClick={() => setSidebarOpen((open) => !open)} aria-label="Toggle navigation"><PanelLeftOpen size={18} /></button>
          <div><span className="eyebrow">LOCAL CONTROL PLANE</span><h1>Agent workspace</h1></div>
          <div className={`connection ${connection}`}><Radio size={14} /> Events: {connection}</div>
        </header>
        {apiError && <div className="banner error"><b>{apiError.code}</b><span>{apiError.message}</span><button onClick={() => { setApiError(null); refresh(); }}>Retry</button></div>}
        <Routes>
          <Route path="/" element={<DashboardPage state={state} />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectPage state={state} />} />
          <Route path="/agents" element={<AgentsPage state={state} />} />
          <Route path="/agents/:agentId" element={<AgentsPage state={state} />} />
          <Route path="/runs/:runId" element={<RunPage state={state} />} />
          <Route path="/approvals" element={<ApprovalsPage state={state} />} />
          <Route path="/providers" element={<ProvidersPage />} />
          <Route path="/events" element={<EventsPage state={state} />} />
          <Route path="/settings" element={<SettingsPage state={state} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer><span>API is independent from the event stream.</span><span className={`connection ${connection}`}><Radio size={12} /> {connection}</span></footer>
    </div>
  );
}
