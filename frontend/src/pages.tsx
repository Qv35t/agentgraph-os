import { type FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { addEdge, applyEdgeChanges, applyNodeChanges, Background, Controls, ReactFlow, type Connection, type Edge, type EdgeChange, type Node, type NodeChange, useEdgesState, useNodesState } from "@xyflow/react";
import { AlertTriangle, ArrowRight, Check, CircleStop, ExternalLink, FolderKanban, Play, Plus, RefreshCw, Trash2, Wrench, X } from "lucide-react";
import { api, ApiError } from "./api";
import type { Agent, Approval, GraphDefinition, MemoryKind, NodeInfo, Provider, Run, RunTreeNode, RuntimeEvent, SystemInfo, VisionAnalysis, VisionAsset, VisionFolder } from "./contracts";
import type { AppState } from "./App";
import { useLanguage } from "./i18n";

const russianLabels: Record<string, string> = {
  "SYSTEM OVERVIEW": "СОСТОЯНИЕ СИСТЕМЫ", "Control room": "Панель управления", "WORKSPACES": "РАБОЧИЕ ПРОСТРАНСТВА", "Projects": "Проекты",
  "PROJECT": "ПРОЕКТ", "AGENT REGISTRY": "РЕЕСТР АГЕНТОВ", "Agents": "Агенты", "RUN WORKSPACE": "РАБОЧЕЕ ПРОСТРАНСТВО RUN",
  "Approvals": "Подтверждения", "MODEL ROUTER": "МАРШРУТИЗАТОР МОДЕЛЕЙ", "Providers": "Провайдеры", "OBSERVABILITY": "НАБЛЮДАЕМОСТЬ", "Events": "События",
  "CLIENT PREFERENCES": "НАСТРОЙКИ КЛИЕНТА", "Settings": "Настройки", "NODES": "УЗЛЫ", "Nodes": "Узлы", "LOCAL MULTIMODAL": "ЛОКАЛЬНАЯ МУЛЬТИМОДАЛЬНОСТЬ", "Vision workspace": "Рабочее пространство Vision", "Team workflow": "Командный workflow", "Agent reference": "Ссылка на агента", "Run hierarchy": "Иерархия run",
};
const russianStatuses: Record<string, string> = { queued: "в очереди", running: "выполняется", succeeded: "завершено", failed: "ошибка", cancelled: "отменено", idle: "ожидание", available: "доступен", unavailable: "недоступен", disabled: "отключён", registered: "зарегистрирован", online: "в сети", offline: "не в сети", pending: "ожидает", approved: "подтверждено", rejected: "отклонено", connected: "подключено", reconnecting: "переподключение", disconnected: "отключено", completed: "завершено" };

function useResource<T>(load: () => Promise<T>, dependencies: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(() => {
    setLoading(true);
    load().then(setData).catch((reason: unknown) => setError(reason instanceof ApiError ? reason : new ApiError("UNKNOWN", "Unexpected response."))).finally(() => setLoading(false));
  // API request functions are stable module-level functions; dependencies identify the resource.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);
  useEffect(() => { refresh(); }, [refresh]);
  return { data, error, loading, refresh };
}

function Page({ title, eyebrow, children }: { title: string; eyebrow: string; children: React.ReactNode }) {
  const { locale } = useLanguage();
  return <section className="page"><div className="page-heading"><div><span className="eyebrow">{locale === "ru" ? russianLabels[eyebrow] ?? eyebrow : eyebrow}</span><h2>{locale === "ru" ? russianLabels[title] ?? title : title}</h2></div></div>{children}</section>;
}

function Loading() { return <div className="state"><RefreshCw className="spin" /> Loading live state...</div>; }
function Empty({ children }: { children: React.ReactNode }) { return <div className="state empty">{children}</div>; }
function ErrorState({ error, retry }: { error: ApiError; retry: () => void }) { return <div className="state error"><AlertTriangle /><div><b>{error.code}</b><p>{error.message}</p></div><button onClick={retry}>Retry</button></div>; }
function Status({ value }: { value: string }) { const { locale } = useLanguage(); return <span className={`status ${value}`}>{locale === "ru" ? russianStatuses[value] ?? value : value.replaceAll("_", " ")}</span>; }
function time(value: string | null) { const locale = localStorage.getItem("agentgraph.locale") === "ru" ? "ru-RU" : undefined; return value ? new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(value)) : "-"; }
function short(value: string | null) { return value ? value.slice(0, 8) : "-"; }

export function EventTimeline({ events, runId }: { events: RuntimeEvent[]; runId?: string }) {
  const list = runId ? events.filter((event) => event.run_id === runId) : events;
  if (!list.length) return <Empty>No recent events.</Empty>;
  return <ol className="timeline">{list.map((event) => <li key={event.event_id}><time>{time(event.timestamp)}</time><div><b>{event.type}</b><span>{event.agent_id ? `agent ${short(event.agent_id)}` : event.provider_id ?? "runtime"}</span>{Object.keys(event.payload).length > 0 && <details><summary>payload</summary><pre>{JSON.stringify(event.payload, null, 2)}</pre></details>}</div></li>)}</ol>;
}

export function DashboardPage({ state }: { state: AppState }) {
  const system = useResource(api.system);
  const agents = useResource(api.agents, [state.events.length]);
  const providers = useResource(api.providers);
  const approvals = useResource(api.approvals, [state.events]);
  const health = useResource(api.health);
  const nodes = useResource(api.nodes);
  const running = agents.data?.filter((agent) => agent.status === "running").length ?? 0;
  return <Page eyebrow="SYSTEM OVERVIEW" title="Control room">
    <div className="metrics">
      <Metric label="API" value={health.data?.status ?? "offline"} tone={health.error ? "danger" : "success"} />
      <Metric label="Remote control" value={system.data?.remote_control ? "enabled" : "restricted"} tone={system.data?.remote_control ? "success" : "warning"} />
      <Metric label="Providers" value={String(providers.data?.filter((item) => item.available).length ?? 0)} detail={`${providers.data?.length ?? 0} registered`} />
      <Metric label="Agents" value={String(agents.data?.length ?? 0)} detail={`${running} active`} />
      <Metric label="Approvals" value={String(approvals.data?.length ?? 0)} detail="pending" tone={approvals.data?.length ? "warning" : undefined} />
      <Metric label="Workers" value={String(nodes.data?.filter((node) => node.role === "worker" && node.status === "online").length ?? 0)} detail={`${nodes.data?.filter((node) => node.role === "worker").length ?? 0} registered`} />
    </div>
    {!system.loading && system.error && <div className="banner warning">Remote control is disabled or this browser identity is not authorized. Read-only health remains available.</div>}
    <div className="dashboard-grid"><Panel title="Live event feed" action={<Link to="/events">View all <ArrowRight size={14} /></Link>}><EventTimeline events={state.events.slice(0, 8)} /></Panel><Panel title="Provider state"><ProviderList providers={providers.data} loading={providers.loading} error={providers.error} retry={providers.refresh} compact /></Panel></div>
    <Panel title="Recent agents" action={<Link to="/agents">Manage agents <ArrowRight size={14} /></Link>}><AgentTable agents={agents.data} loading={agents.loading} error={agents.error} retry={agents.refresh} /></Panel>
  </Page>;
}

function Metric({ label, value, detail, tone }: { label: string; value: string; detail?: string; tone?: string }) { return <div className="metric"><span>{label}</span><strong className={tone}>{value}</strong>{detail && <small>{detail}</small>}</div>; }
function Panel({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) { return <section className="panel"><header><h3>{title}</h3>{action}</header>{children}</section>; }

export function ProjectsPage() {
  const projects = useResource(api.projects);
  return <Page eyebrow="WORKSPACES" title="Projects"><Resource result={projects}>{(items) => <div className="project-grid">{items.map((project) => <Link className="project-card" to={`/projects/${project.project_id}`} key={project.project_id}><FolderKanban /><div><strong>{project.name}</strong><code>{project.project_id}</code></div><ArrowRight /></Link>)}</div>}</Resource></Page>;
}

export function ProjectPage({ state }: { state: AppState }) {
  const { projectId = "" } = useParams();
  const project = useResource(() => api.project(projectId), [projectId]);
  const agents = useResource(api.agents);
  return <Page eyebrow="PROJECT" title={project.data?.name ?? "Project"}><Resource result={project}>{(item) => <><div className="project-identity"><span>PROJECT ID</span><code>{item.project_id}</code></div><Panel title="Agents"><AgentTable agents={agents.data} loading={agents.loading} error={agents.error} retry={agents.refresh} /></Panel><Panel title="Project activity"><EventTimeline events={state.events.filter((event) => event.project_id === item.project_id)} /></Panel></>}</Resource></Page>;
}

export function AgentsPage({ state }: { state: AppState }) {
  const { agentId } = useParams();
  const agents = useResource(api.agents, [state.events.length]);
  const selected = agents.data?.find((agent) => agent.id === agentId);
  return <Page eyebrow="AGENT REGISTRY" title={selected ? selected.name : "Agents"}>{agentId && selected ? <AgentDetail agent={selected} events={state.events} /> : <><AgentComposer onCreated={agents.refresh} /><Panel title="Available agents"><AgentTable agents={agents.data} loading={agents.loading} error={agents.error} retry={agents.refresh} /></Panel></>}</Page>;
}

function AgentTable({ agents, loading, error, retry }: { agents: Agent[] | null; loading: boolean; error: ApiError | null; retry: () => void }) {
  if (loading) return <Loading />; if (error) return <ErrorState error={error} retry={retry} />; if (!agents?.length) return <Empty>No agents available. Create one to start a local workflow.</Empty>;
  return <div className="table-wrap"><table><thead><tr><th>Agent</th><th>Status</th><th>Model route</th><th>Updated</th><th /></tr></thead><tbody>{agents.map((agent) => <tr key={agent.id}><td><b>{agent.name}</b><code>{short(agent.id)}</code></td><td><Status value={agent.status} /></td><td><code>{agent.model_ref}</code></td><td>{time(agent.updated_at)}</td><td><Link className="text-link" to={`/agents/${agent.id}`}>Open</Link></td></tr>)}</tbody></table></div>;
}

function AgentComposer({ onCreated }: { onCreated: () => void }) {
  const providers = useResource(api.providers); const availableAgents = useResource(api.agents); const [open, setOpen] = useState(false); const [name, setName] = useState(""); const [description, setDescription] = useState(""); const [modelRef, setModelRef] = useState("auto://default"); const [graph, setGraph] = useState<GraphDefinition>({ nodes: [{ id: "agent", type: "agent", label: "Agent", position: [80, 70] }], edges: [] }); const [error, setError] = useState<ApiError | null>(null); const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); setError(null); try { await api.createAgent({ name, description: description || null, model_ref: modelRef, graph_definition: graph }); setOpen(false); setName(""); setDescription(""); onCreated(); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("CREATE_FAILED", "Could not create agent.")); } finally { setSaving(false); } }
  const models = providers.data?.flatMap((provider) => provider.models.map((model) => `${provider.provider_id}://${model}`)) ?? [];
  return <section className="composer"><div><span className="eyebrow">NEW WORKFLOW</span><h3>Create an agent graph</h3><p>Graph layout is durable metadata. Runtime behavior remains defined by the backend.</p></div><button onClick={() => setOpen(true)}><Plus size={16} /> Create agent</button>{open && <div className="dialog-backdrop" role="presentation"><form className="dialog" onSubmit={submit} role="dialog" aria-modal="true" aria-label="Create agent"><header><h3>Create agent</h3><button className="icon-button" type="button" onClick={() => setOpen(false)} aria-label="Close"><X /></button></header><label>Name<input autoFocus required value={name} onChange={(event) => setName(event.target.value)} /></label><label>Description<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label><label>Model route<select value={modelRef} onChange={(event) => setModelRef(event.target.value)}><option value="auto://default">auto://default</option>{models.map((model) => <option key={model} value={model}>{model}</option>)}</select></label><GraphEditor value={graph} onChange={setGraph} agents={availableAgents.data ?? []} /><div className="dialog-actions"><button type="button" className="secondary" onClick={() => setOpen(false)}>Cancel</button><button disabled={saving}>{saving ? "Creating..." : "Create agent"}</button></div>{error && <p className="form-error">{error.code}: {error.message}</p>}</form></div>}</section>;
}

function GraphEditor({ value, onChange, agents = [], currentAgentId }: { value: GraphDefinition; onChange: (graph: GraphDefinition) => void; agents?: Agent[]; currentAgentId?: string }) {
  const { locale } = useLanguage();
  const seedNodes: Node[] = value.nodes.length ? value.nodes.map((node) => ({ id: node.id, type: node.type, position: { x: node.position[0], y: node.position[1] }, data: { label: node.label } })) : [{ id: "agent", position: { x: 80, y: 70 }, data: { label: "Agent" } }];
  const [nodes, setNodes] = useNodesState(seedNodes); const [edges, setEdges] = useEdgesState(value.edges);
  const sync = useCallback((nextNodes: Node[], nextEdges: Edge[]) => onChange({ version: value.version, runtime: value.runtime, nodes: nextNodes.map((node) => { const stored = value.nodes.find((item) => item.id === node.id); return { id: node.id, type: stored?.type ?? node.type ?? "agent", label: String(node.data.label ?? node.id), position: [node.position.x, node.position.y], agent_id: stored?.agent_id, instructions: stored?.instructions }; }), edges: nextEdges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target })) }), [onChange, value]);
  const onConnect = useCallback((connection: Connection) => setEdges((current) => { const next = addEdge(connection, current); sync(nodes, next); return next; }), [nodes, setEdges, sync]);
  const onNodeChanges = useCallback((changes: NodeChange[]) => setNodes((current) => { const next = applyNodeChanges(changes, current); sync(next, edges); return next; }), [edges, setNodes, sync]);
  const onEdgeChanges = useCallback((changes: EdgeChange[]) => setEdges((current) => { const next = applyEdgeChanges(changes, current); sync(nodes, next); return next; }), [nodes, setEdges, sync]);
  function addNode(type = "agent") { setNodes((current) => { const number = current.length + 1; const next = [...current, { id: `${type}-${number}`, type: type === "agent-ref" ? undefined : type, position: { x: 100 + current.length * 110, y: 150 }, data: { label: type === "agent-ref" ? `Worker ${number}` : type === "vision-analyze" ? "Vision Analyze" : `Agent ${number}` } }]; const semantic = type === "agent-ref" ? { ...value, nodes: [...value.nodes, { id: `${type}-${number}`, type, label: `Worker ${number}`, position: [100 + current.length * 110, 150] as [number, number] }], edges: value.edges } : null; if (semantic) onChange(semantic); else sync(next, edges); return next; }); }
  function setRuntime(runtime: GraphDefinition["runtime"]) { if (runtime === "team-v1") onChange({ version: 2, runtime, nodes: [], edges: [] }); else onChange({ version: 1, runtime, nodes: value.nodes, edges: value.edges }); }
  function updateWorker(nodeId: string, patch: Partial<GraphDefinition["nodes"][number]>) { onChange({ ...value, nodes: value.nodes.map((node) => node.id === nodeId ? { ...node, ...patch } : node) }); }
  const workers = value.nodes.filter((node) => node.type === "agent-ref");
  return <div className="graph-editor"><div className="graph-label">{locale === "ru" ? "Граф workflow" : "Workflow graph"} <span>{locale === "ru" ? "Перетаскивайте узлы и соединяйте их для сохранения структуры." : "Drag nodes or connect handles to save layout semantics."}</span><label>{locale === "ru" ? "Runtime" : "Runtime"}<select value={value.runtime ?? "model-v1"} onChange={(event) => setRuntime(event.target.value as GraphDefinition["runtime"])}><option value="model-v1">model-v1</option><option value="lexi-v1">lexi-v1</option><option value="team-v1">team-v1</option></select></label><button type="button" className="add-node" onClick={() => addNode(value.runtime === "team-v1" ? "agent-ref" : "agent")}><Plus size={13} /> {value.runtime === "team-v1" ? (locale === "ru" ? "Работник" : "Worker") : "Agent"}</button><button type="button" className="add-node" onClick={() => addNode("vision-analyze")} disabled={value.runtime === "team-v1"}><Plus size={13} /> Vision</button></div>{value.runtime === "team-v1" && <div className="worker-config"><b>{locale === "ru" ? "Ссылки на агентов" : "Agent references"}</b><p>{locale === "ru" ? "Команда запускает существующих агентов; сервер проверяет DAG и лимиты." : "A team runs existing agents; the server validates its DAG and limits."}</p>{workers.map((node) => <div key={node.id}><label>{node.label}<select value={node.agent_id ?? ""} onChange={(event) => updateWorker(node.id, { agent_id: event.target.value })}><option value="">{locale === "ru" ? "Выберите агента" : "Select an agent"}</option>{agents.filter((agent) => agent.id !== currentAgentId).map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}</select></label><label>{locale === "ru" ? "Инструкции" : "Instructions"}<textarea maxLength={4000} value={node.instructions ?? ""} onChange={(event) => updateWorker(node.id, { instructions: event.target.value || undefined })} /></label></div>)}</div>}<ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodeChanges} onEdgesChange={onEdgeChanges} onConnect={onConnect} fitView><Background gap={18} size={1} /><Controls showInteractive={false} /></ReactFlow></div>;
}

