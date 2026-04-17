<template>
  <ProjectContextGuard>
    <section class="editing-workspace-runtime" data-workspace-page="editing">
      <WorkspaceToolbar
        :blocked-message="blockedMessage"
        :has-timeline="hasTimeline"
        :project-name="currentProjectName"
        :selection-label="selectionLabel"
        :status="status"
        :timeline-name="timelineName"
        @create-draft="handleCreateDraft"
        @save="handleSave"
      />

      <WorkspaceStateNotice
        :blocked-message="blockedMessage"
        :error-message="error?.message ?? null"
        :status="status"
        @create-draft="handleCreateDraft"
        @retry="handleRetry"
      />

      <div class="editing-workspace-runtime__stage">
        <WorkspaceAssetRail :selected-clip="selectedClip" :timeline="timeline" />
        <WorkspacePreviewStage
          :blocked-message="blockedMessage"
          :selected-clip="selectedClip"
          :selected-track="selectedTrack"
          :timeline="timeline"
        />
        <WorkspaceInspector
          :blocked-message="blockedMessage"
          :error-message="error?.message ?? null"
          :selected-clip="selectedClip"
          :selected-track="selectedTrack"
          :status="status"
          :timeline="timeline"
        />
      </div>

      <WorkspaceTimeline
        :selected-clip-id="selectedClipId"
        :selected-track-id="selectedTrackId"
        :status="status"
        :timeline="timeline"
        :tracks="orderedTracks"
        @select-clip="handleSelectClip"
        @select-track="handleSelectTrack"
      />

      <WorkspaceAIActions
        :blocked-message="blockedMessage"
        :has-timeline="hasTimeline"
        :selected-clip="selectedClip"
        :status="status"
        @magic-cut="handleMagicCut"
      />
    </section>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, watch } from "vue";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import WorkspaceAIActions from "@/modules/workspace/WorkspaceAIActions.vue";
import WorkspaceAssetRail from "@/modules/workspace/WorkspaceAssetRail.vue";
import WorkspaceInspector from "@/modules/workspace/WorkspaceInspector.vue";
import WorkspacePreviewStage from "@/modules/workspace/WorkspacePreviewStage.vue";
import WorkspaceStateNotice from "@/modules/workspace/WorkspaceStateNotice.vue";
import WorkspaceTimeline from "@/modules/workspace/WorkspaceTimeline.vue";
import WorkspaceToolbar from "@/modules/workspace/WorkspaceToolbar.vue";
import { useEditingWorkspaceStore } from "@/stores/editing-workspace";
import { useProjectStore } from "@/stores/project";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";

const projectStore = useProjectStore();
const shellUiStore = useShellUiStore();
const workspaceStore = useEditingWorkspaceStore();

const {
  blockedMessage,
  error,
  hasTimeline,
  orderedTracks,
  selectedClip,
  selectedClipId,
  selectedTrack,
  selectedTrackId,
  status,
  timeline
} = storeToRefs(workspaceStore);

const currentProjectId = computed(() => projectStore.currentProject?.projectId ?? "");
const currentProjectName = computed(() => projectStore.currentProject?.projectName ?? "未选择项目");
const timelineName = computed(() => timeline.value?.name ?? "未创建时间线");
const selectionLabel = computed(() => {
  if (selectedClip.value) return `片段：${selectedClip.value.label}`;
  if (selectedTrack.value) return `轨道：${selectedTrack.value.name}`;
  if (hasTimeline.value) return "尚未选择轨道或片段";
  return "等待草稿";
});

watch(
  currentProjectId,
  (projectId) => {
    if (projectId) {
      void workspaceStore.load(projectId);
    }
  },
  { immediate: true }
);

watch(
  [currentProjectName, timeline, selectedTrack, selectedClip, status, blockedMessage, error],
  () => {
    shellUiStore.setDetailContext(
      createRouteDetailContext("asset", {
        icon: "movie_edit",
        eyebrow: "AI 剪辑工作台",
        title: currentProjectName.value,
        description: hasTimeline.value
          ? "当前详情面板与时间线选择态联动。"
          : "时间线尚未创建，详情面板保留空态语义。",
        badge: {
          label: status.value,
          tone: status.value === "error" ? "danger" : status.value === "blocked" ? "warning" : "brand"
        },
        metrics: [
          { id: "timeline", label: "时间线", value: timelineName.value },
          { id: "tracks", label: "轨道数", value: String(timeline.value?.tracks.length ?? 0) },
          { id: "selection", label: "当前选择", value: selectionLabel.value }
        ],
        sections: [
          {
            id: "selection",
            title: "当前选择",
            fields: [
              { id: "track", label: "轨道", value: selectedTrack.value?.name ?? "未选择" },
              { id: "clip", label: "片段", value: selectedClip.value?.label ?? "未选择" },
              { id: "status", label: "片段状态", value: selectedClip.value?.status ?? "未选择" }
            ]
          },
          {
            id: "gates",
            title: "运行边界",
            fields: [
              {
                id: "blocked",
                label: "AI 命令",
                value: blockedMessage.value ?? "未触发 blocked",
                multiline: true
              },
              {
                id: "error",
                label: "错误",
                value: error.value?.message ?? "无",
                multiline: true
              }
            ]
          }
        ]
      })
    );

    shellUiStore.openDetailPanel();
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("asset");
});

async function handleCreateDraft(): Promise<void> {
  await workspaceStore.createDraft(currentProjectId.value, "主时间线");
}

async function handleSave(): Promise<void> {
  await workspaceStore.saveTimeline();
}

async function handleMagicCut(): Promise<void> {
  await workspaceStore.runMagicCut(currentProjectId.value);
}

async function handleRetry(): Promise<void> {
  if (currentProjectId.value) {
    await workspaceStore.load(currentProjectId.value);
  }
}

function handleSelectTrack(trackId: string): void {
  workspaceStore.selectTrack(trackId);
  shellUiStore.openDetailPanel();
}

function handleSelectClip(payload: { clipId: string; trackId: string }): void {
  workspaceStore.selectTrack(payload.trackId);
  workspaceStore.selectClip(payload.clipId);
  shellUiStore.openDetailPanel();
}
</script>

<style scoped>
.editing-workspace-runtime {
  display: grid;
  gap: 18px;
}

.editing-workspace-runtime__stage {
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(240px, 280px) minmax(0, 1fr) minmax(240px, 280px);
}

@media (max-width: 1280px) {
  .editing-workspace-runtime__stage {
    grid-template-columns: minmax(220px, 260px) minmax(0, 1fr);
  }

  .editing-workspace-runtime__stage > :last-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 960px) {
  .editing-workspace-runtime__stage {
    grid-template-columns: 1fr;
  }
}
</style>
