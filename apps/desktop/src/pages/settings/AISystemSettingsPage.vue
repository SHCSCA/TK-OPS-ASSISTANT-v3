<template>
  <section class="settings-console" data-testid="settings-console">
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

    <div v-if="pageBanner" class="settings-console__banner" :class="`settings-console__banner--${pageBannerTone}`">
      {{ pageBanner }}
    </div>

    <div class="settings-console__body">
      <SettingsSectionRail :current-section="currentSection" @select="currentSection = $event" />

      <main class="settings-console__workspace">
        <header class="settings-console__workspace-header">
          <div>
            <p class="detail-panel__label">{{ sectionEyebrow }}</p>
            <h2>{{ sectionTitle }}</h2>
            <p class="workspace-page__summary">{{ sectionSummary }}</p>
          </div>
          <div class="settings-console__workspace-actions">
            <span class="settings-console__state-pill">{{ runtimeStatusLabel }}</span>
            <span class="settings-console__state-pill">{{ configStatusLabel }}</span>
          </div>
          </header>
        <section class="settings-console__surface" :data-state="sectionState">
          <SettingsSystemFormPanel
            v-if="currentSection === 'system'"
            :current-section="currentSection"
            :disabled="isDisabled"
            :form="form"
            :model-options="defaultProviderModels"
            :provider-options="capabilityStore.providerCatalog"
            @update="handleSystemUpdate"
            @pick-directory="handlePickDirectory"
            @open-log-directory="handleOpenLogDirectory"
          />

          <ProviderCatalogPanel
            v-else-if="currentSection === 'provider'"
            :disabled="isDisabled"
            :health-model="selectedProviderHealthModel"
            :provider-catalog="capabilityStore.providerCatalog"
            :provider-draft="selectedProviderDraft"
            :refresh-result="selectedProviderRefreshResult"
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

          <div v-else class="settings-console__capability-layout">
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
        </section>

        <SettingsSaveBar
          :capability-dirty="capabilityDirty"
          :is-capability-saving="capabilityStore.status === 'saving'"
          :is-system-saving="store.status === 'saving'"
          :system-dirty="systemDirty"
          :visible="systemDirty || capabilityDirty"
          @save-capabilities="handleSaveCapabilities"
          @save-system="handleSave"
        />
      </main>

    </div>
  </section>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, reactive, ref, watch, watchEffect } from "vue";

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
import { type DetailContext, type DetailContextTone, useShellUiStore } from "@/stores/shell-ui";
import type {
  AICapabilityConfig,
  AICapabilitySupportItem,
  AIProviderSecretInput,
  AppSettingsUpdateInput
} from "@/types/runtime";
import {
  applySettingsToForm,
  capabilityLabel,
  capabilityLabels,
  cloneSettingsInput,
  configStatusLabel as getConfigStatusLabel,
  createEmptySettingsInput,
  type DirectoryField,
  formatDateOnly,
  formatErrorSummary,
  openDirectoryPath,
  pickDirectoryPath,
  runtimeStatusLabel as getRuntimeStatusLabel,
  sectionCopy,
  serializeCapabilities,
  serializeSettings,
  settingsToInput,
  type SettingsSectionId
} from "./ai-system-settings-page-helpers";

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
const localBanner = ref<{ message: string; tone: "blocked" | "error" | "ready" } | null>(null);

