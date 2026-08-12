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
});
