<template>
  <div class="system-status-detail">
    <section class="detail-section detail-section--hero">
      <div>
        <p class="detail-section__eyebrow">设置诊断抽屉</p>
        <h2>系统与 AI 可用性</h2>
        <p>目录边界、配置状态和最近一次模型连通性测试统一收拢在这里。</p>
      </div>
      <span class="live-indicator">
        <span class="live-indicator__dot"></span>
        <span class="live-indicator__text">Live</span>
      </span>
    </section>

    <section class="detail-section">
      <div class="status-stack">
        <div class="status-row">
          <div class="status-row__info">
            <p class="status-row__label">Runtime 引擎</p>
            <p class="status-row__sub">{{ runtimeVersion }}</p>
          </div>
          <p class="status-row__value" :class="runtimeIsActive ? 'status-row__value--active' : 'status-row__value--inactive'">
            {{ runtimeIsActive ? "Active" : "Inactive" }}
          </p>
        </div>

        <div class="status-row">
          <div class="status-row__info">
            <p class="status-row__label">许可证授权</p>
            <p class="status-row__sub">{{ maskedCode }}</p>
          </div>
          <p class="status-row__value" :class="licenseIsActive ? 'status-row__value--active' : 'status-row__value--inactive'">
            {{ licenseIsActive ? "Active" : "Inactive" }}
          </p>
        </div>

        <div class="status-row">
          <div class="status-row__info">
            <p class="status-row__label">配置总线</p>
            <p class="status-row__sub">{{ configStatusLabel }}</p>
          </div>
          <p class="status-row__value" :class="configIsReady ? 'status-row__value--active' : 'status-row__value--inactive'">
            {{ configIsReady ? "Ready" : "Pending" }}
          </p>
        </div>
      </div>
    </section>

    <section class="detail-section">
      <p class="detail-section__title">运行摘要</p>
      <div class="metric-grid">
        <article class="metric-tile">
          <span>已配置 Provider</span>
          <strong>{{ configuredProviderCount }}/{{ providerCount }}</strong>
        </article>
        <article class="metric-tile">
          <span>已启用能力</span>
          <strong>{{ enabledCapabilityCount }}</strong>
        </article>
        <article class="metric-tile">
          <span>配置修订</span>
          <strong>{{ configRevision }}</strong>
        </article>
      </div>
    </section>

    <section class="detail-section">
      <div class="detail-section__header">
        <p class="detail-section__title">最近一次模型测试</p>
        <span class="detail-section__hint">右侧抽屉同步更新</span>
      </div>

      <template v-if="lastCheckedHealth">
        <article class="health-card" :class="healthCardTone">
          <div class="health-card__header">
            <div>
              <strong>{{ lastCheckedProviderLabel }}</strong>
              <p>{{ lastCheckedHealth.message }}</p>
            </div>
            <span class="health-card__badge">{{ healthLabel(lastCheckedHealth.status) }}</span>
          </div>
          <div class="health-card__meta">
            <span>{{ lastCheckedHealth.model || "未指定模型" }}</span>
            <span>{{ latencyLabel }}</span>
            <span>{{ checkedAtLabel }}</span>
          </div>
        </article>
      </template>
      <p v-else class="detail-section__empty">
        在 Provider 配置区选择模型并执行“测试连接”后，这里会显示最近一次真实连通性结果。
      </p>
    </section>

    <section class="detail-section">
      <p class="detail-section__title">目录与边界</p>
      <div class="path-list">
        <div v-for="item in pathItems" :key="item.label" class="path-item">
          <span>{{ item.label }}</span>
          <code :title="item.value">{{ item.value }}</code>
        </div>
      </div>
    </section>

    <section class="detail-section">
      <p class="detail-section__title">项目上下文</p>
      <template v-if="projectName">
        <div class="project-context">
          <strong>{{ projectName }}</strong>
          <p>状态：{{ projectStatus }}</p>
        </div>
      </template>
      <p v-else class="detail-section__empty">尚未选择项目。需要项目上下文的页面会先回到创作总览。</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import { useAICapabilityStore } from "@/stores/ai-capability";
import { useConfigBusStore } from "@/stores/config-bus";

const props = defineProps<{
  configStatusLabel: string;
  licenseLabel: string;
  maskedCode: string;
  projectName: string;
  projectStatus: string;
  runtimeLabel: string;
  runtimeVersion: string;
}>();

const configBusStore = useConfigBusStore();
const capabilityStore = useAICapabilityStore();

