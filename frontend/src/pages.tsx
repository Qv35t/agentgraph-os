import { type FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { addEdge, applyEdgeChanges, applyNodeChanges, Background, Controls, ReactFlow, type Connection, type Edge, type EdgeChange, type Node, type NodeChange, useEdgesState, useNodesState } from "@xyflow/react";
import { AlertTriangle, ArrowRight, Check, CircleStop, FolderKanban, Play, Plus, RefreshCw, X } from "lucide-react";
import { api, ApiError } from "./api";
import type { Agent, Approval, GraphDefinition, Provider, RuntimeEvent, SystemInfo } from "./contracts";
import type { AppState } from "./App";

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
  return <section className="page"><div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div></div>{children}</section>;
}

function Loading() { return <div className="state"><RefreshCw className="spin" /> Loading live state...</div>; }
function Empty({ children }: { children: React.ReactNode }) { return <div className="state empty">{children}</div>; }
function ErrorState({ error, retry }: { error: ApiError; retry: () => void }) { return <div className="state error"><AlertTriangle /><div><b>{error.code}</b><p>{error.message}</p></div><button onClick={retry}>Retry</button></div>; }
function Status({ value }: { value: string }) { return <span className={`status ${value}`}>{value.replaceAll("_", " ")}</span>; }
function time(value: string | null) { return value ? new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(value)) : "-"; }
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
  const running = agents.data?.filter((agent) => agent.status === "running").length ?? 0;
  return <Page eyebrow="SYSTEM OVERVIEW" title="Control room">
    <div className="metrics">
      <Metric label="API" value={health.data?.status ?? "offline"} tone={health.error ? "danger" : "success"} />
      <Metric label="Remote control" value={system.data?.remote_control ? "enabled" : "restricted"} tone={system.data?.remote_control ? "success" : "warning"} />
      <Metric label="Providers" value={String(providers.data?.filter((item) => item.available).length ?? 0)} detail={`${providers.data?.length ?? 0} registered`} />
      <Metric label="Agents" value={String(agents.data?.length ?? 0)} detail={`${running} active`} />
      <Metric label="Approvals" value={String(approvals.data?.length ?? 0)} detail="pending" tone={approvals.data?.length ? "warning" : undefined} />
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
  const providers = useResource(api.providers); const [open, setOpen] = useState(false); const [name, setName] = useState(""); const [description, setDescription] = useState(""); const [modelRef, setModelRef] = useState("auto://default"); const [graph, setGraph] = useState<GraphDefinition>({ nodes: [{ id: "agent", type: "agent", label: "Agent", position: [80, 70] }], edges: [] }); const [error, setError] = useState<ApiError | null>(null); const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); setError(null); try { await api.createAgent({ name, description: description || null, model_ref: modelRef, graph_definition: graph }); setOpen(false); setName(""); setDescription(""); onCreated(); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("CREATE_FAILED", "Could not create agent.")); } finally { setSaving(false); } }
  const models = providers.data?.flatMap((provider) => provider.models.map((model) => `${provider.provider_id}://${model}`)) ?? [];
  return <section className="composer"><div><span className="eyebrow">NEW WORKFLOW</span><h3>Create an agent graph</h3><p>Graph layout is durable metadata. Runtime behavior remains defined by the backend.</p></div><button onClick={() => setOpen(true)}><Plus size={16} /> Create agent</button>{open && <div className="dialog-backdrop" role="presentation"><form className="dialog" onSubmit={submit} role="dialog" aria-modal="true" aria-label="Create agent"><header><h3>Create agent</h3><button className="icon-button" type="button" onClick={() => setOpen(false)} aria-label="Close"><X /></button></header><label>Name<input autoFocus required value={name} onChange={(event) => setName(event.target.value)} /></label><label>Description<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label><label>Model route<select value={modelRef} onChange={(event) => setModelRef(event.target.value)}><option value="auto://default">auto://default</option>{models.map((model) => <option key={model} value={model}>{model}</option>)}</select></label><GraphEditor value={graph} onChange={setGraph} /><div className="dialog-actions"><button type="button" className="secondary" onClick={() => setOpen(false)}>Cancel</button><button disabled={saving}>{saving ? "Creating..." : "Create agent"}</button></div>{error && <p className="form-error">{error.code}: {error.message}</p>}</form></div>}</section>;
}

