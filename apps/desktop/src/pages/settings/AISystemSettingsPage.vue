<template>
  <section class="settings-console">
    <SettingsStatusDock
      :config-status-label="configStatusLabel"
      :configured-provider-count="configuredProviderCount"
      :enabled-capability-count="enabledCapabilityCount"
      :last-synced-label="lastSyncedLabel"
      :license-label="licenseLabel"
      :provider-count="capabilityStore.providerCatalog.length"
      :revision-label="settings?.revision ?? '-'"
      :runtime-status-label="runtimeStatusLabel"
      :version-label="store.health?.version ?? '-'"
    />

    <p v-if="store.error" class="settings-page__error">
      {{ errorSummary }}
    </p>
    <p v-if="capabilityStore.error" class="settings-page__error">
      {{ capabilityErrorSummary }}
    </p>

    <div class="settings-console__body">
      <SettingsSectionRail :current-section="currentSection" @select="currentSection = $event" />

      <div class="settings-console__workspace">
        <header class="settings-console__workspace-header">
          <div>
            <p class="detail-panel__label">{{ sectionEyebrow }}</p>
            <h2>{{ sectionTitle }}</h2>
            <p class="workspace-page__summary">{{ sectionSummary }}</p>
          </div>
        </header>

        <SettingsSystemFormPanel
          v-if="currentSection === 'system'"
          :disabled="isDisabled"
          :form="form"
          :model-options="defaultProviderModels"
          :provider-options="capabilityStore.providerCatalog"
          @pick-directory="handlePickDirectory"
        />

        <ProviderCatalogPanel
          v-else-if="currentSection === 'provider'"
          :health-model="selectedProviderHealthModel"
          :provider-catalog="capabilityStore.providerCatalog"
          :provider-draft="selectedProviderDraft"
          :selected-provider-health="selectedProviderHealth"
          :selected-provider-id="selectedProviderId"
          :selected-provider-models="selectedProviderModels"
          :secret-status="selectedProviderSecretStatus"
          @check-provider="handleCheckProvider"
          @refresh-models="handleRefreshProviderModels"
          @save-provider-secret="handleSaveProviderSecret"
          @select-provider="selectProvider"
          @update:health-model="selectedProviderHealthModel = $event"
        />

        <div v-else-if="currentSection === 'capability'" class="settings-console__capability-layout">
          <AICapabilityMatrix
            :capabilities="capabilityForms"
            :capability-labels="capabilityLabels"
            :disabled="isCapabilityDisabled"
            :selected-capability-id="selectedCapabilityId"
            @select="selectCapability"
          />
          <AICapabilityInspector
            :capability="selectedCapability"
            :capability-label="selectedCapabilityLabel"
            :disabled="isCapabilityDisabled"
            :provider-catalog="capabilityStore.providerCatalog"
            :support-item="selectedSupportItem"
          />
        </div>

        <div v-else class="settings-console__diagnostics-placeholder">
          <section class="command-panel settings-card settings-console__diagnostics-card">
            <p class="detail-panel__label">诊断抽屉</p>
            <h2>诊断信息已移入右侧抽屉</h2>
            <p class="workspace-page__summary">
              当前主区只保留操作入口，目录、运行边界、Provider 连通性和最近一次测试结果统一放到右侧抽屉。
            </p>

            <div class="settings-console__diagnostics-metrics">
              <div class="detail-panel__metric">
                <span>已配置 Provider</span>
                <strong>{{ configuredProviderCount }}/{{ capabilityStore.providerCatalog.length }}</strong>
              </div>
              <div class="detail-panel__metric">
                <span>已启用能力</span>
                <strong>{{ enabledCapabilityCount }}</strong>
              </div>
              <div class="detail-panel__metric">
                <span>最近同步</span>
                <strong>{{ lastSyncedLabel }}</strong>
              </div>
            </div>

            <div class="editor-card__actions">
              <button
                class="settings-page__button"
                type="button"
                data-action="open-diagnostics-drawer"
                @click="shellUiStore.openDetailPanel()"
              >
                打开右侧抽屉
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>

    <SettingsSaveBar
      :capability-dirty="capabilityDirty"
      :is-capability-saving="capabilityStore.status === 'saving'"
      :is-system-saving="store.status === 'saving'"
      :system-dirty="systemDirty"
      :visible="systemDirty || capabilityDirty"
      @save-capabilities="handleSaveCapabilities"
      @save-system="handleSave"
    />
  </section>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, reactive, ref, watch } from "vue";

