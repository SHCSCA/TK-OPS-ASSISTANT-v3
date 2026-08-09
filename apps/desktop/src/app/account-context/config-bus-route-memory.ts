import { shallowReactive } from "vue";

import { RuntimeError } from "@/app/runtime-client/core";
import {
  fetchSystemConfig,
  patchSystemConfig
} from "@/app/runtime-client/system-config";

import type {
  AccountContextError,
  AccountRouteMemoryPort
} from "./types";

export type UiThemePreference = "light" | "dark" | "system";

export type AccountUiConfigState = {
  status: "idle" | "loading" | "ready" | "saving" | "error";
  revision: number;
  lastAccountId: string | null;
  recentPages: Record<string, string>;
  compactWindow: boolean;
  theme: UiThemePreference;
  error: AccountContextError | null;
};

export class AccountUiConfigGateway {
  private loadPromise: Promise<void> | null = null;

  readonly state = shallowReactive<AccountUiConfigState>({
    status: "idle",
    revision: 0,
    lastAccountId: null,
    recentPages: {},
    compactWindow: false,
    theme: "system",
    error: null
  });

  readonly routeMemory: AccountRouteMemoryPort = {
    loadLastRoutes: async (signal) => {
      await this.load(signal);
      return { ...this.state.recentPages };
    },
    saveLastRoute: async (accountId, route, signal) => {
      await this.patch(
        {
          "ui.recentPages": {
            ...this.state.recentPages,
            [accountId]: route
          }
        },
        signal
      );
    },
    removeLastRoute: async (accountId, signal) => {
      const recentPages = { ...this.state.recentPages };
      delete recentPages[accountId];
      await this.patch({ "ui.recentPages": recentPages }, signal);
    }
  };

  async load(signal?: AbortSignal): Promise<void> {
    if (this.loadPromise) {
      return this.loadPromise;
    }
    const operation = this.performLoad(signal);
    this.loadPromise = operation;
    try {
      await operation;
    } finally {
      if (this.loadPromise === operation) {
        this.loadPromise = null;
      }
    }
  }

  private async performLoad(signal?: AbortSignal): Promise<void> {
    this.state.status = "loading";
    this.state.error = null;
    try {
      const result = await fetchSystemConfig({
        prefix: "ui.",
        signal
      });
      this.apply(result.data.values, result.data.revision);
    } catch (error) {
      this.applyError(error, "读取界面配置失败，请稍后重试。");
      throw error;
    }
  }

  async setActiveAccount(
    accountId: string | null,
    route?: string,
    signal?: AbortSignal
  ): Promise<void> {
    const values: Record<string, unknown> = {
      "ui.lastAccountId": accountId
    };
    if (accountId && route) {
      values["ui.recentPages"] = {
        ...this.state.recentPages,
        [accountId]: route
      };
    }
    await this.patch(values, signal);
  }

  async setTheme(
    theme: UiThemePreference,
    signal?: AbortSignal
  ): Promise<void> {
    await this.patch({ "ui.theme": theme }, signal);
  }

  async toggleTheme(): Promise<void> {
    const resolved = resolveTheme(this.state.theme);
    await this.setTheme(resolved === "dark" ? "light" : "dark");
  }

  async patch(
    values: Record<string, unknown>,
    signal?: AbortSignal
  ): Promise<void> {
    await this.ensureLoaded(signal);
    this.state.status = "saving";
    this.state.error = null;
    try {
      const result = await patchSystemConfig(
        { values },
        {
          expectedRevision: this.state.revision,
          signal
        }
      );
      this.apply(result.data.values, result.data.revision);
    } catch (error) {
      if (isRevisionConflict(error)) {
        try {
          await this.load(signal);
          const result = await patchSystemConfig(
            { values },
            {
              expectedRevision: this.state.revision,
              signal
            }
          );
          this.apply(result.data.values, result.data.revision);
          return;
        } catch (retryError) {
          this.applyError(
            retryError,
            "界面配置已被其他操作更新，请重新加载后再试。"
          );
          throw retryError;
        }
      }
      this.applyError(error, "保存界面配置失败，请稍后重试。");
      throw error;
    }
  }

  private async ensureLoaded(signal?: AbortSignal): Promise<void> {
    if (this.state.status === "idle" || this.state.status === "error") {
      await this.load(signal);
    }
  }

  private apply(values: Record<string, unknown>, revision: number): void {
    this.state.revision = revision;
    this.state.lastAccountId = readLastAccountId(values["ui.lastAccountId"]);
    this.state.recentPages = readRecentPages(values["ui.recentPages"]);
    this.state.compactWindow =
      typeof values["ui.compactWindow"] === "boolean"
        ? values["ui.compactWindow"]
        : false;
    this.state.theme = readTheme(values["ui.theme"]);
    this.state.status = "ready";
    this.state.error = null;
    applyTheme(this.state.theme);
  }

  private applyError(error: unknown, fallback: string): void {
    this.state.status = "error";
    this.state.error = toConfigError(error, fallback);
  }
}

function readLastAccountId(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function readRecentPages(value: unknown): Record<string, string> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  const result: Record<string, string> = {};
  for (const [accountId, route] of Object.entries(value)) {
    if (
      accountId.length > 0
      && accountId.length <= 128
      && typeof route === "string"
      && route.startsWith("/")
      && !route.startsWith("//")
      && route.length <= 256
    ) {
      result[accountId] = route;
    }
  }
  return result;
}

function readTheme(value: unknown): UiThemePreference {
  return value === "light" || value === "dark" || value === "system"
    ? value
    : "system";
}

function resolveTheme(theme: UiThemePreference): "light" | "dark" {
  if (theme !== "system") return theme;
  return (
    typeof window !== "undefined"
    && typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-color-scheme: dark)").matches
  )
    ? "dark"
    : "light";
}

function applyTheme(theme: UiThemePreference): void {
  if (typeof document !== "undefined") {
    document.documentElement.dataset.theme = resolveTheme(theme);
  }
}

function isRevisionConflict(error: unknown): boolean {
  return (
    error instanceof RuntimeError
    && error.errorCode === "CONFIG_REVISION_CONFLICT"
  );
}

function toConfigError(
  error: unknown,
  fallback: string
): AccountContextError {
  if (error instanceof RuntimeError) {
    return {
      code: error.errorCode,
      message: error.message || fallback,
      logId: error.logId,
      requestId: error.requestId,
      status: error.status,
      retryable: error.status >= 500 || error.status === 409,
      stage: "committing"
    };
  }
  return {
    code: "INTERNAL_ERROR",
    message: fallback,
    logId: null,
    requestId: null,
    status: null,
    retryable: true,
    stage: "committing"
  };
}
