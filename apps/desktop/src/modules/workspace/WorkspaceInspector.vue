<template>
  <aside class="workspace-inspector" aria-label="时间线检查器">
    <div class="workspace-panel-heading">
      <span class="material-symbols-outlined">tune</span>
      <div>
        <strong>检查器</strong>
        <p>{{ timeline ? "查看当前轨道与片段上下文" : "等待时间线草稿" }}</p>
      </div>
    </div>

    <div v-if="errorMessage" class="workspace-inspector__message workspace-inspector__message--error">
      {{ errorMessage }}
    </div>
    <div v-else-if="blockedMessage" class="workspace-inspector__message">
      {{ blockedMessage }}
    </div>

    <dl class="workspace-inspector__facts">
      <div>
        <dt>工作台状态</dt>
        <dd>{{ statusLabel }}</dd>
      </div>
      <div>
        <dt>时间线</dt>
        <dd>{{ timeline?.name ?? "未创建" }}</dd>
      </div>
      <div>
        <dt>选中轨道</dt>
        <dd>{{ selectedTrack?.name ?? "未选择" }}</dd>
      </div>
      <div>
        <dt>选中片段</dt>
        <dd>{{ selectedClip?.label ?? "未选择" }}</dd>
      </div>
    </dl>
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
    idle: "待加载",
    loading: "加载中",
    empty: "空态",
    ready: "就绪",
    saving: "保存中",
    blocked: "能力阻断",
    error: "请求失败"
  };
  return map[props.status];
});
</script>
