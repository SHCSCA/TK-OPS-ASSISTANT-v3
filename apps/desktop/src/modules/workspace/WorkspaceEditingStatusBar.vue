<template>
  <footer class="workspace-editing-status-bar" data-testid="workspace-editing-status-bar">
    <div class="workspace-editing-status-bar__item" data-testid="workspace-status-playhead">
      <span class="material-symbols-outlined" aria-hidden="true">schedule</span>
      <strong>{{ playheadLabel }}</strong>
      <small>{{ isPlaying ? "播放中" : "已暂停" }}</small>
    </div>

    <div class="workspace-editing-status-bar__item" data-testid="workspace-status-selection">
      <span class="material-symbols-outlined" aria-hidden="true">ads_click</span>
      <strong>{{ selectionLabel }}</strong>
    </div>

    <div class="workspace-editing-status-bar__item" :data-tone="saveTone" data-testid="workspace-status-save">
      <span class="material-symbols-outlined" aria-hidden="true">{{ saveIcon }}</span>
      <strong>{{ saveLabel }}</strong>
    </div>

    <div class="workspace-editing-status-bar__item" :data-tone="precheckTone" data-testid="workspace-status-precheck">
      <span class="material-symbols-outlined" aria-hidden="true">rule_settings</span>
      <strong>{{ precheckLabel }}</strong>
    </div>

    <div class="workspace-editing-status-bar__item" :data-tone="previewTone" data-testid="workspace-status-preview">
      <span class="material-symbols-outlined" aria-hidden="true">{{ previewIcon }}</span>
      <strong>{{ previewLabel }}</strong>
    </div>

    <div class="workspace-editing-status-bar__item" :data-tone="taskTone" data-testid="workspace-status-task">
      <span class="material-symbols-outlined" aria-hidden="true">{{ taskIcon }}</span>
      <strong>{{ taskLabel }}</strong>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { computed } from "vue";

import { buildWorkspaceCommandFeedback } from "./workspaceCommandFeedback";
import type { WorkspacePreviewContext } from "./workspacePreviewContext";
import { formatWorkspaceTime } from "./workspaceTimelineViewModel";
import type { TimelinePrecheckDto, WorkspaceAICommandResultDto, WorkspaceSaveStateDto } from "@/types/runtime";
import type { TaskInfo } from "@/types/task-events";

const props = defineProps<{
  activeTask: TaskInfo | null;
  isPlaying: boolean;
  lastCommandResult: WorkspaceAICommandResultDto | null;
  playheadMs: number;
  precheck: TimelinePrecheckDto | null;
  previewContext: WorkspacePreviewContext;
  saveState: WorkspaceSaveStateDto | null;
  selectionLabel: string;
}>();

const playheadLabel = computed(() => formatWorkspaceTime(props.playheadMs));

const saveTone = computed(() => (props.saveState?.saved ? "ready" : "warning"));
const saveIcon = computed(() => (props.saveState?.saved ? "cloud_done" : "edit_note"));
const saveLabel = computed(() => {
  if (!props.saveState) return "未保存";
  return props.saveState.saved ? "已保存" : "需保存";
});

const precheckTone = computed(() => {
  if (!props.precheck) return "muted";
  return props.precheck.status === "ready" ? "ready" : "warning";
});
const precheckLabel = computed(() => {
  if (!props.precheck) return "未预检";
  return props.precheck.status === "ready" ? "预检通过" : "预检需处理";
});

const previewTone = computed(() => {
  if (props.previewContext.runtimePreviewErrorMessage) return "warning";
  return props.previewContext.previewMode === "media" ? "ready" : "muted";
});
const previewIcon = computed(() => (props.previewContext.previewMode === "media" ? "movie" : "account_tree"));
const previewLabel = computed(() => {
  if (props.previewContext.runtimePreviewErrorMessage) return "预览需同步";
  return props.previewContext.previewMode === "media" ? "真实媒体" : "结构预览";
});

const taskFeedback = computed(() => buildWorkspaceCommandFeedback(props.activeTask, props.lastCommandResult));
const taskTone = computed(() => {
  if (!taskFeedback.value) return "muted";
  return taskFeedback.value.tone === "success" ? "ready" : taskFeedback.value.tone;
});
const taskIcon = computed(() => taskFeedback.value?.icon ?? "radio_button_unchecked");
const taskLabel = computed(() => {
  if (!taskFeedback.value) return "无任务";
  if (taskFeedback.value.showProgress) {
    return `智能粗剪 ${taskFeedback.value.progress}%`;
  }
  return taskFeedback.value.title;
});
</script>

<style scoped>
.workspace-editing-status-bar {
  align-items: center;
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: flex;
  gap: 8px;
  min-height: 40px;
  min-width: 0;
  overflow: hidden;
  padding: 6px 8px;
}

.workspace-editing-status-bar__item {
  align-items: center;
  background: color-mix(in srgb, var(--surface-tertiary) 82%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-secondary);
  display: inline-flex;
  flex: 1 1 0;
  gap: 6px;
  min-width: 0;
  padding: 6px 8px;
}

.workspace-editing-status-bar__item[data-tone="ready"] {
  border-color: color-mix(in srgb, var(--color-success) 36%, var(--border-default));
}

.workspace-editing-status-bar__item[data-tone="warning"] {
  border-color: color-mix(in srgb, var(--color-warning) 42%, var(--border-default));
}

.workspace-editing-status-bar__item[data-tone="danger"] {
  border-color: color-mix(in srgb, var(--color-danger) 38%, var(--border-default));
}

.workspace-editing-status-bar__item[data-tone="brand"] {
  border-color: color-mix(in srgb, var(--accent-primary) 38%, var(--border-default));
}

.workspace-editing-status-bar__item .material-symbols-outlined {
  flex: 0 0 auto;
  font-size: 17px;
}

.workspace-editing-status-bar__item strong,
.workspace-editing-status-bar__item small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-editing-status-bar__item strong {
  color: var(--text-primary);
  font: var(--font-label-sm);
}

.workspace-editing-status-bar__item small {
  color: var(--text-tertiary);
  font: var(--font-caption);
}

@container editing-workspace (max-width: 1040px) {
  .workspace-editing-status-bar {
    overflow-x: auto;
  }

  .workspace-editing-status-bar__item {
    flex: 0 0 auto;
    min-width: 132px;
  }
}
</style>
