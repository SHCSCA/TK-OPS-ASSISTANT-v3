<template>
  <section
    class="workspace-inspector-clip-actions"
    data-testid="workspace-inspector-clip-actions"
  >
    <small>当前片段操作</small>
    <strong>{{ title }}</strong>
    <p>{{ description }}</p>

    <div class="workspace-inspector-clip-actions__buttons">
      <button
        data-testid="workspace-inspector-seek-clip-start"
        type="button"
        :disabled="!selectedClip"
        @click="$emit('seek-clip-start')"
      >
        <span class="material-symbols-outlined" aria-hidden="true">flag</span>
        定位到片段起点
      </button>
    </div>

    <dl class="workspace-inspector-clip-actions__checks">
      <div :data-state="saveStateTone">
        <dt>保存</dt>
        <dd>{{ saveStateLabel }}</dd>
      </div>
      <div :data-state="precheckTone">
        <dt>预检</dt>
        <dd>{{ precheckLabel }}</dd>
      </div>
      <div :data-state="previewTone">
        <dt>预览</dt>
        <dd>{{ previewLabel }}</dd>
      </div>
    </dl>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type {
  TimelinePrecheckDto,
  WorkspaceSaveStateDto,
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto
} from "@/types/runtime";
import type { WorkspacePreviewContext } from "./workspacePreviewContext";
import { cleanWorkspaceText, formatWorkspaceTime } from "./workspaceTimelineViewModel";

defineEmits<{
  "seek-clip-start": [];
}>();

const props = defineProps<{
  precheck: TimelinePrecheckDto | null;
  previewContext: WorkspacePreviewContext;
  saveState: WorkspaceSaveStateDto | null;
  selectedClip: WorkspaceTimelineClipDto | null;
  timeline: WorkspaceTimelineDto | null;
}>();

const title = computed(() => {
  if (!props.timeline) return "等待时间线草稿";
  if (!props.selectedClip) return "先选择片段";
  return "从片段起点检查";
});

const description = computed(() => {
  if (!props.timeline) return "创建或同步 AI 三轨后，才能定位具体片段。";
  if (!props.selectedClip) return "点击时间线、素材池分镜、配音或字幕片段后，这里会给出可执行动作。";

  const label = cleanWorkspaceText(props.selectedClip.label, "未命名片段");
  const startLabel = formatWorkspaceTime(props.selectedClip.startMs);
  const durationLabel = formatWorkspaceTime(props.selectedClip.durationMs);
  return `${label} · 起点 ${startLabel} · 时长 ${durationLabel}`;
});

const saveStateTone = computed(() => {
  if (!props.timeline) return "muted";
  return props.saveState?.saved ? "ready" : "warning";
});

const saveStateLabel = computed(() => {
  if (!props.timeline) return "未创建";
  if (!props.saveState) return "尚未保存";
  return props.saveState.saved ? "已保存" : "需保存";
});

const precheckTone = computed(() => {
  if (!props.precheck) return "muted";
  return props.precheck.status === "ready" ? "ready" : "warning";
});

const precheckLabel = computed(() => {
  if (!props.precheck) return "未预检";
  return props.precheck.status === "ready" ? "通过" : "需处理";
});

const previewTone = computed(() => {
  if (props.previewContext.runtimePreviewErrorMessage) return "warning";
  if (props.previewContext.previewMode === "media") return "ready";
  return "muted";
});

const previewLabel = computed(() => {
  if (props.previewContext.runtimePreviewErrorMessage) return "需同步";
  if (props.previewContext.previewMode === "media") return "可播放";
  return "结构预览";
});
</script>

<style scoped>
.workspace-inspector-clip-actions {
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--accent-primary) 9%, var(--surface-tertiary)),
    var(--surface-tertiary)
  );
  border: 1px solid color-mix(in srgb, var(--accent-primary) 24%, var(--border-default));
  border-radius: 8px;
  display: grid;
  gap: 10px;
  padding: 14px;
}

.workspace-inspector-clip-actions small {
  color: var(--text-tertiary);
}

.workspace-inspector-clip-actions p {
  color: var(--text-secondary);
  margin: 0;
}

.workspace-inspector-clip-actions__buttons {
  display: grid;
  gap: 8px;
}

.workspace-inspector-clip-actions__buttons button {
  align-items: center;
  background: var(--surface-primary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-primary);
  cursor: pointer;
  display: inline-flex;
  gap: 8px;
  justify-content: center;
  line-height: 1.4;
  min-height: 36px;
  padding: 8px 10px;
}

.workspace-inspector-clip-actions__buttons button:disabled {
  cursor: not-allowed;
  opacity: 0.54;
}

.workspace-inspector-clip-actions__buttons button:not(:disabled):hover {
  border-color: color-mix(in srgb, var(--accent-primary) 42%, var(--border-default));
}

.workspace-inspector-clip-actions__checks {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 0;
}

.workspace-inspector-clip-actions__checks div {
  background: color-mix(in srgb, var(--surface-secondary) 78%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: grid;
  gap: 3px;
  min-width: 0;
  padding: 8px;
}

.workspace-inspector-clip-actions__checks div[data-state="ready"] {
  border-color: color-mix(in srgb, var(--color-success) 38%, var(--border-default));
}

.workspace-inspector-clip-actions__checks div[data-state="warning"] {
  border-color: color-mix(in srgb, var(--color-warning) 42%, var(--border-default));
}

.workspace-inspector-clip-actions__checks dt {
  color: var(--text-tertiary);
  font-size: 12px;
}

.workspace-inspector-clip-actions__checks dd {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
