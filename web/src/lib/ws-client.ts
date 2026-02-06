type MessageHandler = (data: unknown) => void;

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export class ReconnectingWebSocket {
  private url: string;
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private retryCount = 0;
  private maxRetries = 10;
  private disposed = false;
  private _connected = false;

  constructor(path: string, token: string) {
    const sep = path.includes("?") ? "&" : "?";
    this.url = `${WS_BASE}${path}${sep}token=${encodeURIComponent(token)}`;
    this.connect();
  }

  get connected(): boolean {
    return this._connected;
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  private connect(): void {
    if (this.disposed) return;

    try {
      this.ws = new WebSocket(this.url);
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this._connected = true;
      this.retryCount = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handlers.forEach((h) => h(data));
      } catch {
        // ignore non-JSON messages
      }
    };

    this.ws.onclose = () => {
      this._connected = false;
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  private scheduleReconnect(): void {
    if (this.disposed || this.retryCount >= this.maxRetries) return;
    const delay = Math.min(1000 * 2 ** this.retryCount, 30000);
    this.retryCount++;
    setTimeout(() => this.connect(), delay);
  }

  dispose(): void {
    this.disposed = true;
    this._connected = false;
    this.handlers.clear();
    this.ws?.close();
    this.ws = null;
  }
}