function AgentDetail({ agent, events }: { agent: Agent; events: RuntimeEvent[] }) {
  const runs = useResource(() => api.agentRuns(agent.id), [agent.id]); const availableAgents = useResource(api.agents); const navigate = useNavigate(); const [input, setInput] = useState(""); const [error, setError] = useState<ApiError | null>(null); const [starting, setStarting] = useState(false); const [graph, setGraph] = useState<GraphDefinition>(agent.graph_definition); const [savingGraph, setSavingGraph] = useState(false);
  useEffect(() => { setGraph(agent.graph_definition); }, [agent.id, agent.graph_definition]);
  async function start(event: FormEvent) { event.preventDefault(); setStarting(true); setError(null); try { const run = await api.startRun(agent.id, input); navigate(`/runs/${run.id}`); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("RUN_FAILED", "Could not start run.")); } finally { setStarting(false); } }
  async function saveGraph() { setSavingGraph(true); setError(null); try { await api.updateAgentGraph(agent.id, graph); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("GRAPH_SAVE_FAILED", "Could not save graph.")); } finally { setSavingGraph(false); } }
  return <div className="detail-grid"><section><Panel title="Run composer"><form className="run-form" onSubmit={start}><label>Task<textarea required value={input} onChange={(event) => setInput(event.target.value)} placeholder="Describe the task for this agent." /></label><div><span>Model route <code>{agent.model_ref}</code></span><button disabled={starting || agent.status === "running"}><Play size={16} /> {starting ? "Starting..." : "Start run"}</button></div>{agent.status === "running" && <p className="form-error">This agent already has an active run.</p>}{error && <p className="form-error">{error.code}: {error.message}</p>}</form></Panel><Panel title="Workflow graph"><GraphEditor key={agent.id} value={graph} onChange={setGraph} agents={availableAgents.data ?? []} currentAgentId={agent.id} /><div className="dialog-actions"><button onClick={saveGraph} disabled={savingGraph}>{savingGraph ? "Saving..." : "Save graph"}</button></div></Panel><Panel title="Run history"><Resource result={runs}>{(items) => items.length ? <div className="run-list">{items.map((run) => <Link to={`/runs/${run.id}`} key={run.id}><Status value={run.status} /><span>{run.input_text}</span><code>{short(run.id)}</code></Link>)}</div> : <Empty>No runs yet.</Empty>}</Resource></Panel></section><section><Panel title="Agent metadata"><dl className="metadata"><dt>Agent ID</dt><dd><code>{agent.id}</code></dd><dt>Status</dt><dd><Status value={agent.status} /></dd><dt>Model</dt><dd><code>{agent.model_ref}</code></dd><dt>Description</dt><dd>{agent.description ?? "No description"}</dd></dl></Panel><Panel title="Activity"><EventTimeline events={events} runId={undefined} /></Panel></section></div>;
}

