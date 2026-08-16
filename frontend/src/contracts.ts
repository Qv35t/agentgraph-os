import { z } from "zod";

export const permissionSchema = z.enum(["read", "execute", "control", "approve", "admin"]);
export type Permission = z.infer<typeof permissionSchema>;

export const errorSchema = z.object({
  error: z.object({ code: z.string(), message: z.string(), details: z.record(z.unknown()) }),
});

export const systemSchema = z.object({ project_id: z.string(), remote_control: z.boolean() });
export type SystemInfo = z.infer<typeof systemSchema>;

export const projectSchema = z.object({ project_id: z.string(), name: z.string() });
export type Project = z.infer<typeof projectSchema>;

export const graphNodeSchema = z.object({
  id: z.string(),
  type: z.string(),
  label: z.string(),
  position: z.tuple([z.number(), z.number()]),
  agent_id: z.string().optional(),
  instructions: z.string().max(4000).optional(),
});
export const graphEdgeSchema = z.object({ id: z.string(), source: z.string(), target: z.string() });
export const graphSchema = z.object({
  version: z.union([z.literal(1), z.literal(2)]).optional(),
  runtime: z.enum(["model-v1", "lexi-v1", "team-v1"]).optional(),
  nodes: z.array(graphNodeSchema),
  edges: z.array(graphEdgeSchema),
});
export type GraphDefinition = z.infer<typeof graphSchema>;

export const agentSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  status: z.enum(["idle", "running", "error"]),
  model_ref: z.string(),
  graph_definition: graphSchema,
  created_at: z.string(),
  updated_at: z.string(),
});
export type Agent = z.infer<typeof agentSchema>;

export const runSchema = z.object({
  id: z.string(),
  agent_id: z.string(),
  status: z.enum(["queued", "running", "succeeded", "failed", "cancelled"]),
  input_text: z.string(),
  output_text: z.string().nullable(),
  error: z.string().nullable(),
  created_at: z.string(),
  started_at: z.string().nullable(),
  finished_at: z.string().nullable(),
  provider_id: z.string().nullable(),
  model_id: z.string().nullable(),
  finish_reason: z.string().nullable(),
  input_tokens: z.number().nullable(),
  output_tokens: z.number().nullable(),
  total_tokens: z.number().nullable(),
  latency_ms: z.number().nullable(),
});
export type Run = z.infer<typeof runSchema>;

export const runTreeNodeSchema: z.ZodType<RunTreeNode> = z.lazy(() => z.object({
  node_id: z.string().nullable(),
  depth: z.number(),
  run: runSchema,
  children: z.array(runTreeNodeSchema),
}));
export type RunTreeNode = { node_id: string | null; depth: number; run: Run; children: RunTreeNode[] };

export const providerSchema = z.object({
  provider_id: z.string(),
  enabled: z.boolean(),
  available: z.boolean(),
  models: z.array(z.string()),
  capabilities: z.record(z.boolean()),
  error_code: z.string().nullable(),
  error: z.string().nullable(),
});
export type Provider = z.infer<typeof providerSchema>;

export const approvalSchema = z.object({
  approval_id: z.string(),
  project_id: z.string(),
  run_id: z.string().nullable(),
  task_id: z.string().nullable(),
  action: z.string(),
  description: z.string(),
  risk: z.string().nullable(),
  status: z.enum(["pending", "approved", "rejected", "expired", "cancelled"]),
  created_at: z.string(),
});
export type Approval = z.infer<typeof approvalSchema>;

export const eventSchema = z.object({
  event_id: z.string(),
  type: z.string(),
  timestamp: z.string(),
  project_id: z.string(),
  run_id: z.string().nullable(),
  task_id: z.string().nullable(),
  agent_id: z.string().nullable(),
  provider_id: z.string().nullable(),
  severity: z.string(),
  payload: z.record(z.unknown()),
});
export type RuntimeEvent = z.infer<typeof eventSchema>;

export const healthSchema = z.object({ status: z.string() });

export const visionAssetSchema = z.object({ id: z.string(), filename: z.string(), mime_type: z.string(), size_bytes: z.number(), sha256: z.string(), source_type: z.string(), created_at: z.string() });
export const visionAnalysisSchema = z.object({ id: z.string(), asset_id: z.string(), provider_id: z.string(), model_id: z.string(), mode: z.enum(["describe", "detailed", "ocr", "objects", "grounding", "ui", "custom"]), prompt: z.string().nullable(), status: z.enum(["queued", "running", "completed", "failed"]), raw_text: z.string().nullable(), description: z.string().nullable(), ocr_text: z.string().nullable(), structured_result: z.record(z.unknown()).nullable(), latency_ms: z.number().nullable(), error_code: z.string().nullable(), created_at: z.string(), completed_at: z.string().nullable() });
export const visionFolderSchema = z.object({ id: z.string(), display_name: z.string(), enabled: z.boolean(), created_at: z.string() });
export type VisionAsset = z.infer<typeof visionAssetSchema>;
export type VisionAnalysis = z.infer<typeof visionAnalysisSchema>;
export type VisionFolder = z.infer<typeof visionFolderSchema>;

export const lexiSchema = z.object({ installed: z.boolean(), agent: agentSchema.nullable() });
export type Lexi = z.infer<typeof lexiSchema>;

export const memoryKindSchema = z.enum(["fact", "preference", "note", "summary"]);
export type MemoryKind = z.infer<typeof memoryKindSchema>;
export const memorySchema = z.object({
  id: z.string(),
  project_id: z.string(),
  agent_id: z.string(),
  kind: memoryKindSchema,
  content: z.string(),
  tags: z.array(z.string()),
  created_at: z.string(),
  updated_at: z.string(),
});
export type Memory = z.infer<typeof memorySchema>;

export const memoryUsageSchema = z.object({ memory_id: z.string(), rank: z.number(), score: z.number().nullable(), deleted: z.boolean() });
export type MemoryUsage = z.infer<typeof memoryUsageSchema>;

export const toolInvocationSchema = z.object({
  id: z.string(),
  tool_id: z.string(),
  risk: z.string(),
  status: z.string(),
  approval_id: z.string().nullable(),
  error_code: z.string().nullable(),
  started_at: z.string().nullable(),
  finished_at: z.string().nullable(),
  duration_ms: z.number().nullable(),
});
export type ToolInvocation = z.infer<typeof toolInvocationSchema>;
