import { describe, expect, it, vi } from "vitest";
import { api } from "./api";

describe("remote API client", () => {
  it("parses a successful response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 })));

    await expect(api.health()).resolves.toEqual({ status: "ok" });
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
});
