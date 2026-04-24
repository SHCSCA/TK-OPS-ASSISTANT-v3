<template>
  <section class="provider-hub-panel" data-testid="provider-catalog-panel">
    <div class="settings-workspace-panel__header">
      <div>
        <p class="detail-panel__label">Provider Hub</p>
        <h2>供应商、模型目录与连接凭据</h2>
        <p class="workspace-page__summary">
          已接入 Provider 保持在左侧，模板库用于新增接入，模型目录只展示当前 Provider 的真实能力。
        </p>
      </div>
      <div class="settings-workspace-panel__meta">
        <span class="settings-workspace-panel__pill">Provider {{ providerCatalog.length }}</span>
        <span class="settings-workspace-panel__pill settings-workspace-panel__pill--muted">已配置 {{ configuredProviderCount }}</span>
        <span class="settings-workspace-panel__pill settings-workspace-panel__pill--muted">可同步 {{ remoteSyncProviderCount }}</span>
      </div>
    </div>

    <div v-if="providerCatalog.length === 0" class="settings-workspace-panel__empty" data-testid="provider-empty-state">
      Provider 注册表尚未加载。
    </div>

    <div v-else class="provider-hub-layout">
      <aside class="provider-connected-list">
        <label class="settings-field provider-connected-list__select">
          <span>当前 Provider</span>
          <select
            :value="selectedProviderId"
            data-testid="provider-picker"
            data-field="provider.selected"
            :disabled="disabled"
            @change="$emit('select-provider', String(($event.target as HTMLSelectElement).value))"
          >
            <option v-for="provider in providerCatalog" :key="provider.provider" :value="provider.provider">
              {{ provider.label }}
            </option>
          </select>
        </label>

        <div class="provider-connected-list__header">
          <span>已接入</span>
          <strong>{{ connectedProviders.length }}</strong>
        </div>

        <button
          v-for="provider in connectedProviders"
          :key="provider.provider"
          class="provider-connected-list__item"
          :class="{ 'provider-connected-list__item--active': provider.provider === selectedProviderId }"
          type="button"
          :disabled="disabled"
          @click="$emit('select-provider', provider.provider)"
        >
          <span>
            <strong>{{ provider.label }}</strong>
            <small>{{ provider.provider }} · {{ providerCategoryLabel(provider) }}</small>
          </span>
          <em>{{ providerStatusLabel(provider.status) }}</em>
        </button>

        <div v-if="connectedProviders.length <= 1" class="provider-connected-list__hint">
          保存密钥和 Base URL 后，Provider 会进入已接入列表。
        </div>
      </aside>

      <section class="provider-hub-main">
        <section class="provider-template-library">
          <div class="settings-card__header">
            <div>
              <p class="detail-panel__label">模板库</p>
              <h3>厂商模板库</h3>
            </div>
            <button
              class="settings-workspace-panel__button"
              type="button"
              :disabled="disabled || !customOpenAIProvider"
              @click="selectCustomProvider"
            >
              新增自定义
            </button>
          </div>

          <div class="provider-template-library__tabs" role="tablist" aria-label="Provider 模板分组">
            <button
              v-for="region in templateRegions"
              :key="region"
              class="provider-template-library__tab"
              :class="{ 'provider-template-library__tab--active': region === activeTemplateRegion }"
              type="button"
              :disabled="disabled"
              @click="activeTemplateRegion = region"
            >
              {{ regionLabel(region) }}
            </button>
          </div>

          <div class="provider-template-library__grid">
            <button
              v-for="provider in visibleTemplateProviders"
              :key="provider.provider"
              class="provider-template-card"
              :class="{ 'provider-template-card--active': provider.provider === selectedProviderId }"
              type="button"
              :disabled="disabled"
              @click="$emit('select-provider', provider.provider)"
            >
              <span class="provider-template-card__copy">
                <strong>{{ provider.label }}</strong>
                <small>{{ provider.provider }} · {{ syncModeLabel(provider.modelSyncMode) }}</small>
              </span>
              <span class="provider-template-card__chips">
                <span
                  v-for="capability in provider.capabilities.slice(0, 4)"
                  :key="`${provider.provider}:${capability}`"
                  class="provider-capability-chip"
                >
                  {{ capabilityLabel(capability) }}
                </span>
              </span>
            </button>
          </div>
        </section>

        <section class="provider-model-directory">
          <div class="settings-card__header">
            <div>
              <p class="detail-panel__label">模型目录</p>
              <h3>{{ selectedProviderLabel }}</h3>
            </div>
            <button
              class="settings-workspace-panel__button"
              type="button"
              :disabled="disabled || !selectedProvider"
              @click="$emit('refresh-models')"
            >
              {{ selectedProvider?.supportsModelDiscovery ? "同步模型" : "刷新目录" }}
            </button>
          </div>

          <article class="provider-summary" :class="providerSummaryTone">
            <div class="provider-summary__header">
              <div>
                <h4>{{ selectedProvider?.label ?? "未选择 Provider" }}</h4>
                <p>{{ selectedProvider?.provider ?? "请选择 Provider" }} · {{ selectedProviderProtocol }}</p>
              </div>
              <span class="provider-summary__status">{{ providerStatusText }}</span>
            </div>

            <div class="provider-summary__chips">
              <span
                v-for="capability in selectedProvider?.capabilities ?? []"
                :key="capability"
                class="provider-capability-chip"
              >
                {{ capabilityLabel(capability) }}
              </span>
            </div>

            <p class="provider-summary__endpoint" :title="selectedProviderBaseUrl">
              {{ selectedProviderBaseUrl || "等待配置 Base URL" }}
            </p>
            <p v-if="refreshResult" class="provider-summary__refresh">
              {{ refreshResult.message }}
            </p>
          </article>

          <label class="settings-field">
            <span>健康检查模型</span>
            <select
              :value="healthModel"
              data-field="provider.health.model"
              :disabled="disabled || selectedProviderModels.length === 0"
              @change="$emit('update:health-model', String(($event.target as HTMLSelectElement).value))"
            >
              <option value="">
                {{ selectedProviderModels.length === 0 ? "当前 Provider 暂无模型目录" : "请选择健康检查模型" }}
              </option>
              <option v-for="model in selectedProviderModels" :key="`${model.provider}:${model.modelId}`" :value="model.modelId">
                {{ model.displayName }}
              </option>
            </select>
          </label>

          <div v-if="selectedProviderModels.length > 0" class="provider-model-directory__tools">
            <label class="settings-field provider-model-directory__search">
              <span>筛选模型</span>
              <input
                v-model="modelSearchQuery"
                data-field="provider.model.search"
                placeholder="输入模型名称或 ID"
                type="search"
              />
            </label>
            <label class="settings-field provider-model-directory__capability">
              <span>能力</span>
              <select v-model="modelCapabilityFilter" data-field="provider.model.capability">
                <option value="">全部能力</option>
                <option v-for="capability in modelCapabilityOptions" :key="capability" :value="capability">
                  {{ capabilityLabel(capability) }}
                </option>
              </select>
            </label>
          </div>

          <div v-if="selectedProviderModels.length > 0" class="provider-model-directory__pager">
            <span>{{ modelRangeLabel }}</span>
            <div class="provider-model-directory__pager-actions">
              <button
                class="settings-workspace-panel__button"
                type="button"
                data-action="provider.model.prev-page"
                :disabled="modelPage <= 1"
                @click="changeModelPage(-1)"
              >
                上一页
              </button>
              <button
                class="settings-workspace-panel__button"
                type="button"
                data-action="provider.model.next-page"
                :disabled="modelPage >= modelTotalPages"
                @click="changeModelPage(1)"
              >
                下一页
              </button>
            </div>
          </div>

          <div v-if="selectedProviderModels.length === 0" class="settings-workspace-panel__empty">
            保存当前 Provider 的连接信息后，可从 Runtime 同步或手动维护模型目录。
          </div>
          <div v-else-if="filteredProviderModels.length === 0" class="settings-workspace-panel__empty">
            当前筛选条件下没有可显示的模型。
          </div>
          <div v-else class="provider-model-list">
            <article
              v-for="model in visibleProviderModels"
              :key="`${model.provider}:${model.modelId}`"
              class="provider-model-list__item"
            >
              <div class="provider-model-list__copy">
                <h4>{{ model.displayName }}</h4>
                <p :title="model.modelId">{{ model.modelId }}</p>
              </div>
              <div class="provider-model-list__capabilities">
                <span
                  v-for="capability in model.capabilityTypes"
                  :key="`${model.modelId}:${capability}`"
                  class="provider-capability-chip"
                >
                  {{ capabilityLabel(capability) }}
                </span>
              </div>
              <div class="provider-model-list__meta">
                <span>输入 {{ model.inputModalities.map(modalityLabel).join(" / ") || "未声明" }}</span>
                <span>输出 {{ model.outputModalities.map(modalityLabel).join(" / ") || "未声明" }}</span>
                <span>默认 {{ model.defaultFor.map(capabilityLabel).join("、") || "手动选择" }}</span>
              </div>
            </article>
          </div>
        </section>
      </section>

      <aside class="provider-credential-inspector">
        <div class="settings-card__header">
          <div>
            <p class="detail-panel__label">Inspector</p>
            <h3>{{ selectedProviderTitle }}</h3>
          </div>
        </div>

        <div class="provider-secret__status" :class="providerHealthTone">
          <strong>{{ selectedProviderHealthLabel }}</strong>
          <p>{{ selectedProviderHealth?.message ?? secretStatusSummary }}</p>
        </div>

        <label class="settings-field">
          <span>API Key</span>
          <input
            v-model="providerDraft.apiKey"
            data-field="provider.secret.apiKey"
            :placeholder="secretPlaceholder"
            :disabled="disabled"
            type="password"
          />
        </label>
        <label class="settings-field">
          <span>Base URL</span>
          <input
            v-model="providerDraft.baseUrl"
            data-field="provider.secret.baseUrl"
            :placeholder="selectedProviderBaseUrl || '请输入 Provider Base URL'"
            :title="providerDraft.baseUrl || selectedProviderBaseUrl"
            :disabled="disabled"
          />
        </label>

        <div class="provider-credential-inspector__facts">
          <span>区域 {{ selectedProvider ? regionLabel(selectedProvider.region) : "-" }}</span>
          <span>同步 {{ selectedProvider ? syncModeLabel(selectedProvider.modelSyncMode) : "-" }}</span>
          <span>密钥 {{ selectedProvider?.secretSource ?? "none" }}</span>
        </div>

        <div class="provider-credential-inspector__actions">
          <button class="settings-workspace-panel__button" type="button" :disabled="disabled" @click="$emit('save-provider-secret')">
            保存凭据
          </button>
          <button
            class="settings-workspace-panel__button"
            type="button"
            :disabled="disabled || !selectedProvider"
            @click="$emit('refresh-models')"
          >
            同步模型
          </button>
          <button
            class="settings-workspace-panel__button settings-workspace-panel__button--primary"
            type="button"
            data-action="check-provider"
            :disabled="disabled || selectedProviderModels.length === 0"
            @click="$emit('check-provider')"
          >
            连接检查
          </button>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type {
  AIModelCatalogItem,
  AIModelCatalogRefreshResult,
  AIProviderCatalogItem,
  AIProviderHealth,
  AIProviderSecretStatus
} from "@/types/runtime";

