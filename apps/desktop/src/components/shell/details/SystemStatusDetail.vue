<template>
  <div class="system-status-detail">
    <section class="detail-section">
      <div class="detail-section__header">
        <p class="detail-section__title">系统状态</p>
        <span class="live-indicator">
          <span class="live-indicator__dot"></span>
          <span class="live-indicator__text">Live</span>
        </span>
      </div>

      <div class="status-row">
        <div class="status-row__info">
          <p class="status-row__label">Runtime 引擎</p>
          <p class="status-row__sub">{{ runtimeVersion }}</p>
        </div>
        <p class="status-row__value" :class="runtimeLabel.includes('在线') ? 'status-row__value--active' : 'status-row__value--inactive'">
          {{ runtimeLabel.includes('在线') ? 'Active' : 'Inactive' }}
        </p>
      </div>

      <div class="status-row">
        <div class="status-row__info">
          <p class="status-row__label">许可证授权</p>
          <p class="status-row__sub">{{ maskedCode }}</p>
        </div>
        <p class="status-row__value" :class="licenseLabel.includes('已激活') ? 'status-row__value--active' : 'status-row__value--inactive'">
          {{ licenseLabel.includes('已激活') ? 'Active' : 'Inactive' }}
        </p>
      </div>

      <div class="status-row">
        <div class="status-row__info">
          <p class="status-row__label">配置总线</p>
          <p class="status-row__sub">{{ configStatusLabel }}</p>
        </div>
        <p class="status-row__value" :class="configStatusLabel.includes('就绪') ? 'status-row__value--active' : 'status-row__value--inactive'">
          {{ configStatusLabel.includes('就绪') ? 'Active' : 'Inactive' }}
        </p>
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
defineProps<{
  configStatusLabel: string;
  licenseLabel: string;
  maskedCode: string;
  projectName: string;
  projectStatus: string;
  runtimeLabel: string;
  runtimeVersion: string;
}>();
</script>

<style scoped>
.detail-section {
  border-bottom: 1px solid var(--border-default);
  padding: 16px 0;
}

.detail-section:first-child {
  padding-top: 0;
}

.detail-section:last-child {
  border-bottom: none;
}

.detail-section__header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.detail-section__title {
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.05em;
  margin: 0;
  text-transform: uppercase;
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
  height: 6px;
  width: 6px;
  box-shadow: 0 0 6px var(--brand-primary);
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.live-indicator__text {
  color: var(--brand-primary);
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-row {
  align-items: center;
  background: var(--surface-tertiary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  padding: 10px 14px;
}

.status-row__info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-row__label {
  font-size: 13px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary);
}

.status-row__sub {
  color: var(--text-tertiary);
  font-size: 11px;
  margin: 0;
  font-family: var(--font-mono);
}

.status-row__value {
  font-size: 12px;
  font-weight: 800;
  margin: 0;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: var(--surface-secondary);
}

.status-row__value--active {
  color: var(--status-success);
}

.status-row__value--inactive {
  color: var(--status-error);
}

.project-context strong {
  display: block;
  font-size: 15px;
  margin-bottom: 6px;
  font-weight: 800;
}

.project-context p {
  color: var(--text-tertiary);
  font-size: 13px;
  margin: 0;
}

.detail-section__empty {
  color: var(--status-warning);
  font-size: 13px;
  margin: 0;
  line-height: 1.6;
  background: color-mix(in srgb, var(--status-warning) 10%, transparent);
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid color-mix(in srgb, var(--status-warning) 20%, transparent);
}
</style>