import AICapabilityInspector from "@/modules/settings/components/AICapabilityInspector.vue";
import AICapabilityMatrix from "@/modules/settings/components/AICapabilityMatrix.vue";
import ProviderCatalogPanel from "@/modules/settings/components/ProviderCatalogPanel.vue";
import SettingsSaveBar from "@/modules/settings/components/SettingsSaveBar.vue";
import SettingsSectionRail from "@/modules/settings/components/SettingsSectionRail.vue";
import SettingsStatusDock from "@/modules/settings/components/SettingsStatusDock.vue";
import SettingsSystemFormPanel from "@/modules/settings/components/SettingsSystemFormPanel.vue";
import { useAICapabilityStore } from "@/stores/ai-capability";
import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { useShellUiStore } from "@/stores/shell-ui";
import type {
  AICapabilityConfig,
  AICapabilitySupportItem,
  AIProviderSecretInput,
  AppSettings,
  AppSettingsUpdateInput
} from "@/types/runtime";

type SettingsSectionId = "system" | "provider" | "capability" | "diagnostics";
type DirectoryField =
  | "runtime.workspaceRoot"
  | "paths.cacheDir"
  | "paths.exportDir"
  | "paths.logDir";

const store = useConfigBusStore();
const capabilityStore = useAICapabilityStore();
const licenseStore = useLicenseStore();
const shellUiStore = useShellUiStore();
const { settings } = storeToRefs(store);
const form = reactive<AppSettingsUpdateInput>(createEmptySettingsInput());
const capabilityForms = ref<AICapabilityConfig[]>([]);
const currentSection = ref<SettingsSectionId>("provider");
const selectedCapabilityId = ref("script_generation");
const selectedProviderId = ref("openai");
const providerDrafts = reactive<Record<string, { apiKey: string; baseUrl: string }>>({});
const providerHealthModelDrafts = reactive<Record<string, string>>({});

const capabilityLabels: Record<string, string> = {
  script_generation: "脚本生成",
  script_rewrite: "脚本改写",
  storyboard_generation: "分镜生成",
  tts_generation: "配音生成",
  subtitle_alignment: "字幕对齐",
  video_generation: "视频生成",
  asset_analysis: "资产分析"
};