export function RunPage({ state }: { state: AppState }) {
  const { runId = "" } = useParams(); const run = useResource(() => api.run(runId), [runId]); const tree = useResource(() => api.runTree(runId), [runId]); const [stopping, setStopping] = useState(false); const [error, setError] = useState<ApiError | null>(null);
  async function stop() { setStopping(true); setError(null); try { await api.stopRun(runId); run.refresh(); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("STOP_FAILED", "Could not stop run.")); } finally { setStopping(false); } }
  const matchingEventCount = state.events.filter((event) => event.run_id === runId).length;
  const refreshRun = run.refresh; const refreshTree = tree.refresh;
  const runStatus = run.data?.status;
  useEffect(() => { if (matchingEventCount > 0) { refreshRun(); refreshTree(); } }, [matchingEventCount, refreshRun, refreshTree]);
  useEffect(() => {
    if (!runStatus || !["queued", "running"].includes(runStatus)) return;
      const poll = window.setInterval(() => { refreshRun(); refreshTree(); }, 3_000);
    return () => window.clearInterval(poll);
  }, [runStatus, refreshRun, refreshTree]);
  return <Page eyebrow="RUN WORKSPACE" title={run.data ? `Run ${short(run.data.id)}` : "Run"}><Resource result={run}>{(item) => <><div className="run-header"><Status value={item.status} /><code>{item.provider_id ?? "provider pending"}/{item.model_id ?? "model pending"}</code>{["queued", "running"].includes(item.status) && <button className="danger" onClick={stop} disabled={stopping}><CircleStop size={16} /> {stopping ? "Stopping..." : "Stop run"}</button>}</div>{error && <div className="banner error">{error.code}: {error.message}</div>}<div className="run-workspace"><Panel title="Output"><div className="output"><p className="input-label">TASK</p><p>{item.input_text}</p><hr /><p className="input-label">RESULT</p>{item.output_text ? <pre>{item.output_text}</pre> : <p className="muted">{item.error ?? "Execution output will appear when the backend completes the run."}</p>}</div></Panel><Panel title="Event timeline"><EventTimeline events={state.events} runId={item.id} /></Panel></div>{tree.data && (tree.data.children.length > 0 || tree.data.node_id !== null) && <Panel title="Run hierarchy"><RunTree tree={tree.data} /></Panel>}<Panel title="Metadata inspector"><dl className="metadata grid"><dt>Run ID</dt><dd><code>{item.id}</code></dd><dt>Agent ID</dt><dd><Link to={`/agents/${item.agent_id}`}><code>{item.agent_id}</code></Link></dd><dt>Created</dt><dd>{new Date(item.created_at).toLocaleString()}</dd><dt>Started</dt><dd>{item.started_at ? new Date(item.started_at).toLocaleString() : "-"}</dd><dt>Finished</dt><dd>{item.finished_at ? new Date(item.finished_at).toLocaleString() : "-"}</dd><dt>Tokens</dt><dd>{item.total_tokens ?? "-"}</dd><dt>Latency</dt><dd>{item.latency_ms ? `${item.latency_ms} ms` : "-"}</dd></dl></Panel></>}</Resource></Page>;
}

