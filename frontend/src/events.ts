import { eventSocketConfig } from "./api";
import type { RuntimeEvent } from "./contracts";

export type ConnectionState = "connected" | "reconnecting" | "disconnected";

export class EventClient {
  private socket: WebSocket | null = null;
  private retryTimer: number | null = null;
  private stopped = false;
  private attempts = 0;

  constructor(
    private readonly onEvent: (event: RuntimeEvent) => void,
    private readonly onState: (state: ConnectionState) => void,
  ) {}

  connect(): void {
    this.stopped = false;
    this.attempts = 0;
    this.open();
  }

  private open(): void {
    this.onState("reconnecting");
    const baseUrl = import.meta.env.VITE_AGENTGRAPH_WS_URL || `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/events`;
    const encodedIdentity = btoa(eventSocketConfig.identity).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
    this.socket = new WebSocket(baseUrl, `agentgraph.identity.${encodedIdentity}`);
    this.socket.onopen = () => { this.attempts = 0; this.onState("connected"); };
    this.socket.onmessage = (message) => {
      try {
        const parsed = eventSocketConfig.eventSchema.safeParse(JSON.parse(String(message.data)));
        if (parsed.success) this.onEvent(parsed.data);
      } catch {
        // Malformed external payloads are intentionally ignored.
      }
    };
    this.socket.onclose = (event) => {
      const closeCode = event?.code ?? 1000;
      if (!this.stopped && closeCode !== 1008) this.reconnect();
      if (closeCode === 1008) this.onState("disconnected");
    };
    this.socket.onerror = () => this.socket?.close();
  }

  disconnect(): void {
    this.stopped = true;
    if (this.retryTimer !== null) window.clearTimeout(this.retryTimer);
    this.socket?.close();
    this.onState("disconnected");
  }

  private reconnect(): void {
    this.onState("reconnecting");
    this.attempts += 1;
    const delay = Math.min(30_000, 1_000 * 2 ** Math.min(this.attempts, 5));
    this.retryTimer = window.setTimeout(() => this.open(), delay);
  }
}