const isDisabled = computed(() => store.status === "saving" || settings.value === null);
const isCapabilityDisabled = computed(
  () => capabilityStore.status === "loading" || capabilityStore.status === "saving"
);
const configuredProviderCount = computed(
  () => capabilityStore.providerCatalog.filter((provider) => provider.configured).length
);
const enabledCapabilityCount = computed(() => capabilityForms.value.filter((item) => item.enabled).length);
const selectedCapability = computed(
  () => capabilityForms.value.find((item) => item.capabilityId === selectedCapabilityId.value) ?? null
);
const selectedCapabilityLabel = computed(() =>
  selectedCapability.value ? capabilityLabel(selectedCapability.value.capabilityId) : "能力策略"
);
const supportMatrixItems = computed(() => capabilityStore.supportMatrix?.capabilities ?? []);
const selectedSupportItem = computed<AICapabilitySupportItem | null>(
  () =>
    supportMatrixItems.value.find((item) => item.capabilityId === selectedCapabilityId.value) ??
    null
);
const selectedProviderCatalogItem = computed(
  () => capabilityStore.providerCatalog.find((item) => item.provider === selectedProviderId.value) ?? null
);
const selectedProviderModels = computed(
  () => capabilityStore.modelCatalogByProvider[selectedProviderId.value] ?? []
);
const selectedProviderLabel = computed(() => selectedProviderCatalogItem.value?.label ?? "未选择 Provider");
const selectedProviderHealth = computed(
  () => capabilityStore.providerHealth[selectedProviderId.value] ?? null
);
const selectedProviderSecretStatus = computed(
  () =>
    capabilityStore.settings?.providers?.find((item) => item.provider === selectedProviderId.value) ??
    null
);
const selectedProviderDraft = computed(() =>
  ensureProviderDraft(
    selectedProviderId.value,
    selectedProviderSecretStatus.value?.baseUrl ?? selectedProviderCatalogItem.value?.baseUrl ?? ""
  )
);
const selectedProviderHealthModel = computed({
  get: () => providerHealthModelDrafts[selectedProviderId.value] ?? "",
  set: (value: string) => {
    providerHealthModelDrafts[selectedProviderId.value] = value;
  }
});
const defaultProviderModels = computed(
  () => capabilityStore.modelCatalogByProvider[form.ai.provider] ?? []
);
const runtimeStatusLabel = computed(() => {
  switch (store.runtimeStatus) {
    case "online":
      return "在线";
    case "loading":
      return "读取中";
    case "offline":
      return "离线";
    default:
      return "待检查";
  }
});
const configStatusLabel = computed(() => {
  switch (store.status) {
    case "loading":
      return "配置读取中";
    case "saving":
      return "配置保存中";
    case "ready":
      return "配置已就绪";
    case "error":
      return "配置异常";
    default:
      return "等待配置";
  }
});
const licenseLabel = computed(() => (licenseStore.active ? "已授权" : "待授权"));
const lastSyncedLabel = computed(() => formatDateOnly(store.lastSyncedAt || store.health?.now || ""));
const errorSummary = computed(() => formatErrorSummary(store.error));
const capabilityErrorSummary = computed(() => formatErrorSummary(capabilityStore.error));
const sectionEyebrow = computed(() => {
  return (
    {
      system: "系统总线",
      provider: "Provider 与模型",
      capability: "能力策略",
      diagnostics: "诊断台"
    }[currentSection.value] ?? "AI 与系统设置"
  );
});
const sectionTitle = computed(() => {
  return (
    {
      system: "集中维护 Runtime、目录和默认模型",
      provider: "管理多 Provider、模型目录与连接凭据",
      capability: "按能力配置 Provider、模型和提示词",
      diagnostics: "把诊断和连通性统一收进右侧抽屉"
    }[currentSection.value] ?? "AI 与系统设置"
  );
});
const sectionSummary = computed(() => {
  return (
    {
      system: "系统配置和默认模型统一通过配置总线保存，不让页面各自写一套本地状态。",
      provider: "主流商业模型、OpenAI-compatible 和本地模型都通过 Runtime 注册表接入，先选 Provider 再配置细节。",
      capability: "能力矩阵负责选中对象，右侧 Inspector 负责细节，不再把所有提示词一次性摊开。",
      diagnostics: "页面主区不再堆系统诊断，右侧抽屉集中显示运行边界、最新测试和当前异常。"
    }[currentSection.value] ?? ""
  );
});
const systemDirty = computed(() => {
  if (!settings.value) {
    return false;
  }

  return serializeSettings(cloneSettingsInput(form)) !== serializeSettings(settingsToInput(settings.value));
});
const capabilityDirty = computed(() => {
  if (!capabilityStore.settings) {
    return false;
  }

  return (
    serializeCapabilities(capabilityForms.value) !==
    serializeCapabilities(capabilityStore.settings.capabilities)
  );
});

watch(
  settings,
  (value) => {
    if (!value) {
      return;
    }

    applySettingsToForm(form, value);
  },
  { immediate: true }
);

watch(
  () => capabilityStore.settings,
  (value) => {
    capabilityForms.value = (value?.capabilities ?? []).map((item) => ({ ...item }));
    if (capabilityForms.value.length > 0) {
      const hasSelected = capabilityForms.value.some(
        (item) => item.capabilityId === selectedCapabilityId.value
      );
      if (!hasSelected) {
        selectedCapabilityId.value = capabilityForms.value[0].capabilityId;
      }
    }
  },
  { immediate: true }
);

watch(
  () => [selectedProviderId.value, selectedProviderSecretStatus.value?.baseUrl, selectedProviderCatalogItem.value?.baseUrl],
  ([providerId, secretBaseUrl, catalogBaseUrl]) => {
    ensureProviderDraft(providerId as string, (secretBaseUrl as string) || (catalogBaseUrl as string) || "");
  },
  { immediate: true }
);

watch(
  () => currentSection.value,
  (section) => {
    if (section === "diagnostics") {
      shellUiStore.openDetailPanel();
    }
  }
);

watch(
  () => form.ai.provider,
  async (providerId) => {
    if (!providerId) {
      form.ai.model = "";
      return;
    }

    if (!capabilityStore.modelCatalogByProvider[providerId]) {
      await capabilityStore.loadProviderModels(providerId);
    }

    const nextModels = capabilityStore.modelCatalogByProvider[providerId] ?? [];
    if (nextModels.length === 0) {
      form.ai.model = "";
      return;
    }

    const hasCurrent = nextModels.some((item) => item.modelId === form.ai.model);
    if (!hasCurrent) {
      form.ai.model = nextModels[0].modelId;
    }
  },
  { immediate: true }
);

