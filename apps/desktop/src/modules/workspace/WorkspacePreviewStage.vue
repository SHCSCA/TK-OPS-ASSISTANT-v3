<template>
  <main class="workspace-preview-stage" aria-label="预览舞台">
    <div class="workspace-preview-stage__frame">
      <div class="workspace-preview-stage__screen">
        <span class="material-symbols-outlined">movie</span>
        <strong>{{ headline }}</strong>
        <p>{{ description }}</p>
      </div>
      <div class="workspace-preview-stage__meta">
        <span>{{ timeline?.name ?? "未创建草稿" }}</span>
        <span>{{ durationLabel }}</span>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type {
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";

const props = defineProps<{
  selectedClip: WorkspaceTimelineClipDto | null;
  selectedTrack: WorkspaceTimelineTrackDto | null;
  timeline: WorkspaceTimelineDto | null;
}>();

const headline = computed(() => {
  if (props.selectedClip) return props.selectedClip.label;
  if (props.selectedTrack) return props.selectedTrack.name;
  if (props.timeline) return "时间线草稿已准备";
  return "等待创建时间线草稿";
});

const description = computed(() => {
  if (props.selectedClip) return "当前选中片段会在真实媒体预览接入后显示画面。";
  if (props.selectedTrack) return "当前选中轨道会在右侧检查器展示上下文。";
  if (props.timeline) return "把真实素材落轨后，这里会显示项目预览。";
  return "先创建空草稿，不生成示例视频或假进度。";
});

const durationLabel = computed(() => {
  const seconds = props.timeline?.durationSeconds;
  if (seconds === null || seconds === undefined) return "时长待定";
  return `${seconds.toFixed(1)} 秒`;
});
</script>
