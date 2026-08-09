import {
  inject,
  onBeforeUnmount,
  onMounted,
  ref,
  watch
} from "vue";
import {
  useRoute,
  useRouter,
  type LocationQueryRaw
} from "vue-router";

import { accountUnsavedGuardRegistrarKey } from "@/modules/accounts/account-guard-port";
import {
  logAIConfigError,
  toAIConfigUiError,
  useCompositionTemplateStore,
  usePromptConfigStore,
  useSystemDiagnosticsStore
} from "@/modules/system/ai-config";
import type {
  AICapabilitySurface,
  AISystemPrimarySection
} from "@/modules/system/ai-config/ai-config-types";

type PendingView = {
  primary: AISystemPrimarySection;
  surface: AICapabilitySurface;
};

export function useAISystemPage() {
  const route = useRoute();
  const router = useRouter();
  const registrar = inject(accountUnsavedGuardRegistrarKey, null);
  const promptStore = usePromptConfigStore();
  const templateStore = useCompositionTemplateStore();
  const diagnosticsStore = useSystemDiagnosticsStore();
  const primary = ref<AISystemPrimarySection>(readPrimary(route.query.section));
  const surface = ref<AICapabilitySurface>(readSurface(route.query.surface));
  const compact = ref(readCompact());
  const tooNarrow = ref(readTooNarrow());
  const guardOpen = ref(false);
  const guardBusy = ref(false);
  const pageError = ref<string | null>(null);
  const pendingView = ref<PendingView | null>(null);
  let unregisterGuard: (() => void) | null = null;

  watch(
    () => [route.query.section, route.query.surface] as const,
    ([section, nextSurface]) => {
      primary.value = readPrimary(section);
      surface.value = readSurface(nextSurface);
    }
  );

  onMounted(() => {
    window.addEventListener("resize", updateWindowClass);
    unregisterGuard =
      registrar?.register({
        id: "ai-system-editors",
        label: "AI 系统版本编辑器",
        isDirty: hasUnsaved,
        save: saveUnsaved,
        discard: discardUnsaved
      }) ?? null;
    const logId = readString(route.query.log_id);
    if (logId) {
      void openLog(logId);
    }
  });

  onBeforeUnmount(() => {
    window.removeEventListener("resize", updateWindowClass);
    unregisterGuard?.();
  });

  function requestPrimary(next: AISystemPrimarySection): void {
    requestView({ primary: next, surface: surface.value });
  }

  function requestSurface(next: AICapabilitySurface): void {
    requestView({ primary: "ai", surface: next });
  }

  function requestView(next: PendingView): void {
    if (
      next.primary === primary.value
      && next.surface === surface.value
    ) {
      return;
    }
    if (hasUnsaved()) {
      pendingView.value = next;
      guardOpen.value = true;
      return;
    }
    void applyView(next);
  }

  async function applyView(next: PendingView): Promise<void> {
    pageError.value = null;
    primary.value = next.primary;
    surface.value = next.surface;
    const query = { ...route.query };
    query.section = next.primary;
    if (next.primary === "ai") query.surface = next.surface;
    else delete query.surface;
    delete query.log_id;
    try {
      await router.replace({ query });
    } catch (error) {
      logAIConfigError("同步设置页地址失败。", error);
      pageError.value = toAIConfigUiError(
        error,
        "设置页地址同步失败，请重试。"
      ).message;
    }
  }

  function hasUnsaved(): boolean {
    return promptStore.dirty || templateStore.dirty;
  }

  async function saveUnsaved(): Promise<void> {
    if (promptStore.dirty && !await promptStore.saveDraft()) {
      throw new Error(promptStore.error?.message ?? "Prompt 保存失败。");
    }
    if (templateStore.dirty && !await templateStore.saveDraft()) {
      throw new Error(templateStore.error?.message ?? "合成模板保存失败。");
    }
  }

  function discardUnsaved(): void {
    if (promptStore.dirty) promptStore.discardDraft();
    if (templateStore.dirty) templateStore.discardDraft();
  }

  async function saveAndContinue(): Promise<void> {
    guardBusy.value = true;
    try {
      await saveUnsaved();
      await finishGuard();
    } catch (error) {
      logAIConfigError("保存未完成，保留当前设置工作面。", error);
      pageError.value = toAIConfigUiError(
        error,
        "保存失败，已保留当前编辑内容。"
      ).message;
    } finally {
      guardBusy.value = false;
    }
  }

  async function discardAndContinue(): Promise<void> {
    discardUnsaved();
    await finishGuard();
  }

  async function finishGuard(): Promise<void> {
    const next = pendingView.value;
    cancelGuard();
    if (next) await applyView(next);
  }

  function cancelGuard(): void {
    guardOpen.value = false;
    pendingView.value = null;
  }

  async function openLog(logId: string): Promise<void> {
    pageError.value = null;
    primary.value = "diagnostics";
    const query: LocationQueryRaw = {
      ...route.query,
      section: "diagnostics",
      log_id: logId
    };
    delete query.surface;
    try {
      await router.replace({ query });
    } catch (error) {
      logAIConfigError("打开日志详情失败。", error);
      pageError.value = toAIConfigUiError(
        error,
        "日志详情地址同步失败，已继续尝试读取日志。"
      ).message;
    }
    diagnosticsStore.logIdInput = logId;
    if (diagnosticsStore.diagnosticsState === "idle") {
      await diagnosticsStore.loadDiagnostics();
    }
    await diagnosticsStore.lookupLog(logId);
  }

  function updateWindowClass(): void {
    compact.value = readCompact();
    tooNarrow.value = readTooNarrow();
  }

  return {
    cancelGuard,
    compact,
    discardAndContinue,
    guardBusy,
    guardOpen,
    openLog,
    pageError,
    primary,
    requestPrimary,
    requestSurface,
    saveAndContinue,
    surface,
    tooNarrow
  };
}

function readPrimary(value: unknown): AISystemPrimarySection {
  const normalized = readString(value);
  return normalized === "runtime" || normalized === "diagnostics"
    ? normalized
    : "ai";
}

function readSurface(value: unknown): AICapabilitySurface {
  const normalized = readString(value);
  return normalized === "models" || normalized === "prompts"
    ? normalized
    : "providers";
}

function readString(value: unknown): string | null {
  if (Array.isArray(value)) return typeof value[0] === "string" ? value[0] : null;
  return typeof value === "string" ? value : null;
}

function readCompact(): boolean {
  return typeof window !== "undefined" && window.innerWidth < 1024;
}

function readTooNarrow(): boolean {
  return typeof window !== "undefined" && window.innerWidth < 960;
}