watch(
  () => [selectedProviderId.value, selectedProviderModels.value.map((item) => item.modelId).join("|"), form.ai.provider, form.ai.model],
  () => {
    const models = selectedProviderModels.value;
    const current = providerHealthModelDrafts[selectedProviderId.value];
    if (models.length === 0) {
      providerHealthModelDrafts[selectedProviderId.value] = "";
      return;
    }

    const fallback =
      selectedProviderId.value === form.ai.provider && models.some((item) => item.modelId === form.ai.model)
        ? form.ai.model
        : models[0].modelId;

    if (!current || !models.some((item) => item.modelId === current)) {
      providerHealthModelDrafts[selectedProviderId.value] = fallback;
    }
  },
  { immediate: true }
);

onMounted(() => {
  void hydrateCapabilityContext();
});

async function handleSave(): Promise<void> {
  await store.save(cloneSettingsInput(form));
}

async function handleSaveCapabilities(): Promise<void> {
  await capabilityStore.saveCapabilities(capabilityForms.value.map((item) => ({ ...item })));
}

async function handleSaveProviderSecret(): Promise<void> {
  if (!selectedProviderId.value) {
    return;
  }

  const draft = ensureProviderDraft(selectedProviderId.value);
  const input: AIProviderSecretInput = {
    apiKey: draft.apiKey.trim(),
    baseUrl: draft.baseUrl.trim() || undefined
  };
  await capabilityStore.saveProviderSecret(selectedProviderId.value, input);
  draft.apiKey = "";
}

async function handleCheckProvider(): Promise<void> {
  if (!selectedProviderId.value) {
    return;
  }

  await capabilityStore.checkProvider(
    selectedProviderId.value,
    selectedProviderHealthModel.value || undefined
  );
  shellUiStore.openDetailPanel();
}

async function handleRefreshProviderModels(): Promise<void> {
  if (!selectedProviderId.value) {
    return;
  }

  await capabilityStore.loadProviderModels(selectedProviderId.value);
}

async function handlePickDirectory(field: DirectoryField): Promise<void> {
  const currentValue =
    field === "runtime.workspaceRoot"
      ? form.runtime.workspaceRoot
      : field === "paths.cacheDir"
        ? form.paths.cacheDir
        : field === "paths.exportDir"
          ? form.paths.exportDir
          : form.paths.logDir;
  const selected = await pickDirectoryPath(currentValue);
  if (!selected) {
    return;
  }

  if (field === "runtime.workspaceRoot") {
    form.runtime.workspaceRoot = selected;
  } else if (field === "paths.cacheDir") {
    form.paths.cacheDir = selected;
  } else if (field === "paths.exportDir") {
    form.paths.exportDir = selected;
  } else {
    form.paths.logDir = selected;
  }
}

async function hydrateCapabilityContext(): Promise<void> {
  const tasks: Array<Promise<void>> = [];
  if (store.status === "idle") {
    tasks.push(store.load());
  }
  if (licenseStore.status === "idle") {
    tasks.push(licenseStore.loadStatus());
  }
  if (capabilityStore.status === "idle") {
    tasks.push(capabilityStore.load());
  }
  tasks.push(capabilityStore.loadProviderCatalog());
  tasks.push(capabilityStore.loadSupportMatrix());
  await Promise.all(tasks);

  const firstProvider = capabilityStore.providerCatalog[0]?.provider ?? selectedProviderId.value;
  selectedProviderId.value = firstProvider;

  const providerIds = new Set<string>();
  if (firstProvider) {
    providerIds.add(firstProvider);
  }
  if (form.ai.provider) {
    providerIds.add(form.ai.provider);
  }

  await Promise.all(
    [...providerIds].map(async (providerId) => {
      await capabilityStore.loadProviderModels(providerId);
    })
  );
}

async function selectProvider(providerId: string): Promise<void> {
  selectedProviderId.value = providerId;
  await capabilityStore.loadProviderModels(providerId);
}

function selectCapability(capabilityId: string): void {
  selectedCapabilityId.value = capabilityId;
}

function capabilityLabel(capabilityId: string): string {
  return capabilityLabels[capabilityId] ?? capabilityId;
}

function ensureProviderDraft(providerId: string, fallbackBaseUrl = ""): {
  apiKey: string;
  baseUrl: string;
} {
  if (!providerDrafts[providerId]) {
    providerDrafts[providerId] = {
      apiKey: "",
      baseUrl: fallbackBaseUrl
    };
  } else if (!providerDrafts[providerId].baseUrl && fallbackBaseUrl) {
    providerDrafts[providerId].baseUrl = fallbackBaseUrl;
  }

  return providerDrafts[providerId];
}

