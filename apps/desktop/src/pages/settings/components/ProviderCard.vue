<template>
  <button 
    class="provider-card" 
    :data-status="status"
    @click="$emit('configure', provider.provider)"
  >
    <div class="provider-icon">
      {{ provider.provider.slice(0, 2).toUpperCase() }}
    </div>
    <div class="provider-info">
      <div class="provider-name-row">
        <strong class="provider-name">{{ provider.label }}</strong>
        <div class="status-indicator">
          <span class="status-dot" :class="status"></span>
          <span class="status-text">{{ statusLabel }}</span>
        </div>
      </div>
      <div class="provider-models">
        {{ modelsLabel }}
      </div>
      <div class="provider-key-hint">
        {{ keyHint }}
      </div>
      <div class="capability-chips">
        <Chip v-if="provider.capabilities.includes('text_generation')" size="sm">文本 ✓</Chip>
        <Chip v-if="provider.capabilities.includes('vision')" size="sm">视觉 ✓</Chip>
        <Chip v-if="provider.capabilities.includes('tts')" size="sm">TTS ✓</Chip>
        <Chip v-if="provider.capabilities.includes('video_generation')" size="sm">视频 ✓</Chip>
        <Chip v-if="provider.capabilities.includes('asset_analysis')" size="sm">分析 ✓</Chip>
      </div>
    </div>
    <div class="provider-actions">
      <Button variant="ghost" size="sm" @click.stop="$emit('test', provider.provider)">测试</Button>
      <span class="material-symbols-outlined action-arrow">chevron_right</span>
    </div>
  </button>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ProviderCardState } from "../types";
import Button from "@/components/ui/Button/Button.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const props = defineProps<{
  provider: ProviderCardState;
}>();

defineEmits<{
  (e: "configure", id: string): void;
  (e: "test", id: string): void;
}>();

const status = computed(() => {
  if (props.provider.status === "testing") return "testing";
  if (!props.provider.configured) return "missing_secret";
  if (props.provider.health?.status === "ready") return "ready";
  if (props.provider.health?.status === "misconfigured" || props.provider.health?.status === "error") return "misconfigured";
  if (props.provider.status === "ready") return "ready";
  if (props.provider.configured) return "offline";
  return "missing_secret";
});

const statusLabel = computed(() => {
  switch (status.value) {
    case "testing": return "测试中...";
    case "ready": return `就绪 · ${props.provider.health?.latencyMs ?? 0}ms`;
    case "misconfigured": return "配置异常";
    case "missing_secret": return "未配置";
    default: return "离线";
  }
});

const modelsLabel = computed(() => {
  if (props.provider.models && props.provider.models.length > 0) {
    const names = props.provider.models.slice(0, 2).map(m => m.modelId);
    const count = props.provider.models.length;
    return count > 2 ? `${names.join(", ")} 等 ${count} 个模型` : names.join(", ");
  }
  return "等待拉取模型列表";
});

const keyHint = computed(() => {
  return props.provider.configured ? "API Key: 已加密存储" : "API Key: 未设置";
});
</script>

<style scoped>
.provider-card {
  display: grid;
  grid-template-columns: 40px 1fr auto;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  transition: border-color var(--motion-fast) var(--ease-standard), box-shadow var(--motion-fast) var(--ease-spring);
  cursor: pointer;
  text-align: left;
  align-items: start;
}

.provider-card:hover {
  border-color: var(--color-border-default);
  box-shadow: var(--shadow-md);
}

.provider-card[data-status="ready"] { border-left: 3px solid var(--color-success); }
.provider-card[data-status="misconfigured"] { border-left: 3px solid var(--color-warning); }
.provider-card[data-status="missing_secret"] { border-left: 3px solid var(--color-border-subtle); }
.provider-card[data-status="offline"] { border-left: 3px solid var(--color-danger); }
.provider-card[data-status="testing"] { border-left: 3px solid var(--color-info); }

.provider-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--color-bg-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  font: var(--font-title-sm);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  flex-shrink: 0;
}

.provider-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.provider-name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.provider-name {
  font: var(--font-title-md);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-bg-muted);
}

.status-dot.ready { background: var(--color-success); box-shadow: 0 0 8px var(--color-success); }
.status-dot.misconfigured { background: var(--color-warning); }
.status-dot.offline { background: var(--color-danger); }
.status-dot.testing { background: var(--color-info); animation: pulse 1.2s infinite; }

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.status-text {
  font: var(--font-caption);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.provider-models {
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.provider-key-hint {
  font: var(--font-caption);
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.capability-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: var(--space-3);
}

.provider-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.action-arrow {
  color: var(--color-text-tertiary);
  font-size: 20px;
}
</style>