const runtimeIsActive = computed(() => props.runtimeLabel.includes("在线"));
const licenseIsActive = computed(() => props.licenseLabel.includes("激活") || props.licenseLabel.includes("授权"));
const configIsReady = computed(() => props.configStatusLabel.includes("就绪"));
const providerCount = computed(() => capabilityStore.providerCatalog.length);
const configuredProviderCount = computed(
  () => capabilityStore.providerCatalog.filter((item) => item.configured).length
);
const enabledCapabilityCount = computed(
  () => capabilityStore.settings?.capabilities.filter((item) => item.enabled).length ?? 0
);
const configRevision = computed(() => configBusStore.settings?.revision ?? "-");
const lastCheckedHealth = computed(() => {
  const providerId = capabilityStore.lastCheckedProviderId;
  return providerId ? capabilityStore.providerHealth[providerId] ?? null : null;
});
const lastCheckedProviderLabel = computed(() => {
  const providerId = capabilityStore.lastCheckedProviderId;
  const provider = capabilityStore.providerCatalog.find((item) => item.provider === providerId);
  return provider?.label ?? "最近测试";
});
const latencyLabel = computed(() =>
  lastCheckedHealth.value?.latencyMs ? `${lastCheckedHealth.value.latencyMs} ms` : "延迟待返回"
);
const checkedAtLabel = computed(() => formatCheckedAt(lastCheckedHealth.value?.checkedAt ?? ""));
const pathItems = computed(() => [
  {
    label: "工作区",
    value: configBusStore.settings?.runtime.workspaceRoot || "-"
  },
  {
    label: "缓存目录",
    value: configBusStore.settings?.paths.cacheDir || "-"
  },
  {
    label: "导出目录",
    value: configBusStore.settings?.paths.exportDir || "-"
  },
  {
    label: "日志目录",
    value: configBusStore.settings?.paths.logDir || configBusStore.diagnostics?.logDir || "-"
  }
]);
const healthCardTone = computed(() => {
  switch (lastCheckedHealth.value?.status) {
    case "ready":
      return "health-card--ready";
    case "offline":
    case "misconfigured":
    case "missing_secret":
      return "health-card--alert";
    default:
      return "";
  }
});

function healthLabel(status: string): string {
  return (
    {
      ready: "正常",
      missing_secret: "缺少密钥",
      misconfigured: "配置异常",
      offline: "不可达",
      unsupported: "未接入"
    }[status] ?? status
  );
}

function formatCheckedAt(value: string): string {
  if (!value) {
    return "刚刚更新";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  const hour = `${date.getHours()}`.padStart(2, "0");
  const minute = `${date.getMinutes()}`.padStart(2, "0");
  return `${year}-${month}-${day} ${hour}:${minute}`;
}
</script>

<style scoped>
.system-status-detail {
  display: grid;
  gap: 18px;
}

.detail-section {
  display: grid;
  gap: 14px;
  border-bottom: 1px solid var(--border-default);
  padding-bottom: 18px;
}

.detail-section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.detail-section--hero {
  align-items: start;
  grid-template-columns: minmax(0, 1fr) auto;
}

.detail-section--hero h2 {
  margin: 6px 0 8px;
}

.detail-section--hero p:last-child {
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
}

.detail-section__eyebrow,
.detail-section__title {
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.05em;
  margin: 0;
  text-transform: uppercase;
}

.detail-section__header {
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.detail-section__hint {
  color: var(--text-tertiary);
  font-size: 12px;
}

.live-indicator {
  align-items: center;
  display: flex;
  gap: 6px;
}

.live-indicator__dot {
  animation: pulse-dot 2s ease-in-out infinite;
  background: var(--brand-primary);
  border-radius: 50%;
  box-shadow: 0 0 6px var(--brand-primary);
  height: 6px;
  width: 6px;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.live-indicator__text {
  color: var(--brand-primary);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.status-stack,
.metric-grid,
.path-list {
  display: grid;
  gap: 10px;
}

.metric-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.status-row,
.metric-tile,
.health-card,
.path-item {
  border: 1px solid var(--border-default);
  border-radius: 12px;
  background: var(--surface-tertiary);
}

.status-row {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
}

.status-row__info {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.status-row__label {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
}

.status-row__sub {
  margin: 0;
  color: var(--text-secondary);
  font-size: 11px;
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-row__value {
  margin: 0;
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--surface-secondary);
  font-size: 12px;
  font-weight: 800;
}

.status-row__value--active {
  color: var(--status-success);
}

.status-row__value--inactive {
  color: var(--status-error);
}

.metric-tile {
  display: grid;
  gap: 6px;
  padding: 14px;
}

.metric-tile span {
  color: var(--text-tertiary);
  font-size: 12px;
}

.metric-tile strong {
  font-size: 22px;
}

.health-card {
  display: grid;
  gap: 12px;
  padding: 14px;
}

.health-card--ready {
  border-color: color-mix(in srgb, var(--status-success) 28%, var(--border-default));
  background: color-mix(in srgb, var(--status-success) 10%, var(--surface-tertiary));
}

.health-card--alert {
  border-color: color-mix(in srgb, var(--status-warning) 28%, var(--border-default));
  background: color-mix(in srgb, var(--status-warning) 12%, var(--surface-tertiary));
}

.health-card__header {
  align-items: start;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.health-card__header strong,
.project-context strong {
  display: block;
  margin-bottom: 6px;
  font-size: 15px;
}

.health-card__header p,
.project-context p {
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
}

.health-card__badge {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--surface-secondary);
  font-size: 12px;
  font-weight: 700;
}

.health-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 12px;
}

.path-item {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
}

.path-item span {
  color: var(--text-tertiary);
  font-size: 12px;
}

.path-item code {
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-section__empty {
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
  padding: 12px 14px;
  border: 1px solid var(--border-default);
  border-radius: 12px;
  background: var(--surface-tertiary);
}

@media (max-width: 1100px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
