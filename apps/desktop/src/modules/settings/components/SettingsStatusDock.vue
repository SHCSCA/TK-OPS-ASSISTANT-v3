<template>
  <section class="settings-status-dock">
    <div class="settings-status-dock__copy">
      <p class="detail-panel__label">系统健康总览</p>
      <h1>AI 与系统设置</h1>
      <p class="workspace-page__summary">
        把 Runtime、授权、Provider、模型和能力策略收束到同一条控制总线里。
      </p>
    </div>

    <div class="settings-status-dock__metrics">
      <article class="status-tile">
        <p class="detail-panel__label">Runtime</p>
        <strong>{{ runtimeStatusLabel }}</strong>
        <span>版本 {{ versionLabel }}</span>
      </article>
      <article class="status-tile">
        <p class="detail-panel__label">授权</p>
        <strong>{{ licenseLabel }}</strong>
        <span>修订号 {{ revisionLabel }}</span>
      </article>
      <article class="status-tile">
        <p class="detail-panel__label">Provider</p>
        <strong>{{ configuredProviderCount }}/{{ providerCount }}</strong>
        <span>已配置 Provider</span>
      </article>
      <article class="status-tile">
        <p class="detail-panel__label">能力</p>
        <strong>{{ enabledCapabilityCount }}</strong>
        <span>已启用能力</span>
      </article>
    </div>

    <div class="settings-status-dock__meta">
      <span class="page-chip page-chip--muted">{{ configStatusLabel }}</span>
      <span class="page-chip">最近同步 {{ lastSyncedLabel }}</span>
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
  gap: 18px;
  padding: 24px 24px 20px;
  border: 1px solid var(--border-default);
  border-radius: 24px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--surface-secondary) 94%, transparent), color-mix(in srgb, var(--surface-tertiary) 88%, transparent)),
    radial-gradient(circle at top left, color-mix(in srgb, var(--brand-primary) 18%, transparent), transparent 30%);
  box-shadow: var(--shadow-md);
}

.settings-status-dock__copy {
  display: grid;
  gap: 8px;
  max-width: 720px;
}

.settings-status-dock__metrics {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.status-tile {
  display: grid;
  gap: 6px;
  min-height: 118px;
  padding: 16px 18px;
  border: 1px solid color-mix(in srgb, var(--border-default) 78%, transparent);
  border-radius: 18px;
  background: color-mix(in srgb, var(--surface-primary) 70%, transparent);
}

.status-tile strong {
  font-size: 26px;
  line-height: 1;
}

.status-tile span {
  color: var(--text-secondary);
  font-size: 13px;
}

.settings-status-dock__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 1120px) {
  .settings-status-dock__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .settings-status-dock {
    padding: 20px 18px 18px;
  }

  .settings-status-dock__metrics {
    grid-template-columns: 1fr;
  }
}
</style>
