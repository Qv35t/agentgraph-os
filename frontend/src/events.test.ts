import { describe, expect, it, vi } from "vitest";
import { EventClient } from "./events";

class FakeSocket {
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close() { this.onclose?.(); }
}

describe("event client", () => {
  it("accepts valid events and ignores malformed payloads", () => {
    const socket = new FakeSocket();
    vi.stubGlobal("WebSocket", vi.fn(() => socket));
    const received: string[] = [];
    const client = new EventClient((event) => received.push(event.event_id), vi.fn());

    client.connect();
    socket.onmessage?.({ data: "not json" } as MessageEvent);
    socket.onmessage?.({ data: JSON.stringify({ event_id: "evt_1", type: "run.started", timestamp: "2026-01-01T00:00:00Z", project_id: "project", run_id: null, task_id: null, agent_id: null, provider_id: null, severity: "info", payload: {} }) } as MessageEvent);

    expect(received).toEqual(["evt_1"]);
    client.disconnect();
  });
});
