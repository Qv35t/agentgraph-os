import { z } from "zod";
import {
  agentSchema,
  approvalSchema,
  errorSchema,
  eventSchema,
  healthSchema,
  projectSchema,
  providerSchema,
  runSchema,
  runTreeNodeSchema,
  systemSchema,
  type Agent,
  type Approval,
  type GraphDefinition,
  type Lexi,
  type Memory,
  type MemoryKind,
  type MemoryUsage,
  type Project,
  type Provider,
  type Run,
  type RunTreeNode,
  type RuntimeEvent,
  type SystemInfo,
  visionAnalysisSchema,
  visionAssetSchema,
  visionFolderSchema,
  type VisionAnalysis,
  type VisionAsset,
  type VisionFolder,
  type ToolInvocation,
  lexiSchema,
  memorySchema,
  memoryUsageSchema,
  toolInvocationSchema,
} from "./contracts";

const apiBaseUrl = import.meta.env.VITE_AGENTGRAPH_API_URL || "/api/v1";
const identity = import.meta.env.VITE_AGENTGRAPH_IDENTITY || "local-user";

export class ApiError extends Error {
  constructor(readonly code: string, message: string, readonly details: Record<string, unknown> = {}) {
    super(message);
  }
}

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: { ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }), "X-AgentGraph-Identity": identity, ...init?.headers },
      signal: AbortSignal.timeout(10_000),
    });
    if (response.status === 204) return schema.parse(undefined);
    const payload: unknown = await response.json();
    const failure = errorSchema.safeParse(payload);
    if (!response.ok || failure.success) {
      const error = failure.success
        ? failure.data.error
        : { code: "HTTP_ERROR", message: `Request failed (${response.status})`, details: {} };
      throw new ApiError(error.code, error.message, error.details);
    }
    return schema.parse(payload);
  } catch (error) {
    if (error instanceof ApiError || error instanceof z.ZodError) throw error;
    throw new ApiError("NETWORK_ERROR", "Backend unavailable. Check the local AgentGraph service.");
  }
}

export const api = {
  health: () => request("/health", healthSchema),
  system: () => request<SystemInfo>("/system", systemSchema),
  projects: () => request<Project[]>("/projects", z.array(projectSchema)),
  project: (id: string) => request<Project>(`/projects/${id}`, projectSchema),
  agents: () => request<Agent[]>("/agents", z.array(agentSchema)),
  agent: (id: string) => request<Agent>(`/agents/${id}`, agentSchema),
  createAgent: (agent: { name: string; description: string | null; model_ref: string; graph_definition: GraphDefinition }) =>
    request<Agent>("/agents", agentSchema, { method: "POST", body: JSON.stringify(agent) }),
  updateAgentGraph: (id: string, graphDefinition: GraphDefinition) =>
    request<Agent>(`/agents/${id}/graph`, agentSchema, { method: "PATCH", body: JSON.stringify({ graph_definition: graphDefinition }) }),
  agentRuns: (agentId: string) => request<Run[]>(`/agents/${agentId}/runs`, z.array(runSchema)),
  run: (id: string) => request<Run>(`/runs/${id}`, runSchema),
  runTree: (id: string) => request<RunTreeNode>(`/runs/${id}/tree`, runTreeNodeSchema),
  startRun: (agentId: string, inputText: string) =>
    request<Run>(`/agents/${agentId}/runs`, runSchema, { method: "POST", body: JSON.stringify({ input_text: inputText }) }),
  stopRun: (id: string) => request<Run>(`/runs/${id}/stop`, runSchema, { method: "POST" }),
  providers: () => request<Provider[]>("/providers", z.array(providerSchema)),
  events: (runId?: string) => request<RuntimeEvent[]>(`/events${runId ? `?run_id=${encodeURIComponent(runId)}` : ""}`, z.array(eventSchema)),
  approvals: () => request<Approval[]>("/approvals", z.array(approvalSchema)),
  approve: (id: string) => request<Approval>(`/approvals/${id}/approve`, approvalSchema, { method: "POST" }),
  reject: (id: string) => request<Approval>(`/approvals/${id}/reject`, approvalSchema, { method: "POST" }),
  visionAssets: () => request<VisionAsset[]>("/vision/assets", z.array(visionAssetSchema)),
  uploadVisionAsset: (file: File) => { const body = new FormData(); body.append("file", file); return request<VisionAsset>("/vision/assets", visionAssetSchema, { method: "POST", body }); },
  visionAnalyses: () => request<VisionAnalysis[]>("/vision/analyses", z.array(visionAnalysisSchema)),
  analyzeVisionAsset: (assetId: string, payload: { mode: string; prompt?: string | null; model?: string | null }) => request<VisionAnalysis>(`/vision/assets/${assetId}/analyses`, visionAnalysisSchema, { method: "POST", body: JSON.stringify(payload) }),
  visionFolders: () => request<VisionFolder[]>("/vision/folders", z.array(visionFolderSchema)),
  registerVisionFolder: (payload: { display_name: string; root: string }) => request<VisionFolder>("/vision/folders", visionFolderSchema, { method: "POST", body: JSON.stringify(payload) }),
  scanVisionFolder: (id: string) => request<Record<string, number>>(`/vision/folders/${id}/scan`, z.record(z.number()), { method: "POST" }),
  lexi: () => request<Lexi>("/lexi", lexiSchema),
  bootstrapLexi: () => request<Lexi>("/lexi/bootstrap", lexiSchema, { method: "POST" }),
  memory: (agentId: string) => request<Memory[]>(`/memory?agent_id=${encodeURIComponent(agentId)}`, z.array(memorySchema)),
  createMemory: (payload: { agent_id: string; kind: MemoryKind; content: string; tags: string[] }) => request<Memory>("/memory", memorySchema, { method: "POST", body: JSON.stringify(payload) }),
  deleteMemory: (id: string, agentId: string) => request<void>(`/memory/${id}?agent_id=${encodeURIComponent(agentId)}`, z.void(), { method: "DELETE" }),
  runMemory: (runId: string) => request<MemoryUsage[]>(`/memory/runs/${runId}`, z.array(memoryUsageSchema)),
  runTools: (runId: string) => request<ToolInvocation[]>(`/runs/${runId}/tools`, z.array(toolInvocationSchema)),
};

export const eventSocketConfig = { identity, eventSchema };
