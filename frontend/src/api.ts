import { z } from "zod";
import {
  agentSchema,
  approvalSchema,
  authSessionSchema,
  errorSchema,
  eventSchema,
  grantSchema,
  healthSchema,
  lockdownSchema,
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
  type NodeInfo,
  type Project,
  type Provider,
  type ProbeResult,
  type RecoveryReport,
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
  nodeSchema,
  probeResultSchema,
  recoveryReportSchema,
  securityAuditSchema,
  securityDeviceSchema,
  totpEnrollmentSchema,
  toolInvocationSchema,
  vaultCredentialSchema,
  webAuthnOptionsSchema,
} from "./contracts";

const apiBaseUrl = import.meta.env.VITE_AGENTGRAPH_API_URL || "/api/v1";
let csrfToken: string | null = null;
const authenticationFailureListeners = new Set<() => void>();

export class ApiError extends Error {
  constructor(readonly code: string, message: string, readonly details: Record<string, unknown> = {}, readonly status?: number) {
    super(message);
  }
}

export function setCsrfToken(token: string | null): void { csrfToken = token; }
export function onAuthenticationFailure(listener: () => void): () => void {
  authenticationFailureListeners.add(listener);
  return () => authenticationFailureListeners.delete(listener);
}

function rememberSession(session: import("./contracts").AuthSession): import("./contracts").AuthSession {
  setCsrfToken(session.csrf_token);
  return session;
}

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  try {
    const method = init?.method?.toUpperCase() ?? "GET";
    const headers = new Headers(init?.headers);
    if (!(init?.body instanceof FormData)) headers.set("Content-Type", "application/json");
    if (!["GET", "HEAD", "OPTIONS"].includes(method) && csrfToken) headers.set("X-AgentGraph-CSRF", csrfToken);
    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      credentials: "include",
      headers,
      signal: AbortSignal.timeout(10_000),
    });
    if (response.status === 204) return schema.parse(undefined);
    const payload: unknown = await response.json();
    const failure = errorSchema.safeParse(payload);
    if (!response.ok || failure.success) {
      const error = failure.success
        ? failure.data.error
        : { code: "HTTP_ERROR", message: `Request failed (${response.status})`, details: {} };
      if (response.status === 401) authenticationFailureListeners.forEach((listener) => listener());
      throw new ApiError(error.code, error.message, error.details, response.status);
    }
    return schema.parse(payload);
  } catch (error) {
    if (error instanceof ApiError || error instanceof z.ZodError) throw error;
    throw new ApiError("NETWORK_ERROR", "Backend unavailable. Check the local AgentGraph service.");
  }
}

export const api = {
  session: () => request("/auth/session", authSessionSchema).then(rememberSession),
  bootstrap: (payload: { username: string; bootstrap_secret: string; device_name: string }) =>
    request("/auth/bootstrap", webAuthnOptionsSchema, { method: "POST", body: JSON.stringify(payload) }),
  passkeyRegistrationOptions: (deviceName: string) =>
    request("/auth/passkeys/registration/options", webAuthnOptionsSchema, { method: "POST", body: JSON.stringify({ device_name: deviceName }) }),
  passkeyRegistrationVerify: (payload: { challenge_id: string; credential: Record<string, unknown> }) =>
    request("/auth/passkeys/registration/verify", authSessionSchema, { method: "POST", body: JSON.stringify(payload) }).then(rememberSession),
  passkeyAuthenticationOptions: (username: string) =>
    request("/auth/passkeys/authentication/options", webAuthnOptionsSchema, { method: "POST", body: JSON.stringify({ username }) }),
  passkeyAuthenticationVerify: (payload: { challenge_id: string; credential: Record<string, unknown> }) =>
    request("/auth/passkeys/authentication/verify", authSessionSchema, { method: "POST", body: JSON.stringify(payload) }).then(rememberSession),
  logout: () => request<void>("/auth/logout", z.void(), { method: "POST" }).then(() => setCsrfToken(null)),
  beginTotpEnrollment: () => request("/auth/totp/enrollment", totpEnrollmentSchema, { method: "POST" }),
  confirmTotpEnrollment: (secret: string, code: string) =>
    request<void>("/auth/totp/confirm", z.void(), { method: "POST", body: JSON.stringify({ secret, code }) }),
  verifyTotp: (code: string) =>
    request("/auth/totp/verify", authSessionSchema, { method: "POST", body: JSON.stringify({ code }) }).then(rememberSession),
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
  recovery: (id: string) => request<RecoveryReport>(`/runs/${id}/recovery`, recoveryReportSchema),
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
  nodes: () => request<NodeInfo[]>("/nodes", z.array(nodeSchema)),
  node: (id: string) => request<NodeInfo>(`/nodes/${id}`, nodeSchema),
  enableNode: (id: string) => request<NodeInfo>(`/nodes/${id}/enable`, nodeSchema, { method: "POST" }),
  disableNode: (id: string) => request<NodeInfo>(`/nodes/${id}/disable`, nodeSchema, { method: "POST" }),
  probeNode: (id: string) => request<ProbeResult>(`/nodes/${id}/probe`, probeResultSchema, { method: "POST" }),
  devices: () => request("/security/devices", z.array(securityDeviceSchema)),
  renameDevice: (id: string, displayName: string) => request(`/security/devices/${id}`, securityDeviceSchema, { method: "PATCH", body: JSON.stringify({ display_name: displayName }) }),
  trustDevice: (id: string) => request(`/security/devices/${id}/trust`, securityDeviceSchema, { method: "POST" }),
  revokeDevice: (id: string) => request(`/security/devices/${id}/revoke`, securityDeviceSchema, { method: "POST" }),
  grants: () => request("/security/grants", z.array(grantSchema)),
  revokeGrant: (id: string) => request(`/security/grants/${id}/revoke`, grantSchema, { method: "POST" }),
  lockdown: () => request("/security/lockdown", lockdownSchema),
  activateLockdown: () => request("/security/lockdown/activate", lockdownSchema, { method: "POST" }),
  deactivateLockdown: () => request("/security/lockdown/deactivate", lockdownSchema, { method: "POST" }),
  securityAudit: () => request("/security/audit", z.array(securityAuditSchema)),
  vaultCredentials: () => request("/security/vault", z.array(vaultCredentialSchema)),
  createVaultCredential: (payload: { name: string; credential_type: string; secret: string }) =>
    request("/security/vault", vaultCredentialSchema, { method: "POST", body: JSON.stringify(payload) }),
  replaceVaultCredential: (id: string, secret: string) =>
    request(`/security/vault/${id}`, vaultCredentialSchema, { method: "PUT", body: JSON.stringify({ secret }) }),
  revokeVaultCredential: (id: string) => request(`/security/vault/${id}/revoke`, vaultCredentialSchema, { method: "POST" }),
};

