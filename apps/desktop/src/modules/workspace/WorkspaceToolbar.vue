<template>
  <header class="workspace-toolbar" aria-label="AI 剪辑工具栏">
    <div class="workspace-toolbar__identity">
      <span class="workspace-toolbar__eyebrow">M05 AI 剪辑工作台</span>
      <strong class="workspace-toolbar__project">{{ projectName }}</strong>
    </div>

    <div class="workspace-toolbar__tools" aria-label="时间线工具">
      <button class="workspace-icon-button" type="button" disabled title="选择">
        <span class="material-symbols-outlined">cursor_default</span>
      </button>
      <button class="workspace-icon-button" type="button" disabled title="剪切">
        <span class="material-symbols-outlined">content_cut</span>
      </button>
      <button class="workspace-icon-button" type="button" disabled title="缩放">
        <span class="material-symbols-outlined">zoom_in</span>
      </button>
      <span class="workspace-toolbar__hint">轨道编辑会在真实素材接入后开放</span>
    </div>

    <div class="workspace-toolbar__actions">
      <span v-if="blockedMessage" class="workspace-toolbar__status">
        {{ blockedMessage }}
      </span>
      <button
        class="workspace-button workspace-button--ghost"
        data-testid="workspace-create-draft-button"
        type="button"
        :disabled="isBusy || hasTimeline"
        @click="$emit('create-draft')"
      >
        创建时间线草稿
      </button>
      <button
        class="workspace-button workspace-button--ghost"
        type="button"
        :disabled="isBusy || !hasTimeline"
        @click="$emit('save')"
      >
        保存草稿
      </button>
      <button
        class="workspace-button workspace-button--primary"
        data-testid="workspace-magic-cut-button"
        type="button"
        :disabled="isBusy || !hasTimeline"
        @click="$emit('magic-cut')"
      >
        <span class="material-symbols-outlined">auto_fix_high</span>
        AI 魔法剪
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { EditingWorkspaceStatus } from "@/stores/editing-workspace";

const props = defineProps<{
  blockedMessage: string | null;
  hasTimeline: boolean;
  projectName: string;
  status: EditingWorkspaceStatus;
}>();

defineEmits<{
  "create-draft": [];
  "magic-cut": [];
  save: [];
}>();

const isBusy = computed(() => props.status === "loading" || props.status === "saving");
</script>