function RunTree({ tree }: { tree: RunTreeNode }) { return <ul className="run-tree"><li><Status value={tree.run.status} /> <Link to={`/runs/${tree.run.id}`}>{tree.node_id ?? "Team run"}</Link>{tree.children.length > 0 && <ul>{tree.children.map((child) => <RunTree key={child.run.id} tree={child} />)}</ul>}</li></ul>; }

export function ApprovalsPage({ state }: { state: AppState }) {
  const approvals = useResource(api.approvals, [state.events]); const [error, setError] = useState<ApiError | null>(null);
  async function decide(approval: Approval, approved: boolean) { setError(null); try { await (approved ? api.approve(approval.approval_id) : api.reject(approval.approval_id)); approvals.refresh(); state.refresh(); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("APPROVAL_FAILED", "Could not submit the decision.")); } }
  return <Page eyebrow="HUMAN GATE" title="Approvals">{error && <div className="banner error">{error.code}: {error.message}</div>}<Resource result={approvals}>{(items) => items.length ? <div className="approval-list">{items.map((approval) => <article key={approval.approval_id} className="approval"><div><Status value={approval.status} /><h3>{approval.action}</h3><p>{approval.description}</p><dl><dt>Run</dt><dd><code>{approval.run_id ?? "not associated"}</code></dd><dt>Task</dt><dd><code>{approval.task_id ?? "not associated"}</code></dd><dt>Requested</dt><dd>{new Date(approval.created_at).toLocaleString()}</dd></dl></div><div className="approval-actions"><button className="secondary" onClick={() => decide(approval, false)}><X size={16} /> Reject</button><button onClick={() => decide(approval, true)}><Check size={16} /> Approve</button></div></article>)}</div> : <Empty>No pending approvals. Approval persistence is process-local and does not pause a run yet.</Empty>}</Resource></Page>;
}

