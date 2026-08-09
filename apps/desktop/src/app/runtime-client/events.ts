import { shallowReactive } from "vue";

import type {
  RuntimeEventDto,
  RuntimeSocketErrorFrame,
  RuntimeSocketStatus,
  RuntimeSubscribedFrame,
  RuntimeSyncRequiredFrame,
  RuntimeTopicCursor
} from "@/types/runtime/events";

import {
  assertStableResourceId,
  getRuntimeConnectionInfo,
  RuntimeError
} from "./core";
import {
  onDesktopRuntimeConnectionChanged,
  onDesktopRuntimeConnectionRecovered
} from "./connection";

const APPLICATION_PROTOCOL = "tk-ops-runtime-v1";
const SESSION_PROTOCOL_PREFIX = "tk-ops-session.";
const SUBSCRIBE_TIMEOUT_MS = 12_000;
const ACCOUNT_TOPIC_RESOURCES = ["workspace", "connection", "knowledge", "tasks"];

export type RuntimeEventSocketState = {
  status: RuntimeSocketStatus;
  accountId: string | null;
  error: RuntimeError | null;
};

export type PreparedAccountEventSubscription = {
  commit(): Promise<void>;
  rollback(): Promise<void>;
  finalize(): Promise<void>;
};

type EventListener = (event: RuntimeEventDto) => void;
type SyncListener = (frame: RuntimeSyncRequiredFrame) => void;

type SocketSession = {
  accountId: string;
  revision: number;
  socket: WebSocket;
  buffer: RuntimeEventDto[];
  committed: boolean;
  closed: boolean;
};

export class RuntimeEventSocketManager {
  readonly state = shallowReactive<RuntimeEventSocketState>({
    status: "idle",
    accountId: null,
    error: null
  });

  private activeSession: SocketSession | null = null;
  private readonly eventListeners = new Set<EventListener>();
  private readonly syncListeners = new Set<SyncListener>();
  private readonly removeConnectionChangedListener: () => void;
  private readonly removeConnectionRecoveredListener: () => void;

  constructor() {
    this.removeConnectionChangedListener = onDesktopRuntimeConnectionChanged(
      () => this.suspendForConnectionChange()
    );
    this.removeConnectionRecoveredListener = onDesktopRuntimeConnectionRecovered(
      () => this.retryCurrent()
    );
  }

  onEvent(listener: EventListener): () => void {
    this.eventListeners.add(listener);
    return () => this.eventListeners.delete(listener);
  }

  onSyncRequired(listener: SyncListener): () => void {
    this.syncListeners.add(listener);
    return () => this.syncListeners.delete(listener);
  }

  async prepareAccount(
    accountId: string,
    subscriptionRevision: number,
    cursors: Readonly<Record<string, RuntimeTopicCursor>>,
    signal: AbortSignal
  ): Promise<PreparedAccountEventSubscription> {
    assertStableResourceId(accountId, "account_id");
    const previous = this.activeSession;
    const session = await this.openAccountSession(
      accountId,
      subscriptionRevision,
      cursors,
      signal
    );
    let settled = false;

    return {
      commit: async () => {
        if (settled || session.closed) {
          throw socketClosedError();
        }
        session.committed = true;
        this.activeSession = session;
        this.state.accountId = accountId;
        this.state.status = "online";
        this.state.error = null;
        for (const event of session.buffer.splice(0)) {
          this.emitEvent(event);
        }
      },
      rollback: async () => {
        if (settled) return;
        settled = true;
        closeSession(session);
        if (session.committed) {
          this.activeSession = previous;
          this.state.accountId = previous?.accountId ?? null;
          this.state.status = previous ? "online" : "idle";
        }
      },
      finalize: async () => {
        if (settled) return;
        settled = true;
        if (previous && previous !== session) {
          closeSession(previous);
        }
      }
    };
  }

  async clear(): Promise<void> {
    const active = this.activeSession;
    this.activeSession = null;
    if (active) closeSession(active);
    this.state.accountId = null;
    this.state.status = "idle";
    this.state.error = null;
  }

  async dispose(): Promise<void> {
    this.removeConnectionChangedListener();
    this.removeConnectionRecoveredListener();
    await this.clear();
  }

  async retryCurrent(signal: AbortSignal = new AbortController().signal): Promise<void> {
    const previous = this.activeSession;
    if (!previous) {
      throw new RuntimeError("当前没有可恢复的账号事件连接。", {
        errorCode: "RUNTIME_NOT_READY",
        status: 409
      });
    }
    if (this.state.status === "online" && !previous.closed) return;

    const session = await this.openAccountSession(
      previous.accountId,
      previous.revision + 1,
      {},
      signal
    );
    session.committed = true;
    this.activeSession = session;
    this.state.accountId = session.accountId;
    this.state.status = "online";
    this.state.error = null;
    for (const event of session.buffer.splice(0)) {
      this.emitEvent(event);
    }
    closeSession(previous);
  }

  private suspendForConnectionChange(): void {
    const active = this.activeSession;
    if (!active) return;
    closeSession(active);
    this.state.status = "offline";
    this.state.error = new RuntimeError(
      "Runtime 已重新启动，正在恢复账号事件连接。",
      {
        errorCode: "RUNTIME_CONNECTION_CHANGED",
        status: 503
      }
    );
  }

