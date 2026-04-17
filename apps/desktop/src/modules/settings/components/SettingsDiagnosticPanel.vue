<template>
  <aside class="settings-diagnostic-panel" data-testid="settings-diagnostic-panel">
    <div class="settings-diagnostic-panel__hero">
      <p class="detail-panel__label">诊断视图</p>
      <h2>当前运行态</h2>
      <p>{{ sectionSummary }}</p>
    </div>

    <section class="settings-diagnostic-panel__grid">
      <article class="settings-diagnostic-panel__metric">
        <span>Runtime 状态</span>
        <strong>{{ runtimeStatusLabel }}</strong>
      </article>
      <article class="settings-diagnostic-panel__metric">
        <span>授权状态</span>
        <strong>{{ licenseLabel }}</strong>
      </article>
      <article class="settings-diagnostic-panel__metric">
        <span>配置状态</span>
        <strong>{{ configStatusLabel }}</strong>
      </article>
      <article class="settings-diagnostic-panel__metric">
        <span>最近同步</span>
        <strong>{{ lastSyncedLabel }}</strong>
      </article>
    </section>

    <section class="settings-diagnostic-panel__section">
      <p class="detail-panel__label">系统边界</p>
      <div class="settings-diagnostic-panel__grid settings-diagnostic-panel__grid--dense">
        <article class="settings-diagnostic-panel__metric">
          <span>数据库</span>
          <strong>{{ diagnostics?.databasePath ?? "暂无数据库路径" }}</strong>
        </article>
        <article class="settings-diagnostic-panel__metric">
          <span>缓存目录</span>
          <strong>{{ diagnostics?.cacheDir ?? "暂无缓存目录" }}</strong>
        </article>
        <article class="settings-diagnostic-panel__metric">
          <span>日志目录</span>
          <strong>{{ diagnostics?.logDir ?? "暂无日志目录" }}</strong>
        </article>
        <article class="settings-diagnostic-panel__metric">
          <span>Provider / 能力</span>
          <strong>{{ configuredProviderCount }}/{{ providerCount }} · {{ enabledCapabilityCount }}</strong>
        </article>
      </div>
    </section>

    <section class="settings-diagnostic-panel__section">
      <p class="detail-panel__label">当前焦点</p>
      <div class="settings-diagnostic-panel__metric">
        <span>选中 Provider</span>
        <strong>{{ selectedProviderLabel }}</strong>
      </div>
      <div class="settings-diagnostic-panel__metric">
        <span>连接状态</span>
        <strong>{{ selectedProviderHealth?.status ?? "待检查" }}</strong>
      </div>
      <p class="settings-diagnostic-panel__message">
        {{ selectedProviderHealth?.message ?? "尚未执行连接检查。" }}
      </p>
    </section>

    <section
      v-if="errors.length > 0"
      class="settings-diagnostic-panel__section settings-diagnostic-panel__section--error"
    >
      <p class="detail-panel__label">异常</p>
      <p v-for="error in errors" :key="error" class="settings-diagnostic-panel__message">
        {{ error }}
      </p>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { AIProviderHealth, RuntimeDiagnostics } from "@/types/runtime";

type SettingsSectionId = "system" | "provider" | "capability" | "diagnostics";

const props = defineProps<{
  configStatusLabel: string;
  configuredProviderCount: number;
  diagnostics: RuntimeDiagnostics | null;
  enabledCapabilityCount: number;
  errors: string[];
  lastSyncedLabel: string;
  licenseLabel: string;
  providerCount: number;
  runtimeStatusLabel: string;
  section: SettingsSectionId;
  selectedProviderHealth: AIProviderHealth | null;
  selectedProviderLabel: string;
}>();

const sectionSummary = computed(() => {
  return (
    {
      system: "检查 Runtime、路径、日志和默认 AI 配置是否已经同步到配置总线。",
      provider: "检查当前 Provider 的凭据、模型目录和连接状态是否可用。",
      capability: "检查能力矩阵、默认模型和提示词策略是否能正确落到运行态。",
      diagnostics: "集中查看错误、依赖边界和系统可用性，便于定位阻断点。"
    }[props.section] ?? "检查当前设置区的运行状态。"
  );
});
</script>

<style scoped>
.settings-diagnostic-panel {
  display: grid;
  align-content: start;
  gap: 14px;
}

.settings-diagnostic-panel__hero {
  display: grid;
  gap: 8px;
  padding: 18px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.settings-diagnostic-panel__hero h2 {
  margin: 0;
}

.settings-diagnostic-panel__hero p:last-child,
.settings-diagnostic-panel__message {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.settings-diagnostic-panel__grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.settings-diagnostic-panel__grid--dense {
  grid-template-columns: 1fr;
}

.settings-diagnostic-panel__metric {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
}

.settings-diagnostic-panel__metric span {
  color: var(--text-secondary);
  font-size: 12px;
}

.settings-diagnostic-panel__metric strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}

.settings-diagnostic-panel__section {
  display: grid;
  gap: 10px;
}

.settings-diagnostic-panel__section--error .settings-diagnostic-panel__metric {
  border-color: color-mix(in srgb, var(--status-error) 28%, var(--border-default));
}

@media (max-width: 980px) {
  .settings-diagnostic-panel__grid {
    grid-template-columns: 1fr;
  }
}
</style>