const props = defineProps<{
  disabled: boolean;
  healthModel: string;
  providerCatalog: AIProviderCatalogItem[];
  providerDraft: { apiKey: string; baseUrl: string };
  refreshResult: AIModelCatalogRefreshResult | null;
  selectedProviderHealth: AIProviderHealth | null;
  selectedProviderId: string;
  selectedProviderModels: AIModelCatalogItem[];
  secretStatus: AIProviderSecretStatus | null;
}>();

const emit = defineEmits<{
  (e: "check-provider"): void;
  (e: "refresh-models"): void;
  (e: "save-provider-secret"): void;
  (e: "select-provider", providerId: string): void;
  (e: "update:health-model", modelId: string): void;
}>();

const activeTemplateRegion = ref("domestic");
const MODEL_PAGE_SIZE = 10;
const modelCapabilityFilter = ref("");
const modelPage = ref(1);
const modelSearchQuery = ref("");

const configuredProviderCount = computed(
  () => props.providerCatalog.filter((provider) => provider.configured).length
);
const remoteSyncProviderCount = computed(
  () => props.providerCatalog.filter((provider) => provider.supportsModelDiscovery).length
);
const selectedProvider = computed(
  () => props.providerCatalog.find((item) => item.provider === props.selectedProviderId) ?? null
);
const selectedProviderLabel = computed(() =>
  selectedProvider.value ? `${selectedProvider.value.label} 模型目录` : "模型目录"
);
const selectedProviderTitle = computed(() =>
  selectedProvider.value ? `${selectedProvider.value.label} 凭据` : "连接凭据"
);
const selectedProviderBaseUrl = computed(() => selectedProvider.value?.baseUrl ?? "");
const selectedProviderProtocol = computed(() => selectedProvider.value?.protocol ?? "manual_catalog");
const connectedProviders = computed(() => {
  const connected = props.providerCatalog.filter((provider) => provider.configured);
  const current = selectedProvider.value;
  if (current && !connected.some((provider) => provider.provider === current.provider)) {
    return [current, ...connected];
  }
  return connected;
});
const customOpenAIProvider = computed(
  () => props.providerCatalog.find((provider) => provider.provider === "custom_openai_compatible") ?? null
);
const templateRegions = computed(() => {
  const available = new Set(props.providerCatalog.map((provider) => provider.region));
  return ["domestic", "custom", "local", "global"].filter((region) => available.has(region));
});
const visibleTemplateProviders = computed(() =>
  props.providerCatalog.filter((provider) => provider.region === activeTemplateRegion.value)
);
const modelCapabilityOptions = computed(() =>
  Array.from(new Set(props.selectedProviderModels.flatMap((model) => model.capabilityTypes))).sort((a, b) =>
    capabilityLabel(a).localeCompare(capabilityLabel(b), "zh-Hans-CN")
  )
);
const filteredProviderModels = computed(() => {
  const query = modelSearchQuery.value.trim().toLowerCase();
  return props.selectedProviderModels.filter((model) => {
    const matchesQuery =
      query === "" ||
      model.displayName.toLowerCase().includes(query) ||
      model.modelId.toLowerCase().includes(query);
    const matchesCapability =
      modelCapabilityFilter.value === "" ||
      model.capabilityTypes.includes(modelCapabilityFilter.value);
    return matchesQuery && matchesCapability;
  });
});
const modelTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredProviderModels.value.length / MODEL_PAGE_SIZE))
);
const visibleProviderModels = computed(() => {
  const start = (modelPage.value - 1) * MODEL_PAGE_SIZE;
  return filteredProviderModels.value.slice(start, start + MODEL_PAGE_SIZE);
});
const modelRangeLabel = computed(() => {
  const total = filteredProviderModels.value.length;
  if (total === 0) {
    return "0 / 0";
  }
  const start = (modelPage.value - 1) * MODEL_PAGE_SIZE + 1;
  const end = Math.min(total, start + MODEL_PAGE_SIZE - 1);
  return `${start}-${end} / ${total}`;
});
const selectedProviderHealthLabel = computed(() => {
  switch (props.selectedProviderHealth?.status) {
    case "ready":
      return "连接正常";
    case "missing_secret":
      return "缺少密钥";
    case "misconfigured":
      return "配置不完整";
    case "offline":
      return "连接离线";
    default:
      return "等待检查";
  }
});
const secretStatusSummary = computed(() => {
  if (props.secretStatus?.configured) {
    return `已保存 ${props.secretStatus.maskedSecret}，来源 ${props.secretStatus.secretSource}。`;
  }
  return "当前 Provider 还没有可用凭据。";
});
const secretPlaceholder = computed(() =>
  props.secretStatus?.configured ? "已保存密钥，输入后会覆盖" : "请输入 Provider API Key"
);
const providerStatusText = computed(() =>
  selectedProvider.value ? providerStatusLabel(selectedProvider.value.status) : "待选择"
);
const providerSummaryTone = computed(() => {
  switch (selectedProvider.value?.status) {
    case "ready":
      return "provider-summary--ready";
    case "missing_secret":
    case "misconfigured":
    case "offline":
      return "provider-summary--blocked";
    default:
      return "";
  }
});
const providerHealthTone = computed(() => {
  switch (props.selectedProviderHealth?.status) {
    case "ready":
      return "provider-secret__status--ready";
    case "missing_secret":
    case "misconfigured":
    case "offline":
      return "provider-secret__status--blocked";
    default:
      return "";
  }
});

