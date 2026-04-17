<template>
  <section
    v-if="shouldRender"
    class="workspace-state-notice"
    :class="`workspace-state-notice--${status}`"
    aria-live="polite"
  >
    <span class="material-symbols-outlined workspace-state-notice__icon">
      {{ icon }}
    </span>
    <div class="workspace-state-notice__copy">
      <strong>{{ title }}</strong>
      <p>{{ description }}</p>
    </div>
    <button
      v-if="status === 'empty'"
      class="workspace-state-notice__button workspace-state-notice__button--primary"
      data-testid="workspace-empty-create-button"
      type="button"
      @click="$emit('create-draft')"
    >
      创建时间线草稿
    </button>
    <button
      v-else-if="status === 'error'"
      class="workspace-state-notice__button workspace-state-notice__button--ghost"
      type="button"
      @click="$emit('retry')"
    >
      重试
    </button>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { EditingWorkspaceStatus } from "@/stores/editing-workspace";

const props = defineProps<{
  blockedMessage: string | null;
  errorMessage: string | null;
  status: EditingWorkspaceStatus;
}>();

defineEmits<{
  "create-draft": [];
  retry: [];
}>();

const shouldRender = computed(() => ["loading", "empty", "blocked", "error"].includes(props.status));

const icon = computed(() => {
  if (props.status === "loading") return "progress_activity";
  if (props.status === "error") return "error";
  if (props.status === "blocked") return "lock";
  return "timeline";
});

const title = computed(() => {
  if (props.status === "loading") return "正在读取项目时间线";
  if (props.status === "error") return "时间线请求失败";
  if (props.status === "blocked") return "AI 命令进入 blocked";
  return "当前项目还没有时间线草稿";
});

const description = computed(() => {
  if (props.status === "loading") return "正在通过 Runtime 获取当前项目的真实时间线草稿。";
  if (props.status === "error") return props.errorMessage ?? "请求失败，请稍后重试。";
  if (props.status === "blocked") {
    return props.blockedMessage ?? "当前 AI Provider 尚未接入，命令不会创建伪任务。";
  }
  return "创建空草稿后，素材区、预览区、时间线和 AI 工具条才会进入真实工作台语义。";
});
</script>

<style scoped>
.workspace-state-notice {
  align-items: center;
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 18px;
  display: flex;
  gap: 14px;
  padding: 14px 16px;
}

.workspace-state-notice__copy {
  flex: 1;
}

.workspace-state-notice__copy p {
  color: var(--text-secondary);
  margin: 0;
}

.workspace-state-notice--error {
  border-color: color-mix(in srgb, var(--color-danger) 35%, var(--border-default));
}

.workspace-state-notice--blocked {
  border-color: color-mix(in srgb, var(--color-warning) 35%, var(--border-default));
}

.workspace-state-notice__button {
  border: 1px solid transparent;
  border-radius: 8px;
  height: 36px;
  padding: 0 14px;
}

.workspace-state-notice__button--primary {
  background: var(--brand-primary);
  color: var(--text-inverse, #041314);
}

.workspace-state-notice__button--ghost {
  background: transparent;
  border-color: var(--border-default);
  color: var(--text-primary);
}

@media (max-width: 960px) {
  .workspace-state-notice {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
