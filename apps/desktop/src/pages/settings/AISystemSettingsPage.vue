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
            <button class="settings-page__button settings-page__button--ghost" type="button" title="切换属性面板" @click="shellUiStore.openDetailPanel()">
              打开右侧抽屉
            </button>
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

          <section v-else class="settings-console__diagnostic-stage">
            <div class="settings-console__diagnostic-hero">
              <div>
                <p class="detail-panel__label">当前运行视图</p>
                <h3>诊断工作台</h3>
                <p class="workspace-page__summary">
                  主区保留运行状态、Provider 连通性和能力矩阵的总览，右侧抽屉继续承载更细的 Runtime / 诊断信息。
                </p>
              </div>

              <div class="settings-console__diagnostic-actions">
                <button class="settings-page__button" type="button" @click="shellUiStore.openDetailPanel()">
                  打开诊断抽屉
                </button>
              </div>
            </div>

            <div class="settings-console__diagnostic-grid">
              <article class="settings-console__diagnostic-tile">
                <span>Runtime</span>
                <strong>{{ runtimeStatusLabel }}</strong>
                <p>{{ store.health?.service || "未读取" }} / {{ store.health?.version || "-" }}</p>
              </article>
              <article class="settings-console__diagnostic-tile">
                <span>配置同步</span>
                <strong>{{ configStatusLabel }}</strong>
                <p>修订号 {{ settings?.revision ?? "-" }}</p>
              </article>
              <article class="settings-console__diagnostic-tile">
                <span>Provider</span>
                <strong>{{ configuredProviderCount }}/{{ capabilityStore.providerCatalog.length }}</strong>
                <p>已保存连接凭据</p>
              </article>
              <article class="settings-console__diagnostic-tile">
                <span>能力</span>
                <strong>{{ enabledCapabilityCount }}</strong>
                <p>已启用的能力配置</p>
              </article>
            </div>
          </section>
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

      <section class="settings-console__inspector" data-testid="settings-inline-diagnostics">
        <SettingsDiagnosticPanel
          :config-status-label="configStatusLabel"
          :configured-provider-count="configuredProviderCount"
          :diagnostics="store.diagnostics"
          :enabled-capability-count="enabledCapabilityCount"
          :errors="diagnosticErrors"
          :last-synced-label="lastSyncedLabel"
          :license-label="licenseLabel"
          :provider-count="capabilityStore.providerCatalog.length"
          :runtime-status-label="runtimeStatusLabel"
          :section="currentSection"
          :selected-provider-health="selectedProviderHealth"
          :selected-provider-label="selectedProviderLabel"
        />
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, reactive, ref, watch } from "vue";

import AICapabilityInspector from "@/modules/settings/components/AICapabilityInspector.vue";
import AICapabilityMatrix from "@/modules/settings/components/AICapabilityMatrix.vue";
import ProviderCatalogPanel from "@/modules/settings/components/ProviderCatalogPanel.vue";
import SettingsDiagnosticPanel from "@/modules/settings/components/SettingsDiagnosticPanel.vue";
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

  await capabilityStore.loadProviderModels(selectedProviderId.value);
}

async function handlePickDirectory(field: DirectoryField): Promise<void> {
  localBanner.value = null;
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
