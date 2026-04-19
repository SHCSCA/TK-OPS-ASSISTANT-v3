<template>
  <aside class="workspace-inspector" aria-label="时间线检查器">
    <div class="workspace-inspector__heading">
      <span class="material-symbols-outlined">tune</span>
      <div>
        <strong>检查器</strong>
        <p>{{ headingDescription }}</p>
      </div>
    </div>

    <div v-if="errorMessage" class="workspace-inspector__message workspace-inspector__message--error">
      {{ errorMessage }}
    </div>
    <div v-else-if="blockedMessage" class="workspace-inspector__message workspace-inspector__message--warning">
      {{ blockedMessage }}
    </div>

    <section class="workspace-inspector__card">
      <small>工作台状态</small>
      <strong>{{ statusLabel }}</strong>
      <p>{{ statusDescription }}</p>
    </section>

    <section class="workspace-inspector__facts scroll-area">
      <div class="fact-item">
        <dt>时间线</dt>
        <dd>{{ timeline?.name ?? "未创建" }}</dd>
      </div>
      <div class="fact-item">
        <dt>轨道数</dt>
        <dd>{{ timeline?.tracks.length ?? 0 }}</dd>
      </div>
      <div class="fact-item">
        <dt>选中轨道</dt>
        <dd>{{ selectedTrack?.name ?? "未选择" }}</dd>
      </div>
      <div class="fact-item">
        <dt>选中片段</dt>
        <dd>{{ selectedClip?.label ?? "未选择" }}</dd>
      </div>
    </section>

    <section class="workspace-inspector__card">
      <small>动作边界</small>
      <strong>{{ actionBoundaryTitle }}</strong>
      <p>{{ actionBoundaryDescription }}</p>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { EditingWorkspaceStatus } from "@/stores/editing-workspace";
import type {
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";

const props = defineProps<{
  blockedMessage: string | null;
  errorMessage: string | null;
  selectedClip: WorkspaceTimelineClipDto | null;
  selectedTrack: WorkspaceTimelineTrackDto | null;
  status: EditingWorkspaceStatus;
  timeline: WorkspaceTimelineDto | null;
}>();

const statusLabel = computed(() => {
  const map: Record<EditingWorkspaceStatus, string> = {
    blocked: "能力阻断",
    empty: "空态",
    error: "请求失败",
    idle: "待加载",
    loading: "加载中",
    ready: "已就绪",
    saving: "保存中"
  };
  return map[props.status];
});

const headingDescription = computed(() => {
  if (props.timeline) return "围绕当前时间线、轨道和片段给出真实上下文。";
  return "等待时间线草稿进入工作台。";
});

const statusDescription = computed(() => {
  if (props.status === "blocked") return "AI 命令走真实 blocked 语义，不会生成假任务。";
  if (props.status === "error") return props.errorMessage ?? "请求失败，请稍后重试。";
  if (props.status === "empty") return "当前没有时间线草稿。";
  if (props.status === "saving") return "正在将当前时间线草稿写回 Runtime。";
  if (props.status === "loading") return "正在读取当前项目的时间线。";
  return "当前可继续在真实时间线草稿上选择、保存和查看上下文。";
});

const actionBoundaryTitle = computed(() => {
  if (!props.timeline) return "先创建时间线";
  if (!props.selectedClip) return "先选中片段";
  return "当前片段已联动";
});

const actionBoundaryDescription = computed(() => {
  if (!props.timeline) return "没有 timeline 时，工具栏与 AI 工具条只显示空态或 disabled。";
  if (!props.selectedClip) return "AI 命令可以发起，但不会伪造片段级生成结果。";
  return `片段状态：${props.selectedClip.status}，来源：${props.selectedClip.sourceType}。`;
});
</script>

<style scoped>
.workspace-inspector {
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 20px;
  box-shadow: var(--shadow-sm);
  display: grid;
  gap: 14px;
  padding: 18px;
}

.workspace-inspector__heading {
  align-items: center;
  display: flex;
  gap: 12px;
}

.workspace-inspector__heading p,
.workspace-inspector__message,
.workspace-inspector__card p {
  color: var(--text-secondary);
  margin: 0;
}

.workspace-inspector__message,
.workspace-inspector__card {
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 16px;
  display: grid;
  gap: 6px;
  padding: 14px;
}

.workspace-inspector__message--error {
  border-color: color-mix(in srgb, var(--color-danger) 35%, var(--border-default));
  color: var(--color-danger);
}

.workspace-inspector__message--warning {
  border-color: color-mix(in srgb, var(--color-warning) 35%, var(--border-default));
  color: var(--color-warning);
}

.workspace-inspector__card small {
  color: var(--text-tertiary);
}
.workspace-inspector__facts {
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 16px;
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 14px;
}

.scroll-area {
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-strong) transparent;
}

.scroll-area::-webkit-scrollbar {
  width: 4px;
}
.scroll-area::-webkit-scrollbar-thumb {
  background: var(--color-border-strong);
  border-radius: 99px;
}

.workspace-inspector__facts div {
  display: grid;
  gap: 4px;
}

.workspace-inspector__facts dt {
  color: var(--text-tertiary);
  font-size: 12px;
}

.workspace-inspector__facts dd {
  margin: 0;
}
</style>
