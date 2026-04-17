<template>
  <aside class="settings-diagnostic-panel">
    <div class="settings-diagnostic-panel__hero">
      <p class="detail-panel__label">诊断台</p>
      <h2>当前运行视图</h2>
      <p>{{ sectionSummary }}</p>
    </div>

    <section class="detail-panel__section">
      <div class="detail-panel__metric">
        <span>Runtime 状态</span>
        <strong>{{ runtimeStatusLabel }}</strong>
      </div>
      <div class="detail-panel__metric">
        <span>授权状态</span>
        <strong>{{ licenseLabel }}</strong>
      </div>
      <div class="detail-panel__metric">
        <span>配置状态</span>
        <strong>{{ configStatusLabel }}</strong>
      </div>
      <div class="detail-panel__metric">
        <span>最近同步</span>
        <strong>{{ lastSyncedLabel }}</strong>
      </div>
    </section>

    <section class="detail-panel__section">
      <p class="detail-panel__label">系统边界</p>
      <div class="detail-panel__metric">
        <span>数据库</span>
        <strong>{{ diagnostics?.databasePath ?? "-" }}</strong>
      </div>
      <div class="detail-panel__metric">
        <span>日志目录</span>
        <strong>{{ diagnostics?.logDir ?? "-" }}</strong>
      </div>
      <div class="detail-panel__metric">
        <span>Provider</span>
        <strong>{{ configuredProviderCount }}/{{ providerCount }}</strong>
      </div>
      <div class="detail-panel__metric">
        <span>启用能力</span>
        <strong>{{ enabledCapabilityCount }}</strong>
      </div>
    </section>

    <section class="detail-panel__section">
      <p class="detail-panel__label">当前焦点</p>
      <div class="detail-panel__metric">
        <span>选中 Provider</span>
        <strong>{{ selectedProviderLabel }}</strong>
      </div>
      <div class="detail-panel__metric">
        <span>连接状态</span>
        <strong>{{ selectedProviderHealth?.status ?? "待检查" }}</strong>
      </div>
      <p class="settings-diagnostic-panel__message">
        {{ selectedProviderHealth?.message ?? "尚未执行连接检查。" }}
      </p>
    </section>

    <section v-if="errors.length > 0" class="detail-panel__section settings-diagnostic-panel__errors">
      <p class="detail-panel__label">异常</p>
      <p v-for="error in errors" :key="error" class="settings-diagnostic-panel__message">
        {{ error }}
      </p>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { RuntimeDiagnostics, AIProviderHealth } from "@/types/runtime";

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
      system: "检查 Runtime、目录、日志与默认模型是否处于可保存状态。",
      provider: "确认当前 Provider 的凭据、模型目录和能力边界是否可用。",
      capability: "对齐能力默认模型、Provider 绑定和提示词策略。",
      diagnostics: "收口错误、路径、配置修订号和当前可用性。"
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
  border-radius: 20px;
  background:
    radial-gradient(circle at top right, color-mix(in srgb, var(--brand-primary) 16%, transparent), transparent 32%),
    color-mix(in srgb, var(--surface-secondary) 92%, transparent);
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

.settings-diagnostic-panel__errors {
  border-color: color-mix(in srgb, var(--status-error) 28%, var(--border-default));
  background: color-mix(in srgb, var(--status-error) 8%, var(--surface-secondary));
}
</style>
