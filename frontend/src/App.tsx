import { useEffect, useEffectEvent, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { Activity, Bot, Boxes, CheckSquare, CircuitBoard, Eye, FolderKanban, HelpCircle, PanelLeftClose, PanelLeftOpen, Radio, Settings } from "lucide-react";
import { api, ApiError } from "./api";
import { EventClient, type ConnectionState } from "./events";
import type { RuntimeEvent } from "./contracts";
import { AgentsPage, DashboardPage, EventsPage, ProjectPage, ProjectsPage, ProvidersPage, RunPage, ApprovalsPage, SettingsPage, VisionPage } from "./pages";
import { HelpPage } from "./help";
import { LanguageProvider, useLanguage } from "./i18n";

const maxEvents = 500;

export type AppState = {
  events: RuntimeEvent[];
  connection: ConnectionState;
  apiError: ApiError | null;
  refresh: () => void;
};

export function App() {
  return <LanguageProvider><Workspace /></LanguageProvider>;
}

function Workspace() {
  const { locale, setLocale, text } = useLanguage();
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
  const nav = [
    ["/", text.nav.dashboard, CircuitBoard], ["/projects", text.nav.projects, FolderKanban], ["/agents", text.nav.agents, Bot],
    ["/approvals", text.nav.approvals, CheckSquare], ["/providers", text.nav.providers, Boxes], ["/vision", text.nav.vision, Eye],
    ["/events", text.nav.events, Activity], ["/settings", text.nav.settings, Settings], ["/help", text.nav.help, HelpCircle],
  ] as const;
  return (
    <div className={`app-shell ${sidebarOpen ? "sidebar-open" : ""}`}>
        <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand"><span className="brand-mark">AG</span><span>AgentGraph <b>OS</b></span></div>
        <nav>{nav.map(([to, label, Icon]) => <NavLink end={to === "/"} to={to} key={to}><Icon size={17} /><span>{label}</span></NavLink>)}</nav>
        <button className="sidebar-toggle" onClick={() => setSidebarOpen(false)} aria-label={text.shell.collapse}><PanelLeftClose size={18} /></button>
      </aside>
      <main>
        <header className="topbar">
          <button className="icon-button mobile-menu" onClick={() => setSidebarOpen((open) => !open)} aria-label={text.shell.toggle}><PanelLeftOpen size={18} /></button>
          <div><span className="eyebrow">{text.shell.eyebrow}</span><h1>{text.shell.workspace}</h1></div>
          <div className="topbar-actions"><div className={`connection ${connection}`}><Radio size={14} /> {text.shell.events}: {connection}</div><div className="language-switch" role="group" aria-label={text.shell.language}><button className={locale === "en" ? "active" : ""} onClick={() => setLocale("en")}>EN</button><button className={locale === "ru" ? "active" : ""} onClick={() => setLocale("ru")}>RU</button></div></div>
        </header>
        {apiError && <div className="banner error"><b>{apiError.code}</b><span>{apiError.message}</span><button onClick={() => { setApiError(null); refresh(); }}>{text.shell.retry}</button></div>}
        <Routes>
          <Route path="/" element={<DashboardPage state={state} />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectPage state={state} />} />
          <Route path="/agents" element={<AgentsPage state={state} />} />
          <Route path="/agents/:agentId" element={<AgentsPage state={state} />} />
          <Route path="/runs/:runId" element={<RunPage state={state} />} />
          <Route path="/approvals" element={<ApprovalsPage state={state} />} />
          <Route path="/providers" element={<ProvidersPage />} />
          <Route path="/vision" element={<VisionPage state={state} />} />
          <Route path="/events" element={<EventsPage state={state} />} />
          <Route path="/settings" element={<SettingsPage state={state} />} />
          <Route path="/help" element={<HelpPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer><span>API is independent from the event stream.</span><span className={`connection ${connection}`}><Radio size={12} /> {connection}</span></footer>
    </div>
  );
}