watch(
  templateRegions,
  (regions) => {
    if (regions.length > 0 && !regions.includes(activeTemplateRegion.value)) {
      activeTemplateRegion.value = regions[0];
    }
  },
  { immediate: true }
);

watch(
  () => [
    props.selectedProviderId,
    props.selectedProviderModels.length,
    modelCapabilityFilter.value,
    modelSearchQuery.value
  ],
  () => {
    modelPage.value = 1;
  }
);

watch(modelTotalPages, (totalPages) => {
  if (modelPage.value > totalPages) {
    modelPage.value = totalPages;
  }
});

function changeModelPage(offset: number): void {
  modelPage.value = Math.min(modelTotalPages.value, Math.max(1, modelPage.value + offset));
}

function selectCustomProvider(): void {
  if (customOpenAIProvider.value) {
    emit("select-provider", customOpenAIProvider.value.provider);
    activeTemplateRegion.value = "custom";
  }
}

function providerStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    ready: "已就绪",
    missing_secret: "缺少密钥",
    misconfigured: "需配置",
    offline: "离线",
    unsupported: "未接入"
  };
  return labels[status] ?? "待检查";
}

function providerCategoryLabel(provider: AIProviderCatalogItem): string {
  const labels: Record<string, string> = {
    aggregator: "聚合",
    asset_analysis: "素材",
    custom: "自定义",
    local: "本地",
    media: "媒体",
    model_hub: "模型平台",
    text: "文本",
    tts: "语音",
    video: "视频"
  };
  return labels[provider.category] ?? provider.kind;
}

