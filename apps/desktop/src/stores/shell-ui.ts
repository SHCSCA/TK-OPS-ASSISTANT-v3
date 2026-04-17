import { defineStore } from "pinia";

export type ShellTheme = "light" | "dark";
export type DetailContextMode = "hidden" | "contextual" | "asset" | "logs" | "binding" | "settings";
export type DetailContextTone = "neutral" | "brand" | "success" | "warning" | "danger" | "info";
export type DetailContextSource = "route" | "asset-library" | "custom";

export type DetailContextBadge = {
  label: string;
  tone?: DetailContextTone;
};

export type DetailContextMetric = {
  id: string;
  label: string;
  value: string;
  hint?: string;
  tone?: DetailContextTone;
};

export type DetailContextField = {
  id: string;
  label: string;
  value: string;
  hint?: string;
  tone?: DetailContextTone;
  mono?: boolean;
  multiline?: boolean;
};

export type DetailContextItem = {
  id: string;
  title: string;
  description?: string;
  meta?: string;
  tone?: DetailContextTone;
  icon?: string;
};

export type DetailContextSection = {
  id: string;
  title: string;
  description?: string;
  emptyLabel?: string;
  fields?: DetailContextField[];
  items?: DetailContextItem[];
};

export type DetailContextAction = {
  id: string;
  label: string;
  icon?: string;
  tone?: DetailContextTone;
  disabled?: boolean;
};

export type DetailContext = {
  key: string;
  mode: DetailContextMode;
  source: DetailContextSource;
  icon?: string;
  eyebrow?: string;
  title: string;
  description?: string;
  badge?: DetailContextBadge;
  metrics?: DetailContextMetric[];
  sections: DetailContextSection[];
  actions?: DetailContextAction[];
};

type PersistedShellUiState = {
  theme: ShellTheme;
  reducedMotion: boolean;
  sidebarCollapsed: boolean;
  detailPanelOpen: boolean;
  detailContext: DetailContext;
};

const SHELL_UI_STORAGE_KEY = "tkops-shell-ui";

function getPreferredTheme(): ShellTheme {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return "dark";
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function getDefaultReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }

  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function createEmptyDetailContext(mode: DetailContextMode = "contextual"): DetailContext {
  return {
    key: `route:${mode}`,
    mode,
    source: "route",
    icon: "right_panel_open",
    eyebrow: "共享详情面板",
    title: "等待上下文",
    description: "当前页面尚未提供详情上下文。",
    sections: [
      {
        id: "empty",
        title: "面板状态",
        emptyLabel: "页面、模块或共享层可以通过 shell-ui 注入新的 detailContext。"
      }
    ]
  };
}

function createDefaultState(): PersistedShellUiState {
  return {
    theme: getPreferredTheme(),
    reducedMotion: getDefaultReducedMotion(),
    sidebarCollapsed: false,
    detailPanelOpen: false,
    detailContext: createEmptyDetailContext()
  };
}

function sanitizeTone(value: unknown): DetailContextTone | undefined {
  return ["neutral", "brand", "success", "warning", "danger", "info"].includes(String(value))
    ? (value as DetailContextTone)
    : undefined;
}

function sanitizeMode(value: unknown): DetailContextMode {
  return ["hidden", "contextual", "asset", "logs", "binding", "settings"].includes(String(value))
    ? (value as DetailContextMode)
    : "contextual";
}

function sanitizeField(field: Partial<DetailContextField>, index: number): DetailContextField {
  return {
    id: typeof field.id === "string" && field.id.length > 0 ? field.id : `field-${index}`,
    label: typeof field.label === "string" ? field.label : "未命名字段",
    value: typeof field.value === "string" ? field.value : "",
    hint: typeof field.hint === "string" ? field.hint : undefined,
    tone: sanitizeTone(field.tone),
    mono: Boolean(field.mono),
    multiline: Boolean(field.multiline)
  };
}