export function ProvidersPage() { const providers = useResource(api.providers); return <Page eyebrow="MODEL ROUTER" title="Providers"><ProviderList providers={providers.data} loading={providers.loading} error={providers.error} retry={providers.refresh} /></Page>; }
export function NodesPage() {
  const nodes = useResource(api.nodes);
  const [error, setError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  async function action(node: NodeInfo, operation: "enable" | "disable" | "probe") {
    setBusy(`${operation}:${node.node_id}`); setError(null); setResult(null);
    try {
      if (operation === "enable") await api.enableNode(node.node_id);
      else if (operation === "disable") await api.disableNode(node.node_id);
      else { const probe = await api.probeNode(node.node_id); setResult(`Probe ${probe.task_id.slice(0, 8)} succeeded.`); }
      nodes.refresh();
    } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("NODE_ACTION_FAILED", "Node action failed.")); } finally { setBusy(null); }
  }
  return <Page eyebrow="NODES" title="Nodes">{error && <div className="banner error">{error.code}: {error.message}</div>}{result && <div className="banner">{result}</div>}<Resource result={nodes}>{(items) => items.length ? <div className="table-wrap"><table><thead><tr><th>Name</th><th>Role</th><th>Status</th><th>Platform</th><th>CPU / RAM</th><th>Last seen</th><th /></tr></thead><tbody>{items.map((node) => <tr key={node.node_id}><td><b>{node.name}</b><code>{short(node.node_id)}</code></td><td>{node.role}</td><td><Status value={node.status} /></td><td>{node.capabilities.platform} / {node.capabilities.architecture}<code>{node.capabilities.agentgraph_version}</code></td><td>{node.capabilities.resources.cpu_count} CPU / {node.capabilities.resources.memory_available_bytes ? `${Math.round(node.capabilities.resources.memory_available_bytes / 1_073_741_824)} GB free` : "-"}</td><td>{time(node.last_seen_at)}</td><td>{node.role === "worker" && <><button className="secondary" onClick={() => action(node, "probe")} disabled={busy !== null || !node.enabled || node.status !== "online"}>Probe</button><button className="secondary" onClick={() => action(node, node.enabled ? "disable" : "enable")} disabled={busy !== null}>{node.enabled ? "Disable" : "Enable"}</button></>}</td></tr>)}</tbody></table></div> : <Empty>No workers are enrolled. Distributed workers remain disabled unless explicitly configured.</Empty>}</Resource></Page>;
}
function ProviderList({ providers, loading, error, retry, compact = false }: { providers: Provider[] | null; loading: boolean; error: ApiError | null; retry: () => void; compact?: boolean }) { if (loading) return <Loading />; if (error) return <ErrorState error={error} retry={retry} />; if (!providers?.length) return <Empty>No providers discovered.</Empty>; return <div className={compact ? "provider-stack compact" : "provider-stack"}>{providers.map((provider) => <article className="provider" key={provider.provider_id}><div><h3>{provider.provider_id}</h3><div><Status value={provider.available ? "available" : provider.enabled ? "unavailable" : "disabled"} /> <span className="capabilities">{Object.entries(provider.capabilities).filter(([, value]) => value).map(([key]) => key).join(" / ") || "no capabilities"}</span></div></div>{!compact && <><div className="models">{provider.models.length ? provider.models.map((model) => <code key={model}>{provider.provider_id}/{model}</code>) : <span className="muted">No models reported</span>}</div>{provider.error && <p className="form-error">{provider.error_code}: {provider.error}</p>}</>}</article>)}</div>; }

