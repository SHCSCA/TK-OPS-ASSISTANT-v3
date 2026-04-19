<template>
  <div
    v-if="health"
    class="test-result-card"
    :data-status="health.status"
    :data-animate="animateState"
  >
    <div class="result-main">
      <span class="status-dot" :class="health.status" />
      <strong>{{ health.status === 'ready' ? '就绪' : '连接失败' }}</strong>
      <span v-if="health.status === 'ready' && health.latencyMs" class="latency">
        · 延迟 {{ health.latencyMs }}ms
      </span>
      <span v-if="health.model" class="model-tag">· {{ health.model }}</span>
    </div>
    <div class="result-time">
      测试时间 {{ formatDateTime(health.checkedAt) }}
    </div>
    <div v-if="health.status !== 'ready' && health.message" class="result-error">
      {{ health.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import type { AIProviderHealth } from "../types";

const props = defineProps<{
  health: AIProviderHealth | null;
}>();

const animateState = ref<"none" | "success" | "failure">("none");

/** 监听 health 变化触发动画 */
watch(() => props.health, (newVal, oldVal) => {
  if (!newVal || newVal === oldVal) return;
  animateState.value = newVal.status === "ready" ? "success" : "failure";
  setTimeout(() => { animateState.value = "none"; }, 1200);
});

function formatDateTime(val?: string | null) {
  if (!val) return "-";
  return new Date(val).toLocaleString("zh-CN");
}
</script>

<style scoped>
.test-result-card {
  padding: var(--space-4);
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-border-default);
  transition: border-color var(--motion-fast) var(--ease-standard),
              background var(--motion-fast) var(--ease-standard),
              box-shadow var(--motion-default) var(--ease-standard);
}

.test-result-card[data-status="ready"] {
  border-left-color: var(--color-success);
  background: color-mix(in srgb, var(--color-success) 5%, var(--color-bg-muted));
}

.test-result-card[data-status="error"],
.test-result-card[data-status="misconfigured"],
.test-result-card[data-status="offline"] {
  border-left-color: var(--color-danger);
}

/* 成功发光动画 */
.test-result-card[data-animate="success"] {
  animation: glow-success 1s var(--ease-decelerate) forwards;
}

/* 失败抖动动画 */
.test-result-card[data-animate="failure"] {
  animation: shake 240ms var(--ease-standard);
}

@keyframes glow-success {
  0% { box-shadow: 0 0 24px var(--color-success); }
  100% { box-shadow: 0 0 0 transparent; }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  16% { transform: translateX(-2px); }
  33% { transform: translateX(2px); }
  50% { transform: translateX(-2px); }
  66% { transform: translateX(2px); }
  83% { transform: translateX(-1px); }
}

.result-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.ready { background: var(--color-success); box-shadow: 0 0 8px var(--color-success); }
.status-dot.error,
.status-dot.misconfigured,
.status-dot.offline { background: var(--color-danger); }

.latency, .model-tag {
  color: var(--color-text-secondary);
  font: var(--font-body-sm);
}

.result-time {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  margin-top: 4px;
}

.result-error {
  margin-top: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: color-mix(in srgb, var(--color-danger) 8%, transparent);
  color: var(--color-danger);
  font: var(--font-mono-md);
  border-radius: var(--radius-xs);
  word-break: break-all;
}
</style>
