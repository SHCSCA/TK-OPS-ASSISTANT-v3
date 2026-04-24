<template>
  <section class="settings-status-dock">
    <div class="settings-status-dock__copy">
      <p class="detail-panel__label">系统总览</p>
      <h1>AI 与系统设置</h1>
      <p class="workspace-page__summary">
        Runtime、授权、Provider、模型和能力配置都收束到统一控制台，状态变化直接来自配置总线和能力总线。
      </p>
    </div>

    <div class="settings-status-dock__metrics">
      <article class="settings-status-dock__metric">
        <p class="detail-panel__label">Runtime</p>
        <strong>{{ runtimeStatusLabel }}</strong>
        <span>版本 {{ versionLabel }}</span>
      </article>
      <article class="settings-status-dock__metric">
        <p class="detail-panel__label">授权</p>
        <strong>{{ licenseLabel }}</strong>
        <span>修订号 {{ revisionLabel }}</span>
      </article>
      <article class="settings-status-dock__metric">
        <p class="detail-panel__label">Provider</p>
        <strong>{{ configuredProviderCount }}/{{ providerCount }}</strong>
        <span>已接入 Provider</span>
      </article>
      <article class="settings-status-dock__metric">
        <p class="detail-panel__label">能力</p>
        <strong>{{ enabledCapabilityCount }}</strong>
        <span>已启用能力</span>
      </article>
    </div>

    <div class="settings-status-dock__meta">
      <span class="settings-status-dock__pill">{{ configStatusLabel }}</span>
      <span class="settings-status-dock__pill settings-status-dock__pill--muted">最近同步 {{ lastSyncedLabel }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  configStatusLabel: string;
  configuredProviderCount: number;
  enabledCapabilityCount: number;
  lastSyncedLabel: string;
  licenseLabel: string;
  providerCount: number;
  revisionLabel: number | string;
  runtimeStatusLabel: string;
  versionLabel: string;
}>();
</script>

<style scoped>
.settings-status-dock {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-5);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.settings-status-dock__copy {
  display: grid;
  gap: var(--space-2);
  max-width: 680px;
}

.settings-status-dock__copy .detail-panel__label,
.settings-status-dock__copy h1,
.settings-status-dock__copy .workspace-page__summary,
.settings-status-dock__metric .detail-panel__label {
  margin: 0;
}

.settings-status-dock__copy h1 {
  font: var(--font-display-md);
  letter-spacing: 0;
}

.settings-status-dock__copy .workspace-page__summary {
  color: var(--text-secondary);
  font: var(--font-body-sm);
  letter-spacing: 0;
}

.settings-status-dock__metrics {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.settings-status-dock__metric {
  display: grid;
  gap: var(--space-1);
  min-height: 88px;
  padding: var(--space-4);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 96%, transparent);
}

.settings-status-dock__metric strong {
  font: var(--font-title-lg);
  letter-spacing: 0;
}

.settings-status-dock__metric span {
  color: var(--text-secondary);
  font: var(--font-body-sm);
  letter-spacing: 0;
}

.settings-status-dock__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.settings-status-dock__pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid var(--border-default);
  border-radius: 999px;
  background: color-mix(in srgb, var(--surface-primary) 94%, transparent);
  color: var(--text-primary);
  font: var(--font-caption);
  letter-spacing: 0;
}

.settings-status-dock__pill--muted {
  color: var(--text-secondary);
}

@media (max-width: 1120px) {
  .settings-status-dock__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .settings-status-dock {
    padding: var(--space-4);
  }

  .settings-status-dock__metrics {
    grid-template-columns: 1fr;
  }
}
</style>