const isDisabled = computed(() => store.status === "saving" || settings.value === null);
const isCapabilityDisabled = computed(
  () => capabilityStore.status === "loading" || capabilityStore.status === "saving"
);
const isHydrating = computed(
  () =>
    store.status === "loading" ||
    capabilityStore.status === "loading" ||
    licenseStore.status === "loading"
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
const selectedProviderRefreshResult = computed(
  () => capabilityStore.refreshResultByProvider[selectedProviderId.value] ?? null
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
const runtimeStatusLabel = computed(() => getRuntimeStatusLabel(store.runtimeStatus));
const configStatusLabel = computed(() => getConfigStatusLabel(store.status));
const licenseLabel = computed(() => (licenseStore.active ? "授权已激活" : "授权未激活"));
const lastSyncedLabel = computed(() => formatDateOnly(store.lastSyncedAt || store.health?.now || ""));
const diagnosticErrors = computed(() => {
  const errors: string[] = [];
  if (store.error) {
    errors.push(formatErrorSummary(store.error));
  }
  if (capabilityStore.error) {
    errors.push(formatErrorSummary(capabilityStore.error));
  }
  return errors;
});
const currentSectionCopy = computed(() => sectionCopy(currentSection.value));
const sectionEyebrow = computed(() => currentSectionCopy.value.eyebrow);
const sectionTitle = computed(() => currentSectionCopy.value.title);
const sectionSummary = computed(() => currentSectionCopy.value.summary);
const sectionState = computed(() => {
  if (currentSection.value === "provider" && selectedProviderCatalogItem.value?.status === "missing_secret") {
    return "blocked";
  }
  if (currentSection.value === "capability" && !selectedSupportItem.value) {
    return "empty";
  }
  if (isHydrating.value) {
    return "loading";
  }
  if (diagnosticErrors.value.length > 0) {
    return "error";
  }
  return "ready";
});
const pageBanner = computed(() => {
  if (localBanner.value) {
    return localBanner.value.message;
  }
  if (diagnosticErrors.value.length > 0) {
    return diagnosticErrors.value.join("；");
  }
  if (isHydrating.value) {
    return "正在读取 Runtime、Provider 和能力矩阵。";
  }
  if (!licenseStore.active) {
    return "当前授权未激活，部分控制项将保持受限。";
  }
  return "";
});
const pageBannerTone = computed(() => {
  if (localBanner.value) {
    return localBanner.value.tone;
  }
  if (diagnosticErrors.value.length > 0) {
    return "error";
  }
  if (!licenseStore.active) {
    return "blocked";
  }
  if (isHydrating.value) {
    return "loading";
  }
  return "ready";
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

watchEffect(() => {
  shellUiStore.setDetailContext(buildSettingsShellDetailContext());
});

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
  () => [
    selectedProviderId.value,
    selectedProviderModels.value.map((item) => item.modelId).join("|"),
    form.ai.provider,
    form.ai.model
  ],
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

function handleSystemUpdate(patch: Partial<AppSettingsUpdateInput>) {
  localBanner.value = null;
  if (patch.runtime) Object.assign(form.runtime, patch.runtime);
  if (patch.paths) Object.assign(form.paths, patch.paths);
  if (patch.logging) Object.assign(form.logging, patch.logging);
  if (patch.ai) Object.assign(form.ai, patch.ai);
}

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
    selectedProviderHealthModel.value ? { model: selectedProviderHealthModel.value } : undefined
  );
  shellUiStore.openDetailPanel();
}

async function handleRefreshProviderModels(): Promise<void> {
  if (!selectedProviderId.value) {
    return;
  }

  await capabilityStore.refreshProviderModels(selectedProviderId.value);
}

async function handlePickDirectory(field: DirectoryField): Promise<void> {
  localBanner.value = null;
  try {
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
  } catch (error) {
    localBanner.value = {
      message: error instanceof Error ? error.message : "当前环境无法打开系统目录选择器。",
      tone: "error"
    };
  }
}

async function handleOpenLogDirectory(): Promise<void> {
  try {
    await openDirectoryPath(form.paths.logDir);
    localBanner.value = { message: "已请求系统打开日志目录。", tone: "ready" };
  } catch {
    localBanner.value = { message: "无法打开日志目录，请先确认路径已设置且本地目录存在。", tone: "error" };
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

function buildSettingsShellDetailContext(): DetailContext {
  const errors = diagnosticErrors.value;
  const hasErrors = errors.length > 0;
  const providerHealth = selectedProviderHealth.value;
  const sections: DetailContext["sections"] = [
    {
      id: "settings-running",
      title: "运行态",
      description: sectionSummary.value,
      fields: [
        createDetailField("runtime", "Runtime", runtimeStatusLabel.value),
        createDetailField("license", "授权", licenseLabel.value),
        createDetailField("config", "配置", configStatusLabel.value),
        createDetailField("sync", "最近同步", lastSyncedLabel.value || "待同步")
      ]
    },
    {
      id: "settings-boundary",
      title: "系统边界",
      fields: [
        createDetailField("database", "数据库", store.diagnostics?.databasePath ?? "暂无数据库路径", {
          mono: true,
          multiline: true
        }),
        createDetailField("cache", "缓存目录", store.diagnostics?.cacheDir ?? "暂无缓存目录", {
          mono: true,
          multiline: true
        }),
        createDetailField("logs", "日志目录", store.diagnostics?.logDir ?? "暂无日志目录", {
          mono: true,
          multiline: true
        }),
        createDetailField(
          "capability",
          "Provider / 能力",
          `${configuredProviderCount.value}/${capabilityStore.providerCatalog.length} · ${enabledCapabilityCount.value}`
        )
      ]
    },
    {
      id: "settings-focus",
      title: "当前焦点",
      fields: [
        createDetailField("section", "设置分区", sectionTitle.value),
        createDetailField("provider", "选中 Provider", selectedProviderLabel.value),
        createDetailField("health", "连接状态", providerHealth?.status ?? "待检查"),
        createDetailField("message", "检查结果", providerHealth?.message ?? "尚未执行连接检查。", {
          multiline: true
        })
      ]
    }
  ];

  if (errors.length > 0) {
    sections.push({
      id: "settings-errors",
      title: "异常",
      items: errors.map((error, index) => ({
        id: `settings-error-${index}`,
        title: error,
        icon: "error",
        tone: "danger"
      }))
    });
  }

  return {
    key: `settings:${currentSection.value}:${selectedProviderId.value}:${selectedCapabilityId.value}`,
    mode: "settings",
    source: "custom",
    icon: "settings",
    eyebrow: "AI 与系统设置",
    title: `${sectionTitle.value} 上下文`,
    description: "页面主区只保留当前设置工作流，运行态、系统边界和焦点信息统一收拢到右侧抽屉。",
    badge: {
      label: hasErrors ? "需要处理" : runtimeStatusLabel.value,
      tone: hasErrors ? "danger" : mapRuntimeDetailTone()
    },
    metrics: [
      {
        id: "runtime",
        label: "Runtime",
        value: runtimeStatusLabel.value
      },
      {
        id: "providers",
        label: "Provider",
        value: `${configuredProviderCount.value}/${capabilityStore.providerCatalog.length}`
      },
      {
        id: "capabilities",
        label: "能力",
        value: `${enabledCapabilityCount.value}`
      }
    ],
    sections
  };
}

function createDetailField(
  id: string,
  label: string,
  value: string,
  options: { mono?: boolean; multiline?: boolean } = {}
) {
  return {
    id,
    label,
    value,
    mono: options.mono,
    multiline: options.multiline
  };
}

function mapRuntimeDetailTone(): DetailContextTone {
  if (store.runtimeStatus === "online") {
    return "success";
  }
  if (store.runtimeStatus === "offline") {
    return "danger";
  }
  if (store.runtimeStatus === "loading") {
    return "warning";
  }
  return "info";
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
</script>

<style scoped src="./AISystemSettingsPage.css"></style>