function formatErrorSummary(
  error: { message: string; requestId: string } | null
): string {
  if (!error) {
    return "";
  }

  return error.requestId ? `${error.message}（${error.requestId}）` : error.message;
}

function createEmptySettingsInput(): AppSettingsUpdateInput {
  return {
    runtime: {
      mode: "",
      workspaceRoot: ""
    },
    paths: {
      cacheDir: "",
      exportDir: "",
      logDir: ""
    },
    logging: {
      level: "INFO"
    },
    ai: {
      provider: "",
      model: "",
      voice: "",
      subtitleMode: ""
    }
  };
}

function settingsToInput(source: AppSettings): AppSettingsUpdateInput {
  return {
    runtime: {
      mode: source.runtime.mode,
      workspaceRoot: source.runtime.workspaceRoot
    },
    paths: {
      cacheDir: source.paths.cacheDir,
      exportDir: source.paths.exportDir,
      logDir: source.paths.logDir
    },
    logging: {
      level: source.logging.level
    },
    ai: {
      provider: source.ai.provider,
      model: source.ai.model,
      voice: source.ai.voice,
      subtitleMode: source.ai.subtitleMode
    }
  };
}

function applySettingsToForm(target: AppSettingsUpdateInput, source: AppSettings): void {
  target.runtime.mode = source.runtime.mode;
  target.runtime.workspaceRoot = source.runtime.workspaceRoot;
  target.paths.cacheDir = source.paths.cacheDir;
  target.paths.exportDir = source.paths.exportDir;
  target.paths.logDir = source.paths.logDir;
  target.logging.level = source.logging.level;
  target.ai.provider = source.ai.provider;
  target.ai.model = source.ai.model;
  target.ai.voice = source.ai.voice;
  target.ai.subtitleMode = source.ai.subtitleMode;
}

function cloneSettingsInput(source: AppSettingsUpdateInput): AppSettingsUpdateInput {
  return {
    runtime: {
      mode: source.runtime.mode,
      workspaceRoot: source.runtime.workspaceRoot
    },
    paths: {
      cacheDir: source.paths.cacheDir,
      exportDir: source.paths.exportDir,
      logDir: source.paths.logDir
    },
    logging: {
      level: source.logging.level
    },
    ai: {
      provider: source.ai.provider,
      model: source.ai.model,
      voice: source.ai.voice,
      subtitleMode: source.ai.subtitleMode
    }
  };
}

function serializeSettings(input: AppSettingsUpdateInput): string {
  return JSON.stringify(input);
}

function serializeCapabilities(items: AICapabilityConfig[]): string {
  return JSON.stringify(
    items.map((item) => ({
      capabilityId: item.capabilityId,
      enabled: item.enabled,
      provider: item.provider,
      model: item.model,
      agentRole: item.agentRole,
      systemPrompt: item.systemPrompt,
      userPromptTemplate: item.userPromptTemplate
    }))
  );
}

function formatDateOnly(value: string): string {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

async function pickDirectoryPath(currentValue: string): Promise<string> {
  try {
    const dialogModuleName = "@tauri-apps/plugin-dialog";
    const dialog = await import(/* @vite-ignore */ dialogModuleName);
    const selected = await dialog.open({
      defaultPath: currentValue || undefined,
      directory: true,
      multiple: false
    });
    return typeof selected === "string" ? selected : "";
  } catch {
    return window.prompt("请输入本地目录路径", currentValue)?.trim() ?? "";
  }
}
</script>

<style scoped>
.settings-console {
  display: grid;
  gap: 16px;
  min-height: 100%;
}

.settings-console__body {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 16px;
  min-height: 0;
}

.settings-console__workspace {
  display: grid;
  align-content: start;
  gap: 16px;
  min-width: 0;
}

.settings-console__workspace-header {
  display: grid;
  gap: 8px;
  padding: 4px 2px 0;
}

.settings-console__workspace-header h2 {
  margin: 0;
}

.settings-console__capability-layout,
.settings-console__diagnostics-placeholder,
.settings-console__diagnostics-metrics {
  display: grid;
  gap: 16px;
}

.settings-console__capability-layout {
  grid-template-columns: minmax(300px, 0.8fr) minmax(0, 1.2fr);
}

.settings-console__diagnostics-card {
  display: grid;
  gap: 18px;
}

.settings-console__diagnostics-metrics {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

@media (max-width: 1120px) {
  .settings-console__body,
  .settings-console__capability-layout,
  .settings-console__diagnostics-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
