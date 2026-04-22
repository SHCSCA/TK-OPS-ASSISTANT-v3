import { defineStore } from "pinia";

import type { TaskEvent, TaskInfo, TaskEventType } from "@/types/task-events";

type TaskEventCallback = (event: TaskEvent) => void;

type TaskBusState = {
  tasks: Map<string, TaskInfo>;
  lastEvents: Map<string, TaskEvent>;
  connected: boolean;
  _socket: WebSocket | null;
  _subscribers: Map<string, Set<TaskEventCallback>>;
  _typeSubscribers: Map<TaskEventType, Set<TaskEventCallback>>;
  _reconnectTimer: number | null;
  _heartbeatTimer: number | null;
  _manualDisconnect: boolean;
};

const DEFAULT_RUNTIME_BASE_URL = "http://127.0.0.1:8000";
const RECONNECT_DELAY_MS = 3000;
const HEARTBEAT_INTERVAL_MS = 25000;

function resolveRuntimeBaseUrl(): string {
  return import.meta.env.VITE_RUNTIME_BASE_URL?.trim() || DEFAULT_RUNTIME_BASE_URL;
}

function resolveWebSocketUrl(): string {
  const url = new URL(resolveRuntimeBaseUrl());
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/api/ws";
  url.search = "";
  url.hash = "";
  return url.toString();
}

function isRuntimeEvent(value: unknown): value is TaskEvent {
  if (!value || typeof value !== "object") {
    return false;
  }

  const event = value as Partial<TaskEvent>;
  return typeof event.schema_version === "number" && typeof event.type === "string";
}

function inferTaskStatus(event: TaskEvent, existing: TaskInfo | undefined): TaskInfo["status"] {
  if (event.status) {
    return event.status;
  }

  switch (event.type) {
    case "task.started":
      return "running";
    case "task.completed":
      return "succeeded";
    case "task.failed":
      return "failed";
    case "render.progress":
      return "running";
    default:
      return existing?.status ?? "queued";
  }
}

function inferTaskType(event: TaskEvent, existing: TaskInfo | undefined): string {
  if (event.taskType) {
    return event.taskType;
  }
  if (existing?.task_type) {
    return existing.task_type;
  }
  return event.type.split(".")[0] || "generic";
}

function inferTaskProgress(event: TaskEvent, existing: TaskInfo | undefined): number {
  if (typeof event.progressPct === "number") {
    return event.progressPct;
  }
  if (typeof event.progress === "number") {
    return event.progress;
  }
  if (event.type === "task.completed") {
    return 100;
  }
  return existing?.progress ?? 0;
}

function collectEventKeys(event: TaskEvent): string[] {
  const keys = new Set<string>();
  const candidates = [
    event.taskId,
    event.videoId,
    event.jobId,
    event.trackId,
    event.accountId,
    event.workspaceId,
    event.planId,
    event.projectId
  ];

  candidates.forEach((candidate) => {
    if (typeof candidate === "string" && candidate.length > 0) {
      keys.add(candidate);
    }
  });

  return [...keys];
}

function buildTaskInfo(event: TaskEvent, existing: TaskInfo | undefined): TaskInfo | null {
  if (typeof event.taskId !== "string" || event.taskId.length === 0) {
    return null;
  }

  const now = new Date().toISOString();
  const progress = inferTaskProgress(event, existing);
  const taskType = inferTaskType(event, existing);
  const status = inferTaskStatus(event, existing);
  const message =
    event.message ??
    existing?.message ??
    (event.type === "render.progress" ? "任务处理中" : taskType);

  return {
    id: event.taskId,
    task_type: taskType,
    project_id: event.projectId ?? existing?.project_id ?? null,
    status,
    progress,
    message,
    created_at: existing?.created_at ?? now,
    updated_at: now
  };
}

