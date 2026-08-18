import { useEffect, useEffectEvent, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { Activity, Bot, Boxes, CheckSquare, CircuitBoard, Eye, FolderKanban, HelpCircle, PanelLeftClose, PanelLeftOpen, Radio, Server, Settings, ShieldCheck, Sparkles } from "lucide-react";
import { api, ApiError, onAuthenticationFailure, setCsrfToken } from "./api";
import { EventClient, type ConnectionState } from "./events";
import type { AuthSession, RuntimeEvent } from "./contracts";
import { AgentsPage, AuthenticationPage, DashboardPage, EventsPage, ProjectPage, ProjectsPage, ProvidersPage, RunPage, ApprovalsPage, SecurityPage, SettingsPage, VisionPage, LexiPage, NodesPage } from "./pages";
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
  return <LanguageProvider><AuthenticationBoundary /></LanguageProvider>;
}

function AuthenticationBoundary() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);
  const refreshSession = useEffectEvent(async () => {
    try {
      setSession(await api.session());
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) return;
      setCsrfToken(null);
      setSession(null);
    } finally {
      setLoading(false);
    }
  });
  const unauthenticate = useEffectEvent(() => {
    setCsrfToken(null);
    setSession(null);
    setLoading(false);
  });

  useEffect(() => {
    refreshSession();
    return onAuthenticationFailure(unauthenticate);
  }, [refreshSession, unauthenticate]);

  if (loading) return <div className="state"><Radio className="spin" /> Checking local session...</div>;
  if (!session) return <AuthenticationPage onAuthenticated={setSession} />;
  return <Workspace session={session} onSessionUpdated={setSession} onUnauthenticated={unauthenticate} />;
}

function Workspace({ session, onSessionUpdated, onUnauthenticated }: { session: AuthSession; onSessionUpdated: (session: AuthSession) => void; onUnauthenticated: () => void }) {
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
    ["/approvals", text.nav.approvals, CheckSquare], ["/providers", text.nav.providers, Boxes], ["/vision", text.nav.vision, Eye], ["/lexi", text.nav.lexi, Sparkles],
    ["/nodes", text.nav.nodes, Server], ["/events", text.nav.events, Activity], ["/security", "Security", ShieldCheck], ["/settings", text.nav.settings, Settings], ["/help", text.nav.help, HelpCircle],
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
          <Route path="/lexi" element={<LexiPage state={state} />} />
          <Route path="/nodes" element={<NodesPage />} />
          <Route path="/events" element={<EventsPage state={state} />} />
          <Route path="/security" element={<SecurityPage session={session} onSessionUpdated={onSessionUpdated} onUnauthenticated={onUnauthenticated} />} />
          <Route path="/settings" element={<SettingsPage state={state} />} />
          <Route path="/help" element={<HelpPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer><span>API is independent from the event stream.</span><span className={`connection ${connection}`}><Radio size={12} /> {connection}</span></footer>
    </div>
  );
}
