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
  systemSchema,
  type Agent,
  type Approval,
  type GraphDefinition,
  type Project,
  type Provider,
  type Run,
  type RuntimeEvent,
  type SystemInfo,
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
      headers: { "Content-Type": "application/json", "X-AgentGraph-Identity": identity, ...init?.headers },
      signal: AbortSignal.timeout(10_000),
    });
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
  startRun: (agentId: string, inputText: string) =>
    request<Run>(`/agents/${agentId}/runs`, runSchema, { method: "POST", body: JSON.stringify({ input_text: inputText }) }),
  stopRun: (id: string) => request<Run>(`/runs/${id}/stop`, runSchema, { method: "POST" }),
  providers: () => request<Provider[]>("/providers", z.array(providerSchema)),
  events: (runId?: string) => request<RuntimeEvent[]>(`/events${runId ? `?run_id=${encodeURIComponent(runId)}` : ""}`, z.array(eventSchema)),
  approvals: () => request<Approval[]>("/approvals", z.array(approvalSchema)),
  approve: (id: string) => request<Approval>(`/approvals/${id}/approve`, approvalSchema, { method: "POST" }),
  reject: (id: string) => request<Approval>(`/approvals/${id}/reject`, approvalSchema, { method: "POST" }),
};

export const eventSocketConfig = { identity, eventSchema };
