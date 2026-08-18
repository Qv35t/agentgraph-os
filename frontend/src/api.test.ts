import { describe, expect, it, vi } from "vitest";
import { api, setCsrfToken } from "./api";

describe("remote API client", () => {
  it("parses a successful response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 })));

    await expect(api.health()).resolves.toEqual({ status: "ok" });
  });

  it("uses cookie sessions and in-memory CSRF tokens without an identity header", async () => {
    setCsrfToken("csrf-token");
    const run = { id: "run-1", agent_id: "agent-1", status: "cancelled", input_text: "task", output_text: null, error: null, created_at: "2026-08-18T00:00:00Z", started_at: null, finished_at: null, provider_id: null, model_id: null, finish_reason: null, input_tokens: null, output_tokens: null, total_tokens: null, latency_ms: null };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(run), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await api.stopRun("run-1");

    const request = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = request.headers as Headers;
    expect(request.credentials).toBe("include");
    expect(headers.get("X-AgentGraph-CSRF")).toBe("csrf-token");
    expect(headers.get("X-AgentGraph-Identity")).toBeNull();
  });

  it("normalizes backend error envelopes", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "FORBIDDEN", message: "Denied", details: {} } }), { status: 403 })));

    await expect(api.system()).rejects.toMatchObject({ code: "FORBIDDEN", message: "Denied" });
  });

  it("normalizes network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));

    await expect(api.providers()).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  });

  it("parses Lexi bootstrap state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ installed: true, agent: { id: "agent-1", name: "Lexi", description: null, status: "idle", model_ref: "auto://default", graph_definition: { version: 1, runtime: "lexi-v1", nodes: [], edges: [] }, created_at: "2026-08-15T00:00:00Z", updated_at: "2026-08-15T00:00:00Z" } }), { status: 200 })));

    await expect(api.lexi()).resolves.toMatchObject({ installed: true, agent: { graph_definition: { runtime: "lexi-v1" } } });
  });

  it("accepts the empty response from scoped memory deletion", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    await expect(api.deleteMemory("memory-1", "agent-1")).resolves.toBeUndefined();
  });

  it("parses a persisted run hierarchy", async () => {
    const run = { id: "run-1", agent_id: "agent-1", status: "succeeded", input_text: "task", output_text: "result", error: null, created_at: "2026-08-16T00:00:00Z", started_at: null, finished_at: null, provider_id: null, model_id: null, finish_reason: null, input_tokens: null, output_tokens: null, total_tokens: null, latency_ms: null };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ node_id: null, depth: 0, run, children: [{ node_id: "research", depth: 1, run: { ...run, id: "run-2" }, children: [] }] }), { status: 200 })));

    await expect(api.runTree("run-1")).resolves.toMatchObject({ children: [{ node_id: "research" }] });
  });

  it("parses node registry and probe responses", async () => {
    const node = { node_id: "node-1", name: "Worker", role: "worker", status: "online", enabled: true, capabilities: { platform: "Linux", architecture: "x86_64", agentgraph_version: "0.1.0", features: ["system.probe"], resources: { cpu_count: 4, load_average: 0, memory_total_bytes: 100, memory_available_bytes: 50 } }, created_at: "2026-08-17T00:00:00Z", updated_at: "2026-08-17T00:00:00Z", last_seen_at: "2026-08-17T00:00:00Z" };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response(JSON.stringify([node]), { status: 200 })).mockResolvedValueOnce(new Response(JSON.stringify({ task_id: "task-1", node_id: "node-1", status: "succeeded", result: { ok: true } }), { status: 200 })));

    await expect(api.nodes()).resolves.toEqual([node]);
    await expect(api.probeNode("node-1")).resolves.toMatchObject({ status: "succeeded", result: { ok: true } });
  });

  it("parses durable recovery evidence", async () => {
    const report = { run_id: "run-1", checkpoints: [{ checkpoint_id: "checkpoint-1", sequence: 1, format_version: 1, reason: "created", checksum: "a".repeat(64), created_at: "2026-08-17T00:00:00Z" }], actions: [], decisions: [{ decision_id: "decision-1", checkpoint_id: "checkpoint-1", outcome: "stopped_no_replay", details: { reason: "safe" }, created_at: "2026-08-17T00:00:00Z" }], limits: { automatic_resume: false, automatic_rollback: false, description: "No replay." } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(report), { status: 200 })));

    await expect(api.recovery("run-1")).resolves.toMatchObject({ decisions: [{ outcome: "stopped_no_replay" }] });
  });
});