export function EventsPage({ state }: { state: AppState }) { const [type, setType] = useState(""); const [run, setRun] = useState(""); const [agent, setAgent] = useState(""); const events = state.events.filter((event) => (!type || event.type.includes(type)) && (!run || event.run_id?.includes(run)) && (!agent || event.agent_id?.includes(agent))); return <Page eyebrow="OBSERVABILITY" title="Events"><div className="filters"><label>Type<input value={type} onChange={(event) => setType(event.target.value)} placeholder="run.started" /></label><label>Run ID<input value={run} onChange={(event) => setRun(event.target.value)} /></label><label>Agent ID<input value={agent} onChange={(event) => setAgent(event.target.value)} /></label></div><Panel title={`${events.length} loaded events`}><EventTimeline events={events} /></Panel></Page>; }

export function SettingsPage({ state }: { state: AppState }) { const system = useResource(api.system); return <Page eyebrow="CLIENT PREFERENCES" title="Settings"><Panel title="Server capabilities"><Resource result={system}>{(item: SystemInfo) => <dl className="metadata"><dt>Project</dt><dd><code>{item.project_id}</code></dd><dt>Remote control</dt><dd><Status value={item.remote_control ? "enabled" : "disabled"} /></dd><dt>Event connection</dt><dd><Status value={state.connection} /></dd></dl>}</Resource></Panel><Panel title="Visual preferences"><p className="muted">Dark technical workspace is the current local preference. Server settings and provider credentials are intentionally not editable from this browser.</p></Panel></Page>; }

function Resource<T>({ result, children }: { result: { data: T | null; error: ApiError | null; loading: boolean; refresh: () => void }; children: (data: T) => React.ReactNode }) { if (result.loading) return <Loading />; if (result.error) return <ErrorState error={result.error} retry={result.refresh} />; if (result.data === null) return <Empty>No data returned.</Empty>; return <>{children(result.data)}</>; }

export function VisionPage({ state }: { state: AppState }) {
  const assets = useResource(api.visionAssets, [state.events.length]); const analyses = useResource(api.visionAnalyses, [state.events.length]); const folders = useResource(api.visionFolders); const providers = useResource(api.providers); const [file, setFile] = useState<File | null>(null); const [asset, setAsset] = useState<VisionAsset | null>(null); const [mode, setMode] = useState("describe"); const [prompt, setPrompt] = useState(""); const [error, setError] = useState<ApiError | null>(null); const [busy, setBusy] = useState(false); const [folderRoot, setFolderRoot] = useState(""); const [folderName, setFolderName] = useState("");
  const visionModels = providers.data?.filter((provider) => provider.capabilities.vision).flatMap((provider) => provider.models.map((model) => `${provider.provider_id}://${model}`)) ?? [];
  async function upload() { if (!file) return; setBusy(true); setError(null); try { const created = await api.uploadVisionAsset(file); setAsset(created); assets.refresh(); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("VISION_UPLOAD_FAILED", "Could not upload image.")); } finally { setBusy(false); } }
  async function analyze() { if (!asset) return; setBusy(true); setError(null); try { await api.analyzeVisionAsset(asset.id, { mode, prompt: mode === "custom" ? prompt : null, model: null }); analyses.refresh(); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("VISION_ANALYSIS_FAILED", "Could not start analysis.")); } finally { setBusy(false); } }
  async function registerFolder(event: FormEvent) { event.preventDefault(); setBusy(true); try { await api.registerVisionFolder({ display_name: folderName, root: folderRoot }); folders.refresh(); setFolderName(""); setFolderRoot(""); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("VISION_FOLDER_FAILED", "Could not register folder.")); } finally { setBusy(false); } }
  return <Page eyebrow="LOCAL MULTIMODAL" title="Vision workspace">{error && <div className="banner error">{error.code}: {error.message}</div>}<div className="detail-grid"><section><Panel title="Upload and analyze"><div className="vision-upload"><input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />{file && <p><b>{file.name}</b> <span className="muted">{Math.round(file.size / 1024)} KB</span></p>}<button onClick={upload} disabled={!file || busy}>Upload image</button>{asset && <><dl className="metadata"><dt>Asset</dt><dd><code>{asset.id}</code></dd><dt>Format</dt><dd>{asset.mime_type}</dd></dl><label>Mode<select value={mode} onChange={(event) => setMode(event.target.value)}>{["describe", "detailed", "ocr", "objects", "grounding", "ui", "custom"].map((value) => <option key={value}>{value}</option>)}</select></label>{mode === "custom" && <label>Prompt<textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} /></label>}<p className="muted">Compatible models: {visionModels.length || "no vision-capable provider currently available"}</p><button onClick={analyze} disabled={busy || !visionModels.length}>Analyze</button></>}</div></Panel><Panel title="Analysis history"><Resource result={analyses}>{(items: VisionAnalysis[]) => items.length ? <div className="run-list">{items.map((item) => <div key={item.id}><Status value={item.status} /><span>{item.mode} / {item.model_id}</span><p>{item.description ?? item.ocr_text ?? item.raw_text ?? "Awaiting local model."}</p>{item.error_code && <p className="form-error">{item.error_code}</p>}</div>)}</div> : <Empty>No vision analyses yet.</Empty>}</Resource></Panel></section><section><Panel title="Stored assets"><Resource result={assets}>{(items: VisionAsset[]) => items.length ? <div className="run-list">{items.map((item) => <button className="secondary" key={item.id} onClick={() => setAsset(item)}><span>{item.filename}</span><code>{item.mime_type}</code></button>)}</div> : <Empty>No uploaded images.</Empty>}</Resource></Panel><Panel title="Registered folders"><form className="run-form" onSubmit={registerFolder}><label>Name<input required value={folderName} onChange={(event) => setFolderName(event.target.value)} /></label><label>Allowed local folder<input required value={folderRoot} onChange={(event) => setFolderRoot(event.target.value)} /></label><button disabled={busy}>Register folder</button></form><Resource result={folders}>{(items: VisionFolder[]) => <div className="run-list">{items.map((item) => <div key={item.id}><span>{item.display_name}</span><button className="secondary" onClick={() => api.scanVisionFolder(item.id).then(assets.refresh).catch((reason: unknown) => setError(reason as ApiError))}>Scan</button></div>)}</div>}</Resource></Panel></section></div><p className="muted">Vision observes images only. It never clicks, types, or controls the computer. Folder paths are accepted only when they resolve under server-configured allowed roots.</p></Page>;
}