function regionLabel(region: string): string {
  const labels: Record<string, string> = {
    domestic: "国内",
    global: "国际",
    local: "本地",
    custom: "自定义"
  };
  return labels[region] ?? region;
}

function syncModeLabel(mode: string): string {
  const labels: Record<string, string> = {
    remote: "远端同步",
    static: "内置目录",
    manual: "手动维护"
  };
  return labels[mode] ?? mode;
}

function capabilityLabel(capability: string): string {
  const labels: Record<string, string> = {
    asset_analysis: "资产",
    asr: "ASR",
    script_generation: "脚本",
    script_rewrite: "改写",
    storyboard_generation: "分镜",
    subtitle_alignment: "字幕",
    text_generation: "文本",
    tts: "TTS",
    tts_generation: "TTS",
    video_generation: "视频",
    vision: "视觉"
  };
  return labels[capability] ?? capability;
}

function modalityLabel(modality: string): string {
  const labels: Record<string, string> = {
    audio: "音频",
    image: "图像",
    text: "文本",
    video: "视频"
  };
  return labels[modality] ?? modality;
}
</script>

<style scoped>
.provider-hub-panel {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
  container-type: inline-size;
}

.settings-workspace-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.settings-workspace-panel__header h2,
.settings-workspace-panel__header p,
.provider-summary h4,
.settings-card__header h3,
.provider-model-list__copy h4 {
  margin: 0;
}