function GraphEditor({ value, onChange }: { value: GraphDefinition; onChange: (graph: GraphDefinition) => void }) {
  const seedNodes: Node[] = value.nodes.length ? value.nodes.map((node) => ({ id: node.id, type: node.type, position: { x: node.position[0], y: node.position[1] }, data: { label: node.label } })) : [{ id: "agent", position: { x: 80, y: 70 }, data: { label: "Agent" } }];
  const [nodes, setNodes] = useNodesState(seedNodes); const [edges, setEdges] = useEdgesState(value.edges);
  const sync = useCallback((nextNodes: Node[], nextEdges: Edge[]) => onChange({ nodes: nextNodes.map((node) => ({ id: node.id, type: node.type ?? "agent", label: String(node.data.label ?? node.id), position: [node.position.x, node.position.y] })), edges: nextEdges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target })) }), [onChange]);
  const onConnect = useCallback((connection: Connection) => setEdges((current) => { const next = addEdge(connection, current); sync(nodes, next); return next; }), [nodes, setEdges, sync]);
  const onNodeChanges = useCallback((changes: NodeChange[]) => setNodes((current) => { const next = applyNodeChanges(changes, current); sync(next, edges); return next; }), [edges, setNodes, sync]);
  const onEdgeChanges = useCallback((changes: EdgeChange[]) => setEdges((current) => { const next = applyEdgeChanges(changes, current); sync(nodes, next); return next; }), [nodes, setEdges, sync]);
  function addNode() { setNodes((current) => { const next = [...current, { id: `agent-${current.length + 1}`, position: { x: 100 + current.length * 110, y: 150 }, data: { label: `Agent ${current.length + 1}` } }]; sync(next, edges); return next; }); }
  return <div className="graph-editor"><div className="graph-label">Workflow graph <span>Drag nodes or connect handles to save layout semantics.</span><button type="button" className="add-node" onClick={addNode}><Plus size={13} /> Add node</button></div><ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodeChanges} onEdgesChange={onEdgeChanges} onConnect={onConnect} fitView><Background gap={18} size={1} /><Controls showInteractive={false} /></ReactFlow></div>;
}

function AgentDetail({ agent, events }: { agent: Agent; events: RuntimeEvent[] }) {
  const runs = useResource(() => api.agentRuns(agent.id), [agent.id]); const navigate = useNavigate(); const [input, setInput] = useState(""); const [error, setError] = useState<ApiError | null>(null); const [starting, setStarting] = useState(false); const [graph, setGraph] = useState<GraphDefinition>(agent.graph_definition); const [savingGraph, setSavingGraph] = useState(false);
  useEffect(() => { setGraph(agent.graph_definition); }, [agent.id, agent.graph_definition]);
  async function start(event: FormEvent) { event.preventDefault(); setStarting(true); setError(null); try { const run = await api.startRun(agent.id, input); navigate(`/runs/${run.id}`); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("RUN_FAILED", "Could not start run.")); } finally { setStarting(false); } }
  async function saveGraph() { setSavingGraph(true); setError(null); try { await api.updateAgentGraph(agent.id, graph); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("GRAPH_SAVE_FAILED", "Could not save graph.")); } finally { setSavingGraph(false); } }
  return <div className="detail-grid"><section><Panel title="Run composer"><form className="run-form" onSubmit={start}><label>Task<textarea required value={input} onChange={(event) => setInput(event.target.value)} placeholder="Describe the task for this agent." /></label><div><span>Model route <code>{agent.model_ref}</code></span><button disabled={starting || agent.status === "running"}><Play size={16} /> {starting ? "Starting..." : "Start run"}</button></div>{agent.status === "running" && <p className="form-error">This agent already has an active run.</p>}{error && <p className="form-error">{error.code}: {error.message}</p>}</form></Panel><Panel title="Workflow graph"><GraphEditor key={agent.id} value={graph} onChange={setGraph} /><div className="dialog-actions"><button onClick={saveGraph} disabled={savingGraph}>{savingGraph ? "Saving..." : "Save graph"}</button></div></Panel><Panel title="Run history"><Resource result={runs}>{(items) => items.length ? <div className="run-list">{items.map((run) => <Link to={`/runs/${run.id}`} key={run.id}><Status value={run.status} /><span>{run.input_text}</span><code>{short(run.id)}</code></Link>)}</div> : <Empty>No runs yet.</Empty>}</Resource></Panel></section><section><Panel title="Agent metadata"><dl className="metadata"><dt>Agent ID</dt><dd><code>{agent.id}</code></dd><dt>Status</dt><dd><Status value={agent.status} /></dd><dt>Model</dt><dd><code>{agent.model_ref}</code></dd><dt>Description</dt><dd>{agent.description ?? "No description"}</dd></dl></Panel><Panel title="Activity"><EventTimeline events={events} runId={undefined} /></Panel></section></div>;
}