export function LexiPage({ state }: { state: AppState }) {
  const { text } = useLanguage();
  const t = text.lexi;
  const lexi = useResource(api.lexi);
  const agent = lexi.data?.agent ?? null;
  const agentId = agent?.id;
  const providers = useResource(api.providers);
  const runs = useResource(() => agentId ? api.agentRuns(agentId) : Promise.resolve<Run[]>([]), [agentId, state.events.length]);
  const memory = useResource(() => agentId ? api.memory(agentId) : Promise.resolve([]), [agentId]);
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const selectedRunId = selectedRun?.id ?? null;
  const runDetail = useResource(() => selectedRunId ? api.run(selectedRunId) : Promise.resolve<Run | null>(null), [selectedRunId]);
  const runMemory = useResource(() => selectedRunId ? api.runMemory(selectedRunId) : Promise.resolve([]), [selectedRunId]);
  const tools = useResource(() => selectedRunId ? api.runTools(selectedRunId) : Promise.resolve([]), [selectedRunId]);
  const approvals = useResource(api.approvals, [selectedRunId, state.events.length]);
  const [task, setTask] = useState("");
  const [memoryKind, setMemoryKind] = useState<MemoryKind>("fact");
  const [memoryContent, setMemoryContent] = useState("");
  const [memoryTags, setMemoryTags] = useState("");
  const [bootstrapping, setBootstrapping] = useState(false);
  const [starting, setStarting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [savingMemory, setSavingMemory] = useState(false);
  const [deletingMemoryId, setDeletingMemoryId] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const currentRun = runDetail.data ?? selectedRun;
  const currentRunStatus = currentRun?.status;
  const refreshRunDetail = runDetail.refresh;
  const refreshRunMemory = runMemory.refresh;
  const refreshTools = tools.refresh;
  const refreshApprovals = approvals.refresh;
  const matchingEventCount = selectedRunId ? state.events.filter((event) => event.run_id === selectedRunId).length : 0;
  const pendingApprovals = approvals.data?.filter((approval) => approval.run_id === selectedRunId) ?? [];

  useEffect(() => {
    if (!currentRunStatus || !["queued", "running"].includes(currentRunStatus)) return;
    const poll = window.setInterval(() => {
      refreshRunDetail();
      refreshTools();
      refreshRunMemory();
      refreshApprovals();
    }, 3_000);
    return () => window.clearInterval(poll);
  }, [currentRunStatus, refreshApprovals, refreshRunDetail, refreshRunMemory, refreshTools]);

  useEffect(() => {
    if (!matchingEventCount) return;
    refreshRunDetail();
    refreshTools();
    refreshRunMemory();
    refreshApprovals();
  }, [matchingEventCount, refreshApprovals, refreshRunDetail, refreshRunMemory, refreshTools]);

  async function bootstrap() {
    setBootstrapping(true);
    setError(null);
    try {
      await api.bootstrapLexi();
      lexi.refresh();
    } catch (reason) {
      setError(reason instanceof ApiError ? reason : new ApiError("LEXI_BOOTSTRAP_FAILED", t.error));
    } finally {
      setBootstrapping(false);
    }
  }

  async function start(event: FormEvent) {
    event.preventDefault();
    if (!agent) return;
    setStarting(true);
    setError(null);
    try {
      const run = await api.startRun(agent.id, task);
      setSelectedRun(run);
      setTask("");
      runs.refresh();
    } catch (reason) {
      setError(reason instanceof ApiError ? reason : new ApiError("LEXI_RUN_FAILED", t.error));
    } finally {
      setStarting(false);
    }
  }

  async function cancel() {
    if (!selectedRunId) return;
    setCancelling(true);
    setError(null);
    try {
      // The returned lifecycle record is the only cancellation state applied to the UI.
      const stopped = await api.stopRun(selectedRunId);
      setSelectedRun(stopped);
      runs.refresh();
      refreshRunDetail();
    } catch (reason) {
      setError(reason instanceof ApiError ? reason : new ApiError("LEXI_CANCEL_FAILED", t.error));
    } finally {
      setCancelling(false);
    }
  }

  async function addMemory(event: FormEvent) {
    event.preventDefault();
    if (!agent) return;
    setSavingMemory(true);
    setError(null);
    try {
      await api.createMemory({ agent_id: agent.id, kind: memoryKind, content: memoryContent, tags: memoryTags.split(",").map((tag) => tag.trim()).filter(Boolean) });
      setMemoryContent("");
      setMemoryTags("");
      memory.refresh();
    } catch (reason) {
      setError(reason instanceof ApiError ? reason : new ApiError("MEMORY_CREATE_FAILED", t.error));
    } finally {
      setSavingMemory(false);
    }
  }

  async function removeMemory(memoryId: string) {
    if (!agent) return;
    setDeletingMemoryId(memoryId);
    setError(null);
    try {
      await api.deleteMemory(memoryId, agent.id);
      memory.refresh();
    } catch (reason) {
      setError(reason instanceof ApiError ? reason : new ApiError("MEMORY_DELETE_FAILED", t.error));
    } finally {
      setDeletingMemoryId(null);
    }
  }

  if (lexi.loading) return <section className="page"><div className="state"><RefreshCw className="spin" /> {t.loading}</div></section>;
  if (lexi.error) return <section className="page"><div className="state error"><AlertTriangle /><div><b>{t.error}</b><p>{lexi.error.message}</p></div><button onClick={lexi.refresh}>{t.retry}</button></div></section>;
  if (!lexi.data?.installed || !agent) return <section className="page lexi-page"><div className="page-heading"><div><span className="eyebrow">{t.eyebrow}</span><h2>{t.title}</h2></div></div>{error && <div className="banner error">{error.code}: {error.message}</div>}<section className="panel lexi-bootstrap"><header><h3>{t.bootstrapTitle}</h3></header><p>{t.bootstrapDescription}</p><button onClick={bootstrap} disabled={bootstrapping}><Play size={16} /> {bootstrapping ? t.bootstrapping : t.bootstrap}</button></section></section>;

  return <section className="page lexi-page"><div className="page-heading"><div><span className="eyebrow">{t.eyebrow}</span><h2>{t.title}</h2></div><Status value={agent.status} /></div>{error && <div className="banner error">{error.code}: {error.message}</div>}<p className="lexi-installed">{t.installed}</p><div className="lexi-grid"><section><Panel title={t.composer}><form className="run-form" onSubmit={start}><label>{t.task}<textarea required value={task} onChange={(event) => setTask(event.target.value)} placeholder={t.taskPlaceholder} /></label><div><span>{t.provider} <code>{agent.model_ref}</code></span><button disabled={starting || ["queued", "running"].includes(currentRunStatus ?? "") || !task.trim()}><Play size={16} /> {starting ? t.starting : t.start}</button></div></form></Panel><Panel title={t.output}>{currentRun ? <div className="output lexi-output"><div className="lexi-run-heading"><span>{t.selectedRun}</span><Status value={currentRun.status} /><Link className="text-link" to={`/runs/${currentRun.id}`}>{t.fullRun} <ExternalLink size={14} /></Link></div>{["queued", "running"].includes(currentRun.status) && <button className="danger" onClick={cancel} disabled={cancelling}><CircleStop size={16} /> {cancelling ? t.cancelling : t.cancel}</button>}{cancelling && <p className="muted">{t.cancelPending}</p>}{currentRun.output_text ? <pre>{currentRun.output_text}</pre> : <p className="muted">{currentRun.error ?? t.noOutput}</p>}</div> : <Empty>{t.noRuns}</Empty>}</Panel><Panel title={t.recentRuns}><Resource result={runs}>{(items) => items.length ? <div className="run-list lexi-runs">{items.map((run) => <button className="secondary" key={run.id} onClick={() => setSelectedRun(run)}><Status value={run.status} /><span>{run.input_text}</span><code>{short(run.id)}</code></button>)}</div> : <Empty>{t.noRuns}</Empty>}</Resource></Panel></section><section><Panel title={t.providers}><div className="lexi-provider"><span>{t.provider}</span><code>{agent.model_ref}</code></div>{providers.data?.filter((provider) => provider.available).length ? <div className="capabilities">{providers.data.filter((provider) => provider.available).map((provider) => provider.provider_id).join(" / ")}</div> : <p className="muted">{t.noProviders}</p>}</Panel><Panel title={t.memory}><form className="lexi-memory-form" onSubmit={addMemory}><label>{t.memoryKind}<select value={memoryKind} onChange={(event) => setMemoryKind(event.target.value as MemoryKind)}>{(["fact", "preference", "note", "summary"] as const).map((kind) => <option value={kind} key={kind}>{t.kinds[kind]}</option>)}</select></label><label>{t.memoryContent}<textarea required value={memoryContent} onChange={(event) => setMemoryContent(event.target.value)} /></label><label>{t.memoryTags}<input value={memoryTags} onChange={(event) => setMemoryTags(event.target.value)} placeholder={t.memoryTagsPlaceholder} /></label><button disabled={savingMemory || !memoryContent.trim()}><Plus size={16} /> {savingMemory ? t.addingMemory : t.addMemory}</button></form><Resource result={memory}>{(items) => items.length ? <div className="lexi-memory-list">{items.map((item) => <article key={item.id}><div><Status value={item.kind} /><p>{item.content}</p>{item.tags.length > 0 && <span className="capabilities">{item.tags.join(" / ")}</span>}</div><button className="danger" onClick={() => removeMemory(item.id)} disabled={deletingMemoryId === item.id} aria-label={t.deleteMemory}><Trash2 size={15} /> {deletingMemoryId === item.id ? t.deletingMemory : t.deleteMemory}</button></article>)}</div> : <Empty>{t.memoryEmpty}</Empty>}</Resource></Panel></section></div>{currentRun && <div className="lexi-grid lexi-activity"><Panel title={t.injectedMemory}><Resource result={runMemory}>{(items) => items.length ? <div className="lexi-activity-list">{items.map((item) => <div key={item.memory_id}><code>{short(item.memory_id)}</code><span>#{item.rank}</span>{item.score !== null && <span>{item.score}</span>}{item.deleted && <Status value={t.deletedMemory} />}</div>)}</div> : <Empty>{t.noInjectedMemory}</Empty>}</Resource></Panel><Panel title={t.toolActivity}><Resource result={tools}>{(items) => items.length ? <div className="lexi-activity-list">{items.map((tool) => <div key={tool.id}><Wrench size={15} /><code>{tool.tool_id}</code><Status value={tool.status} />{tool.duration_ms !== null && <span>{tool.duration_ms} {t.milliseconds}</span>}{tool.error_code && <span className="form-error">{tool.error_code}</span>}</div>)}</div> : <Empty>{t.noTools}</Empty>}</Resource>{pendingApprovals.length > 0 && <div className="lexi-approval"><AlertTriangle size={16} /><span>{pendingApprovals.length === 1 ? t.pendingApproval : t.pendingApprovals}</span><Link className="text-link" to="/approvals">{t.openApprovals} <ArrowRight size={14} /></Link></div>}</Panel></div>}</section>;
}