.settings-workspace-panel__header h2,
.settings-card__header h3 {
  font: var(--font-title-md);
  letter-spacing: 0;
}

.settings-workspace-panel__meta,
.provider-summary__chips,
.provider-credential-inspector__actions,
.provider-template-card__chips,
.provider-model-list__capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.settings-workspace-panel__pill,
.provider-capability-chip {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
  color: var(--text-primary);
  font: var(--font-caption);
}

.settings-workspace-panel__pill--muted,
.provider-capability-chip {
  color: var(--text-secondary);
}

.settings-workspace-panel__empty {
  padding: var(--space-4);
  border: 1px dashed var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  color: var(--text-secondary);
  font: var(--font-body-sm);
}

.provider-hub-layout {
  display: grid;
  grid-template-columns: minmax(190px, 0.28fr) minmax(420px, 1fr) minmax(280px, 0.42fr);
  gap: var(--density-panel-gap);
  align-items: start;
  min-width: 0;
}

.provider-connected-list,
.provider-template-library,
.provider-model-directory,
.provider-credential-inspector {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.provider-hub-main {
  display: grid;
  gap: var(--density-panel-gap);
  min-width: 0;
}

.provider-connected-list__select {
  display: grid;
  gap: var(--space-2);
}

.provider-connected-list__header,
.settings-card__header,
.provider-summary__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.provider-connected-list__header {
  align-items: center;
  color: var(--text-secondary);
  font: var(--font-caption);
}

.provider-connected-list__header strong {
  color: var(--text-primary);
  font: var(--font-title-sm);
}

.provider-connected-list__item,
.provider-template-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  min-width: 0;
  min-height: 48px;
  padding: var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
}

.provider-connected-list__item--active,
.provider-connected-list__item:hover,
.provider-template-card--active,
.provider-template-card:hover {
  border-color: color-mix(in srgb, var(--brand-primary) 34%, var(--border-default));
  background: color-mix(in srgb, var(--brand-primary) 10%, var(--surface-tertiary));
  transform: translateY(-1px);
}

