<template>
  <header class="workspace-toolbar" aria-label="工作台顶部操作栏">
    <div class="workspace-toolbar__identity">
      <span class="material-symbols-outlined">movie_edit</span>
      <div>
        <span class="workspace-toolbar__eyebrow">AI 剪辑工作台</span>
        <strong class="workspace-toolbar__project">{{ projectName }}</strong>
      </div>
      <span class="workspace-toolbar__tag">核心创作中枢</span>
    </div>

    <div class="workspace-toolbar__status">
      <span class="workspace-toolbar__pill">
        {{ timelineName }}
      </span>
      <span class="workspace-toolbar__pill" :data-tone="statusTone">
        {{ statusLabel }}
      </span>
      <span class="workspace-toolbar__pill">
        {{ selectionLabel }}
      </span>
    </div>

    <div class="workspace-toolbar__actions">
      <button class="workspace-toolbar__button workspace-toolbar__button--ghost" type="button" disabled>
        <span class="material-symbols-outlined">play_arrow</span>
        预览
      </button>
      <button class="workspace-toolbar__button workspace-toolbar__button--ghost" type="button" disabled>
        <span class="material-symbols-outlined">movie</span>
        渲染
      </button>
      <button
        class="workspace-toolbar__button workspace-toolbar__button--ghost"
        data-testid="workspace-create-draft-button"
        type="button"
        :disabled="createDisabled"
        @click="$emit('create-draft')"
      >
        <span class="material-symbols-outlined">add</span>
        创建时间线
      </button>
      <button
        class="workspace-toolbar__button workspace-toolbar__button--primary"
        type="button"
        :disabled="saveDisabled"
        @click="$emit('save')"
      >
        <span class="material-symbols-outlined">save</span>
        保存草稿
      </button>
    </div>

    <p v-if="blockedMessage" class="workspace-toolbar__note">
      {{ blockedMessage }}
    </p>
  </header>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { EditingWorkspaceStatus } from "@/stores/editing-workspace";

const props = defineProps<{
  blockedMessage: string | null;
  hasTimeline: boolean;
  projectName: string;
  selectionLabel: string;
  status: EditingWorkspaceStatus;
  timelineName: string;
}>();

defineEmits<{
  "create-draft": [];
  save: [];
}>();

const isBusy = computed(() => props.status === "loading" || props.status === "saving");
const createDisabled = computed(() => isBusy.value || props.hasTimeline);
const saveDisabled = computed(() => isBusy.value || !props.hasTimeline);
const statusLabel = computed(() => {
  const map: Record<EditingWorkspaceStatus, string> = {
    blocked: "AI 阻断",
    empty: "空态",
    error: "错误",
    idle: "待加载",
    loading: "加载中",
    ready: "已就绪",
    saving: "保存中"
  };
  return map[props.status];
});
const statusTone = computed(() => {
  if (props.status === "error") return "danger";
  if (props.status === "blocked") return "warning";
  if (props.status === "ready") return "success";
  return "neutral";
});
</script>

<style scoped>
.workspace-toolbar {
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 12%, transparent), transparent 58%),
    color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 20px;
  box-shadow: var(--shadow-sm);
  display: grid;
  gap: 14px;
  padding: 18px 20px;
}

.workspace-toolbar__identity,
.workspace-toolbar__status,
.workspace-toolbar__actions {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.workspace-toolbar__identity {
  color: var(--text-primary);
}

.workspace-toolbar__eyebrow {
  color: var(--text-tertiary);
  display: block;
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.workspace-toolbar__project {
  display: block;
  font-size: 18px;
}

.workspace-toolbar__tag,
.workspace-toolbar__pill {
  background: color-mix(in srgb, var(--surface-tertiary) 94%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 999px;
  color: var(--text-secondary);
  font-size: 12px;
  padding: 6px 12px;
}

.workspace-toolbar__tag {
  color: var(--brand-primary);
}

.workspace-toolbar__pill[data-tone="success"] {
  border-color: color-mix(in srgb, var(--color-success) 36%, var(--border-default));
  color: var(--color-success);
}

.workspace-toolbar__pill[data-tone="warning"] {
  border-color: color-mix(in srgb, var(--color-warning) 36%, var(--border-default));
  color: var(--color-warning);
}

.workspace-toolbar__pill[data-tone="danger"] {
  border-color: color-mix(in srgb, var(--color-danger) 36%, var(--border-default));
  color: var(--color-danger);
}

.workspace-toolbar__button {
  align-items: center;
  border: 1px solid transparent;
  border-radius: 8px;
  display: inline-flex;
  gap: 8px;
  height: 38px;
  padding: 0 14px;
}

.workspace-toolbar__button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.workspace-toolbar__button--ghost {
  background: transparent;
  border-color: var(--border-default);
  color: var(--text-primary);
}

.workspace-toolbar__button--primary {
  background: var(--brand-primary);
  color: var(--text-inverse, #041314);
}

.workspace-toolbar__note {
  color: var(--color-warning);
  margin: 0;
}

@media (max-width: 960px) {
  .workspace-toolbar__identity,
  .workspace-toolbar__status,
  .workspace-toolbar__actions {
    align-items: stretch;
  }
}
</style>