function sanitizeItem(item: Partial<DetailContextItem>, index: number): DetailContextItem {
  return {
    id: typeof item.id === "string" && item.id.length > 0 ? item.id : `item-${index}`,
    title: typeof item.title === "string" ? item.title : "未命名项",
    description: typeof item.description === "string" ? item.description : undefined,
    meta: typeof item.meta === "string" ? item.meta : undefined,
    tone: sanitizeTone(item.tone),
    icon: typeof item.icon === "string" ? item.icon : undefined
  };
}

function sanitizeSection(section: Partial<DetailContextSection>, index: number): DetailContextSection {
  return {
    id: typeof section.id === "string" && section.id.length > 0 ? section.id : `section-${index}`,
    title: typeof section.title === "string" ? section.title : "未命名分组",
    description: typeof section.description === "string" ? section.description : undefined,
    emptyLabel: typeof section.emptyLabel === "string" ? section.emptyLabel : undefined,
    fields: Array.isArray(section.fields) ? section.fields.map(sanitizeField) : undefined,
    items: Array.isArray(section.items) ? section.items.map(sanitizeItem) : undefined
  };
}

function sanitizeMetric(metric: Partial<DetailContextMetric>, index: number): DetailContextMetric {
  return {
    id: typeof metric.id === "string" && metric.id.length > 0 ? metric.id : `metric-${index}`,
    label: typeof metric.label === "string" ? metric.label : "未命名指标",
    value: typeof metric.value === "string" ? metric.value : "",
    hint: typeof metric.hint === "string" ? metric.hint : undefined,
    tone: sanitizeTone(metric.tone)
  };
}

function sanitizeAction(action: Partial<DetailContextAction>, index: number): DetailContextAction {
  return {
    id: typeof action.id === "string" && action.id.length > 0 ? action.id : `action-${index}`,
    label: typeof action.label === "string" ? action.label : "未命名动作",
    icon: typeof action.icon === "string" ? action.icon : undefined,
    tone: sanitizeTone(action.tone),
    disabled: Boolean(action.disabled)
  };
}

function sanitizeDetailContext(value: unknown): DetailContext {
  const fallback = createEmptyDetailContext();
  if (!value || typeof value !== "object") {
    return fallback;
  }

  const detail = value as Partial<DetailContext>;
  return {
    key: typeof detail.key === "string" && detail.key.length > 0 ? detail.key : fallback.key,
    mode: sanitizeMode(detail.mode),
    source: ["route", "asset-library", "custom"].includes(String(detail.source))
      ? (detail.source as DetailContextSource)
      : fallback.source,
    icon: typeof detail.icon === "string" ? detail.icon : fallback.icon,
    eyebrow: typeof detail.eyebrow === "string" ? detail.eyebrow : fallback.eyebrow,
    title: typeof detail.title === "string" && detail.title.length > 0 ? detail.title : fallback.title,
    description: typeof detail.description === "string" ? detail.description : fallback.description,
    badge:
      detail.badge && typeof detail.badge === "object" && typeof detail.badge.label === "string"
        ? {
            label: detail.badge.label,
            tone: sanitizeTone(detail.badge.tone) ?? "neutral"
          }
        : undefined,
    metrics: Array.isArray(detail.metrics) ? detail.metrics.map(sanitizeMetric) : undefined,
    sections: Array.isArray(detail.sections) && detail.sections.length > 0
      ? detail.sections.map(sanitizeSection)
      : fallback.sections,
    actions: Array.isArray(detail.actions) ? detail.actions.map(sanitizeAction) : undefined
  };
}