.provider-connected-list__item span,
.provider-template-card__copy,
.provider-model-list__copy,
.provider-model-list__meta,
.provider-summary__header > div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.provider-connected-list__item strong,
.provider-connected-list__item small,
.provider-connected-list__item em,
.provider-template-card strong,
.provider-template-card small {
  min-width: 0;
  overflow-wrap: anywhere;
}

.provider-connected-list__item small,
.provider-connected-list__item em,
.provider-connected-list__hint,
.provider-summary p,
.provider-model-list__copy p,
.provider-model-list__meta span,
.provider-secret__status p,
.provider-credential-inspector__facts,
.settings-field span {
  color: var(--text-secondary);
  font: var(--font-caption);
  letter-spacing: 0;
}

.provider-connected-list__item em {
  flex: 0 0 auto;
  font-style: normal;
}

.provider-template-library__tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.provider-template-library__tab {
  min-height: 30px;
  padding: 0 var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: 999px;
  background: color-mix(in srgb, var(--surface-primary) 94%, transparent);
  color: var(--text-secondary);
  cursor: pointer;
  font: var(--font-caption);
}

.provider-template-library__tab--active {
  border-color: var(--brand-primary);
  color: var(--text-primary);
}

.provider-template-library__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
  max-height: 250px;
  min-width: 0;
  overflow: auto;
  padding-right: 2px;
}

.provider-template-card {
  align-items: flex-start;
  flex-direction: column;
  min-height: 86px;
}

.provider-summary,
.provider-secret__status,
.provider-model-list__item {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
  padding: var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
}

.provider-summary--ready,
.provider-secret__status--ready {
  border-color: color-mix(in srgb, var(--status-success) 34%, var(--border-default));
}

.provider-summary--blocked,
.provider-secret__status--blocked {
  border-color: color-mix(in srgb, var(--status-warning) 42%, var(--border-default));
}

.provider-summary__status {
  flex: 0 0 auto;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: var(--surface-secondary);
  color: var(--text-secondary);
  font: var(--font-caption);
}

.provider-summary__endpoint {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.provider-summary__refresh {
  padding-top: var(--space-2);
  border-top: 1px solid var(--border-subtle);
}

.provider-model-directory__tools {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(160px, 0.34fr);
  gap: var(--space-3);
  min-width: 0;
}

.provider-model-directory__pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  min-width: 0;
  color: var(--text-secondary);
  font: var(--font-caption);
}

.provider-model-directory__pager-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.settings-field {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.settings-field input,
.settings-field select {
  width: 100%;
  min-height: 38px;
  padding: 0 var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 96%, transparent);
  color: var(--text-primary);
  font: var(--font-body-md);
}

.provider-model-list {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
  max-height: min(780px, calc(100vh - 320px));
  overflow: auto;
  padding-right: 2px;
}

.provider-model-list__item {
  grid-template-columns: minmax(0, 0.9fr) minmax(160px, 0.8fr) minmax(190px, 1fr);
  align-items: start;
}

.provider-model-list__copy h4 {
  font: var(--font-title-sm);
  letter-spacing: 0;
}

.provider-credential-inspector__facts {
  display: grid;
  gap: var(--space-1);
}

.settings-workspace-panel__button {
  min-height: 34px;
  padding: 0 var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 96%, transparent);
  color: var(--text-primary);
  cursor: pointer;
  font: var(--font-title-sm);
}

.settings-workspace-panel__button--primary {
  border-color: var(--brand-primary);
  background: var(--brand-primary);
  color: var(--color-white);
}

.settings-workspace-panel__button:disabled,
.provider-connected-list__item:disabled,
.provider-template-card:disabled,
.provider-template-library__tab:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

@container (max-width: 1120px) {
  .provider-hub-layout {
    grid-template-columns: minmax(190px, 0.34fr) minmax(0, 1fr);
  }

  .provider-credential-inspector {
    grid-column: 1 / -1;
  }
}

@container (max-width: 760px) {
  .settings-workspace-panel__header,
  .settings-card__header,
  .provider-summary__header {
    flex-direction: column;
  }

  .provider-hub-layout,
  .provider-model-directory__tools,
  .provider-template-library__grid,
  .provider-model-list__item {
    grid-template-columns: 1fr;
  }

  .provider-model-directory__pager {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