export const eventSocketConfig = { eventSchema };

type JsonWebAuthnCredential = Record<string, unknown>;

function base64UrlToBytes(value: string): Uint8Array {
  const base64 = value.replaceAll("-", "+").replaceAll("_", "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
  return Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
}

function bytesToBase64Url(value: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(value))).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function credentialJson(credential: PublicKeyCredential): JsonWebAuthnCredential {
  const response = credential.response;
  const base = {
    id: credential.id,
    rawId: bytesToBase64Url(credential.rawId),
    type: credential.type,
    clientExtensionResults: credential.getClientExtensionResults(),
  };
  if (response instanceof AuthenticatorAttestationResponse) {
    return { ...base, response: { clientDataJSON: bytesToBase64Url(response.clientDataJSON), attestationObject: bytesToBase64Url(response.attestationObject), transports: response.getTransports?.() } };
  }
  if (response instanceof AuthenticatorAssertionResponse) {
    return { ...base, response: { clientDataJSON: bytesToBase64Url(response.clientDataJSON), authenticatorData: bytesToBase64Url(response.authenticatorData), signature: bytesToBase64Url(response.signature), userHandle: response.userHandle ? bytesToBase64Url(response.userHandle) : null } };
  }
  throw new ApiError("WEBAUTHN_UNSUPPORTED", "The browser returned an unsupported passkey response.");
}

function publicKeyOptions(options: Record<string, unknown>, operation: "create" | "get"): PublicKeyCredentialCreationOptions | PublicKeyCredentialRequestOptions {
  const source = options as Record<string, unknown>;
  if (typeof source.challenge !== "string") throw new ApiError("WEBAUTHN_OPTIONS", "The server returned invalid passkey options.");
  const credentials = (items: unknown) => Array.isArray(items)
    ? items.map((item) => ({ ...(item as PublicKeyCredentialDescriptor), id: base64UrlToBytes(String((item as Record<string, unknown>).id)) }))
    : undefined;
  if (operation === "create") {
    const user = source.user as Record<string, unknown> | undefined;
    if (!user || typeof user.id !== "string" || !Array.isArray(source.pubKeyCredParams)) throw new ApiError("WEBAUTHN_OPTIONS", "The server returned invalid passkey options.");
    return { ...source, challenge: base64UrlToBytes(source.challenge), user: { ...user, id: base64UrlToBytes(user.id) }, excludeCredentials: credentials(source.excludeCredentials) } as unknown as PublicKeyCredentialCreationOptions;
  }
  return { ...source, challenge: base64UrlToBytes(source.challenge), allowCredentials: credentials(source.allowCredentials) } as PublicKeyCredentialRequestOptions;
}

export async function createPasskeyCredential(options: Record<string, unknown>): Promise<JsonWebAuthnCredential> {
  if (!window.PublicKeyCredential || !navigator.credentials) throw new ApiError("WEBAUTHN_UNAVAILABLE", "This browser does not support passkeys.");
  const credential = await navigator.credentials.create({ publicKey: publicKeyOptions(options, "create") as PublicKeyCredentialCreationOptions });
  if (!(credential instanceof PublicKeyCredential)) throw new ApiError("WEBAUTHN_CANCELLED", "Passkey registration was cancelled.");
  return credentialJson(credential);
}

export async function getPasskeyCredential(options: Record<string, unknown>): Promise<JsonWebAuthnCredential> {
  if (!window.PublicKeyCredential || !navigator.credentials) throw new ApiError("WEBAUTHN_UNAVAILABLE", "This browser does not support passkeys.");
  const credential = await navigator.credentials.get({ publicKey: publicKeyOptions(options, "get") as PublicKeyCredentialRequestOptions });
  if (!(credential instanceof PublicKeyCredential)) throw new ApiError("WEBAUTHN_CANCELLED", "Passkey sign-in was cancelled.");
  return credentialJson(credential);
}