function readPersistedState(): PersistedShellUiState {
  const fallbackState = createDefaultState();
  if (typeof window === "undefined") {
    return fallbackState;
  }

  const rawValue = window.localStorage.getItem(SHELL_UI_STORAGE_KEY);
  if (!rawValue) {
    return fallbackState;
  }

  try {
    const parsedValue = JSON.parse(rawValue) as Partial<PersistedShellUiState>;
    return {
      theme: parsedValue.theme === "light" ? "light" : parsedValue.theme === "dark" ? "dark" : fallbackState.theme,
      reducedMotion:
        typeof parsedValue.reducedMotion === "boolean"
          ? parsedValue.reducedMotion
          : fallbackState.reducedMotion,
      sidebarCollapsed:
        typeof parsedValue.sidebarCollapsed === "boolean"
          ? parsedValue.sidebarCollapsed
          : fallbackState.sidebarCollapsed,
      detailPanelOpen:
        typeof parsedValue.detailPanelOpen === "boolean"
          ? parsedValue.detailPanelOpen
          : typeof (parsedValue as { isDetailPanelOpen?: boolean }).isDetailPanelOpen === "boolean"
            ? Boolean((parsedValue as { isDetailPanelOpen?: boolean }).isDetailPanelOpen)
            : fallbackState.detailPanelOpen,
      detailContext: sanitizeDetailContext(parsedValue.detailContext)
    };
  } catch {
    return fallbackState;
  }
}

function persistState(state: PersistedShellUiState) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    SHELL_UI_STORAGE_KEY,
    JSON.stringify({
      theme: state.theme,
      reducedMotion: state.reducedMotion,
      sidebarCollapsed: state.sidebarCollapsed,
      detailPanelOpen: state.detailPanelOpen,
      detailContext: state.detailContext
    })
  );
}

export const useShellUiStore = defineStore("shell-ui", {
  state: (): PersistedShellUiState => readPersistedState(),
  getters: {
    isDetailPanelOpen(state) {
      return state.detailPanelOpen;
    }
  },
  actions: {
    persist() {
      persistState({
        theme: this.theme,
        reducedMotion: this.reducedMotion,
        sidebarCollapsed: this.sidebarCollapsed,
        detailPanelOpen: this.detailPanelOpen,
        detailContext: this.detailContext
      });
    },
    setTheme(theme: ShellTheme) {
      this.theme = theme;
      this.persist();
    },
    toggleTheme() {
      this.setTheme(this.theme === "dark" ? "light" : "dark");
    },
    syncReducedMotionPreference() {
      if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
        return;
      }

      this.reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      this.persist();
    },
    setReducedMotion(reducedMotion: boolean) {
      this.reducedMotion = reducedMotion;
      this.persist();
    },
    toggleReducedMotion() {
      this.setReducedMotion(!this.reducedMotion);
    },
    setSidebarCollapsed(sidebarCollapsed: boolean) {
      this.sidebarCollapsed = sidebarCollapsed;
      this.persist();
    },
    toggleSidebar() {
      this.setSidebarCollapsed(!this.sidebarCollapsed);
    },
    setDetailPanelOpen(detailPanelOpen: boolean) {
      this.detailPanelOpen = detailPanelOpen;
      this.persist();
    },
    openDetailPanel() {
      this.setDetailPanelOpen(true);
    },
    closeDetailPanel() {
      this.setDetailPanelOpen(false);
    },
    toggleDetailPanel() {
      this.setDetailPanelOpen(!this.detailPanelOpen);
    },
    setDetailContext(detailContext: DetailContext) {
      this.detailContext = sanitizeDetailContext(detailContext);
      this.persist();
    },
    patchDetailContext(partial: Partial<DetailContext>) {
      this.detailContext = sanitizeDetailContext({
        ...this.detailContext,
        ...partial
      });
      this.persist();
    },
    clearDetailContext(mode: DetailContextMode = "contextual") {
      this.detailContext = createEmptyDetailContext(mode);
      this.persist();
    },
    openDetailWithContext(detailContext: DetailContext) {
      this.setDetailContext(detailContext);
      this.openDetailPanel();
    }
  }
});

export function createRouteDetailContext(
  mode: DetailContextMode,
  context: Omit<DetailContext, "key" | "mode" | "source">
): DetailContext {
  return sanitizeDetailContext({
    key: `route:${mode}:${context.title}`,
    mode,
    source: "route",
    ...context
  });
}