export const useTaskBusStore = defineStore("task-bus", {
  state: (): TaskBusState => ({
    tasks: new Map<string, TaskInfo>(),
    lastEvents: new Map<string, TaskEvent>(),
    connected: false,
    _socket: null,
    _subscribers: new Map<string, Set<TaskEventCallback>>(),
    _typeSubscribers: new Map<TaskEventType, Set<TaskEventCallback>>(),
    _reconnectTimer: null,
    _heartbeatTimer: null,
    _manualDisconnect: false
  }),
  actions: {
    connect(): void {
      if (
        this._socket &&
        (this._socket.readyState === WebSocket.OPEN ||
          this._socket.readyState === WebSocket.CONNECTING)
      ) {
        return;
      }

      this._manualDisconnect = false;
      this._clearReconnectTimer();

      const socket = new WebSocket(resolveWebSocketUrl());
      this._socket = socket;

      socket.onopen = () => {
        this.connected = true;
        this._startHeartbeat();
      };

      socket.onmessage = (event) => {
        this._handleIncomingMessage(event.data);
      };

      socket.onerror = () => {
        this.connected = false;
      };

      socket.onclose = () => {
        this.connected = false;
        this._socket = null;
        this._clearHeartbeatTimer();

        if (!this._manualDisconnect) {
          this._reconnectTimer = window.setTimeout(() => {
            this.connect();
          }, RECONNECT_DELAY_MS);
        }
      };
    },

    disconnect(): void {
      this._manualDisconnect = true;
      this._clearReconnectTimer();
      this._clearHeartbeatTimer();
      this.connected = false;

      if (this._socket) {
        this._socket.close();
        this._socket = null;
      }
    },

    subscribe(key: string, callback: TaskEventCallback): () => void {
      const subscribers = this._subscribers.get(key) ?? new Set<TaskEventCallback>();
      subscribers.add(callback);
      this._subscribers.set(key, subscribers);

      return () => {
        this.unsubscribe(key, callback);
      };
    },

    unsubscribe(key: string, callback: TaskEventCallback): void {
      const subscribers = this._subscribers.get(key);
      if (!subscribers) {
        return;
      }

      subscribers.delete(callback);
      if (subscribers.size === 0) {
        this._subscribers.delete(key);
      }
    },

    subscribeToType(type: TaskEventType, callback: TaskEventCallback): () => void {
      const subscribers = this._typeSubscribers.get(type) ?? new Set<TaskEventCallback>();
      subscribers.add(callback);
      this._typeSubscribers.set(type, subscribers);

      return () => {
        this.unsubscribeFromType(type, callback);
      };
    },

    unsubscribeFromType(type: TaskEventType, callback: TaskEventCallback): void {
      const subscribers = this._typeSubscribers.get(type);
      if (!subscribers) {
        return;
      }

      subscribers.delete(callback);
      if (subscribers.size === 0) {
        this._typeSubscribers.delete(type);
      }
    },

    _handleIncomingMessage(data: string): void {
      try {
        const parsed = JSON.parse(data) as unknown;
        if (!isRuntimeEvent(parsed)) {
          return;
        }

        const event = parsed as TaskEvent;
        const keys = collectEventKeys(event);

        keys.forEach((key) => {
          this.lastEvents.set(key, event);
        });

        const nextTask = buildTaskInfo(
          event,
          typeof event.taskId === "string" ? this.tasks.get(event.taskId) : undefined
        );
        if (nextTask) {
          this.tasks.set(nextTask.id, nextTask);
        }

        keys.forEach((key) => {
          const subscribers = this._subscribers.get(key);
          subscribers?.forEach((callback) => callback(event));
        });

        const typeSubscribers = this._typeSubscribers.get(event.type);
        typeSubscribers?.forEach((callback) => callback(event));
      } catch (error) {
        console.error("解析任务 WebSocket 消息失败:", error);
      }
    },

    _startHeartbeat(): void {
      this._clearHeartbeatTimer();
      this._heartbeatTimer = window.setInterval(() => {
        if (this._socket?.readyState === WebSocket.OPEN) {
          this._socket.send("ping");
        }
      }, HEARTBEAT_INTERVAL_MS);
    },

    _clearReconnectTimer(): void {
      if (this._reconnectTimer !== null) {
        window.clearTimeout(this._reconnectTimer);
        this._reconnectTimer = null;
      }
    },

    _clearHeartbeatTimer(): void {
      if (this._heartbeatTimer !== null) {
        window.clearInterval(this._heartbeatTimer);
        this._heartbeatTimer = null;
      }
    }
  }
});