export function RunPage({ state }: { state: AppState }) {
  const { runId = "" } = useParams(); const run = useResource(() => api.run(runId), [runId]); const [stopping, setStopping] = useState(false); const [error, setError] = useState<ApiError | null>(null);
  async function stop() { setStopping(true); setError(null); try { await api.stopRun(runId); run.refresh(); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("STOP_FAILED", "Could not stop run.")); } finally { setStopping(false); } }
  const matchingEventCount = state.events.filter((event) => event.run_id === runId).length;
  const refreshRun = run.refresh;
  const runStatus = run.data?.status;
  useEffect(() => { if (matchingEventCount > 0) refreshRun(); }, [matchingEventCount, refreshRun]);
  useEffect(() => {
    if (!runStatus || !["queued", "running"].includes(runStatus)) return;
    const poll = window.setInterval(refreshRun, 3_000);
    return () => window.clearInterval(poll);
  }, [runStatus, refreshRun]);
  return <Page eyebrow="RUN WORKSPACE" title={run.data ? `Run ${short(run.data.id)}` : "Run"}><Resource result={run}>{(item) => <><div className="run-header"><Status value={item.status} /><code>{item.provider_id ?? "provider pending"}/{item.model_id ?? "model pending"}</code>{["queued", "running"].includes(item.status) && <button className="danger" onClick={stop} disabled={stopping}><CircleStop size={16} /> {stopping ? "Stopping..." : "Stop run"}</button>}</div>{error && <div className="banner error">{error.code}: {error.message}</div>}<div className="run-workspace"><Panel title="Output"><div className="output"><p className="input-label">TASK</p><p>{item.input_text}</p><hr /><p className="input-label">RESULT</p>{item.output_text ? <pre>{item.output_text}</pre> : <p className="muted">{item.error ?? "Execution output will appear when the backend completes the run."}</p>}</div></Panel><Panel title="Event timeline"><EventTimeline events={state.events} runId={item.id} /></Panel></div><Panel title="Metadata inspector"><dl className="metadata grid"><dt>Run ID</dt><dd><code>{item.id}</code></dd><dt>Agent ID</dt><dd><Link to={`/agents/${item.agent_id}`}><code>{item.agent_id}</code></Link></dd><dt>Created</dt><dd>{new Date(item.created_at).toLocaleString()}</dd><dt>Started</dt><dd>{item.started_at ? new Date(item.started_at).toLocaleString() : "-"}</dd><dt>Finished</dt><dd>{item.finished_at ? new Date(item.finished_at).toLocaleString() : "-"}</dd><dt>Tokens</dt><dd>{item.total_tokens ?? "-"}</dd><dt>Latency</dt><dd>{item.latency_ms ? `${item.latency_ms} ms` : "-"}</dd></dl></Panel></>}</Resource></Page>;
}

