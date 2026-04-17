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
      class="workspace-button workspace-button--primary"
      data-testid="workspace-empty-create-button"
      type="button"
      @click="$emit('create-draft')"
    >
      创建时间线草稿
    </button>
    <button
      v-else-if="status === 'error'"
      class="workspace-button workspace-button--ghost"
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

const shouldRender = computed(() =>
  ["loading", "empty", "blocked", "error"].includes(props.status)
);

const icon = computed(() => {
  if (props.status === "loading") return "sync";
  if (props.status === "error") return "error";
  if (props.status === "blocked") return "lock";
  return "timeline";
});

const title = computed(() => {
  if (props.status === "loading") return "正在读取项目时间线";
  if (props.status === "error") return "时间线请求失败";
  if (props.status === "blocked") return "AI 能力暂未接入";
  return "当前项目还没有时间线草稿";
});

const description = computed(() => {
  if (props.status === "loading") return "正在通过 Runtime 获取当前项目的真实草稿。";
  if (props.status === "error") return props.errorMessage ?? "请求失败，请稍后重试。";
  if (props.status === "blocked") {
    return props.blockedMessage ?? "AI 剪辑命令尚未接入 Provider。";
  }
  return props.blockedMessage ?? "创建空草稿后，可以把真实素材、配音和字幕逐步落到同一条时间线。";
});
</script>
