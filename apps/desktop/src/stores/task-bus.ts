import { defineStore } from "pinia";

import type { TaskEvent, TaskInfo } from "@/types/task-events";

type TaskEventCallback = (event: TaskEvent) => void;

type TaskBusState = {
  tasks: Map<string, TaskInfo>;
  connected: boolean;
  _socket: WebSocket | null;
  _subscribers: Map<string, Set<TaskEventCallback>>;
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

function isTaskEvent(value: unknown): value is TaskEvent {
  if (!value || typeof value !== "object") {
    return false;
  }

  const event = value as Partial<TaskEvent>;
  return (
    typeof event.type === "string" &&
    event.type.startsWith("task.") &&
    typeof event.taskId === "string" &&
    typeof event.taskType === "string"
  );
}

export const useTaskBusStore = defineStore("task-bus", {
  state: (): TaskBusState => ({
    tasks: new Map<string, TaskInfo>(),
    connected: false,
    _socket: null,
    _subscribers: new Map<string, Set<TaskEventCallback>>(),
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
        this._handleMessage(event.data);
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

    subscribe(taskId: string, callback: TaskEventCallback): () => void {
      const subscribers = this._subscribers.get(taskId) ?? new Set<TaskEventCallback>();
      subscribers.add(callback);
      this._subscribers.set(taskId, subscribers);

      return () => {
        this.unsubscribe(taskId, callback);
      };
    },

    unsubscribe(taskId: string, callback: TaskEventCallback): void {
      const subscribers = this._subscribers.get(taskId);
      if (!subscribers) {
        return;
      }

      subscribers.delete(callback);
      if (subscribers.size === 0) {
        this._subscribers.delete(taskId);
      }
    },

    _handleMessage(data: string): void {
      try {
        const parsed = JSON.parse(data) as unknown;
        if (!isTaskEvent(parsed)) {
          return;
        }

        const now = new Date().toISOString();
        const existing = this.tasks.get(parsed.taskId);
        this.tasks.set(parsed.taskId, {
          id: parsed.taskId,
          task_type: parsed.taskType,
          project_id: parsed.projectId,
          status: parsed.status,
          progress: parsed.progress,
          message: parsed.message,
          created_at: existing?.created_at ?? now,
          updated_at: now
        });

        const subscribers = this._subscribers.get(parsed.taskId);
        subscribers?.forEach((callback) => callback(parsed));
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