export function ApprovalsPage({ state }: { state: AppState }) {
  const approvals = useResource(api.approvals, [state.events]); const [error, setError] = useState<ApiError | null>(null);
  async function decide(approval: Approval, approved: boolean) { setError(null); try { await (approved ? api.approve(approval.approval_id) : api.reject(approval.approval_id)); approvals.refresh(); state.refresh(); } catch (reason) { setError(reason instanceof ApiError ? reason : new ApiError("APPROVAL_FAILED", "Could not submit the decision.")); } }
  return <Page eyebrow="HUMAN GATE" title="Approvals">{error && <div className="banner error">{error.code}: {error.message}</div>}<Resource result={approvals}>{(items) => items.length ? <div className="approval-list">{items.map((approval) => <article key={approval.approval_id} className="approval"><div><Status value={approval.status} /><h3>{approval.action}</h3><p>{approval.description}</p><dl><dt>Run</dt><dd><code>{approval.run_id ?? "not associated"}</code></dd><dt>Task</dt><dd><code>{approval.task_id ?? "not associated"}</code></dd><dt>Requested</dt><dd>{new Date(approval.created_at).toLocaleString()}</dd></dl></div><div className="approval-actions"><button className="secondary" onClick={() => decide(approval, false)}><X size={16} /> Reject</button><button onClick={() => decide(approval, true)}><Check size={16} /> Approve</button></div></article>)}</div> : <Empty>No pending approvals. Approval persistence is process-local and does not pause a run yet.</Empty>}</Resource></Page>;
}

export function ProvidersPage() { const providers = useResource(api.providers); return <Page eyebrow="MODEL ROUTER" title="Providers"><ProviderList providers={providers.data} loading={providers.loading} error={providers.error} retry={providers.refresh} /></Page>; }
function ProviderList({ providers, loading, error, retry, compact = false }: { providers: Provider[] | null; loading: boolean; error: ApiError | null; retry: () => void; compact?: boolean }) { if (loading) return <Loading />; if (error) return <ErrorState error={error} retry={retry} />; if (!providers?.length) return <Empty>No providers discovered.</Empty>; return <div className={compact ? "provider-stack compact" : "provider-stack"}>{providers.map((provider) => <article className="provider" key={provider.provider_id}><div><h3>{provider.provider_id}</h3><div><Status value={provider.available ? "available" : provider.enabled ? "unavailable" : "disabled"} /> <span className="capabilities">{Object.entries(provider.capabilities).filter(([, value]) => value).map(([key]) => key).join(" / ") || "no capabilities"}</span></div></div>{!compact && <><div className="models">{provider.models.length ? provider.models.map((model) => <code key={model}>{provider.provider_id}/{model}</code>) : <span className="muted">No models reported</span>}</div>{provider.error && <p className="form-error">{provider.error_code}: {provider.error}</p>}</>}</article>)}</div>; }

export function EventsPage({ state }: { state: AppState }) { const [type, setType] = useState(""); const [run, setRun] = useState(""); const [agent, setAgent] = useState(""); const events = state.events.filter((event) => (!type || event.type.includes(type)) && (!run || event.run_id?.includes(run)) && (!agent || event.agent_id?.includes(agent))); return <Page eyebrow="OBSERVABILITY" title="Events"><div className="filters"><label>Type<input value={type} onChange={(event) => setType(event.target.value)} placeholder="run.started" /></label><label>Run ID<input value={run} onChange={(event) => setRun(event.target.value)} /></label><label>Agent ID<input value={agent} onChange={(event) => setAgent(event.target.value)} /></label></div><Panel title={`${events.length} loaded events`}><EventTimeline events={events} /></Panel></Page>; }

export function SettingsPage({ state }: { state: AppState }) { const system = useResource(api.system); return <Page eyebrow="CLIENT PREFERENCES" title="Settings"><Panel title="Server capabilities"><Resource result={system}>{(item: SystemInfo) => <dl className="metadata"><dt>Project</dt><dd><code>{item.project_id}</code></dd><dt>Remote control</dt><dd><Status value={item.remote_control ? "enabled" : "disabled"} /></dd><dt>Event connection</dt><dd><Status value={state.connection} /></dd></dl>}</Resource></Panel><Panel title="Visual preferences"><p className="muted">Dark technical workspace is the current local preference. Server settings and provider credentials are intentionally not editable from this browser.</p></Panel></Page>; }

function Resource<T>({ result, children }: { result: { data: T | null; error: ApiError | null; loading: boolean; refresh: () => void }; children: (data: T) => React.ReactNode }) { if (result.loading) return <Loading />; if (result.error) return <ErrorState error={result.error} retry={result.refresh} />; if (result.data === null) return <Empty>No data returned.</Empty>; return <>{children(result.data)}</>; }