  private async openAccountSession(
    accountId: string,
    subscriptionRevision: number,
    cursors: Readonly<Record<string, RuntimeTopicCursor>>,
    signal: AbortSignal
  ): Promise<SocketSession> {
    if (
      !Number.isInteger(subscriptionRevision)
      || subscriptionRevision < 1
    ) {
      throw new RuntimeError("事件订阅修订号无效。", {
        errorCode: "REQUEST_VALIDATION_FAILED",
        status: 422
      });
    }
    this.state.status = "connecting";
    this.state.error = null;

    const connection = await getRuntimeConnectionInfo();
    const socket = new WebSocket(
      buildWebSocketUrl(connection.baseUrl),
      [
        APPLICATION_PROTOCOL,
        `${SESSION_PROTOCOL_PREFIX}${encodeSessionToken(connection.sessionToken)}`
      ]
    );
    const session: SocketSession = {
      accountId,
      revision: subscriptionRevision,
      socket,
      buffer: [],
      committed: false,
      closed: false
    };

    try {
      await waitForSubscription(
        session,
        cursors,
        signal,
        (event) => this.handleEvent(session, event),
        (frame) => this.emitSync(frame),
        () => this.handleSessionClosed(session)
      );
      return session;
    } catch (error) {
      closeSession(session);
      const normalized = normalizeSocketError(error);
      this.state.status = "error";
      this.state.error = normalized;
      throw normalized;
    }
  }

  private handleEvent(session: SocketSession, event: RuntimeEventDto): void {
    if (
      event.accountId !== session.accountId
      || !event.topic.startsWith(`account:${session.accountId}:`)
    ) {
      this.state.status = "error";
      this.state.error = new RuntimeError(
        "Runtime 推送了其他账号的事件，已阻止写入当前工作区。",
        {
          errorCode: "ACCOUNT_SCOPE_MISMATCH",
          status: 403
        }
      );
      return;
    }
    if (session.committed && this.activeSession === session) {
      this.emitEvent(event);
      return;
    }
    session.buffer.push(event);
  }

  private emitEvent(event: RuntimeEventDto): void {
    for (const listener of this.eventListeners) listener(event);
  }

  private emitSync(frame: RuntimeSyncRequiredFrame): void {
    for (const listener of this.syncListeners) listener(frame);
  }

  private handleSessionClosed(session: SocketSession): void {
    if (!session.committed || this.activeSession !== session) {
      return;
    }
    this.state.status = "offline";
    this.state.error = new RuntimeError(
      "账号事件连接已断开，页面将使用 HTTP 状态继续工作。",
      {
        errorCode: "RUNTIME_NOT_READY",
        status: 503
      }
    );
  }
}

async function waitForSubscription(
  session: SocketSession,
  cursors: Readonly<Record<string, RuntimeTopicCursor>>,
  signal: AbortSignal,
  onEvent: EventListener,
  onSync: SyncListener,
  onClosed: () => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(
      () => reject(new Error("事件订阅确认超时。")),
      SUBSCRIBE_TIMEOUT_MS
    );
    const cleanup = () => {
      window.clearTimeout(timer);
      signal.removeEventListener("abort", handleAbort);
    };
    const handleAbort = () => {
      cleanup();
      reject(signal.reason);
    };
    signal.addEventListener("abort", handleAbort, { once: true });

    session.socket.onopen = () => {
      session.socket.send(
        JSON.stringify({
          type: "subscribe",
          subscriptionRevision: session.revision,
          accountId: session.accountId,
          topics: ACCOUNT_TOPIC_RESOURCES.map((resource) => {
            const topic = `account:${session.accountId}:${resource}`;
            const cursor = cursors[topic];
            return {
              topic,
              lastEventId: cursor?.lastEventId ?? null,
              afterSequence: cursor?.afterSequence ?? null
            };
          })
        })
      );
    };
    session.socket.onmessage = (message) => {
      const frame = parseSocketFrame(message.data);
      if (!frame) return;
      if (frame.type === "subscribed") {
        const subscribed = frame as RuntimeSubscribedFrame;
        if (subscribed.subscriptionRevision === session.revision) {
          cleanup();
          resolve();
        }
        return;
      }
      if (frame.type === "sync.required") {
        onSync(frame as RuntimeSyncRequiredFrame);
        return;
      }
      if (frame.type === "error") {
        const errorFrame = frame as RuntimeSocketErrorFrame;
        cleanup();
        reject(
          new RuntimeError(errorFrame.message, {
            errorCode: errorFrame.errorCode,
            status: 409
          })
        );
        return;
      }
      if ("eventId" in frame) {
        onEvent(frame as RuntimeEventDto);
      }
    };
    session.socket.onerror = () => {
      cleanup();
      reject(new Error("事件连接失败。"));
    };
    session.socket.onclose = () => {
      session.closed = true;
      if (!session.committed) {
        cleanup();
        reject(socketClosedError());
        return;
      }
      onClosed();
    };
  });
}

function parseSocketFrame(data: unknown): Record<string, unknown> | null {
  if (typeof data !== "string") return null;
  try {
    const value = JSON.parse(data) as unknown;
    return value && typeof value === "object"
      ? (value as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

function buildWebSocketUrl(baseUrl: string): string {
  const url = new URL(baseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/api/v1/ws";
  url.search = "";
  url.hash = "";
  return url.toString();
}

function encodeSessionToken(token: string): string {
  const bytes = new TextEncoder().encode(token);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function closeSession(session: SocketSession): void {
  if (session.closed) return;
  session.closed = true;
  session.socket.close(1000, "account-context-changed");
}

function socketClosedError(): RuntimeError {
  return new RuntimeError("账号事件订阅已断开，请重试切换。", {
    errorCode: "ACCOUNT_SWITCH_PREPARE_FAILED",
    status: 503
  });
}

function normalizeSocketError(error: unknown): RuntimeError {
  if (error instanceof RuntimeError) return error;
  return new RuntimeError("账号事件订阅失败，请稍后重试。", {
    cause: error,
    errorCode: "ACCOUNT_SWITCH_PREPARE_FAILED",
    status: 503
  });
}
