<template>
  <ProjectContextGuard>
    <section class="workspace-page editing-workspace-runtime" data-workspace-page="editing">
      <WorkspaceToolbar
        :blocked-message="blockedMessage"
        :has-timeline="hasTimeline"
        :project-name="currentProjectName"
        :status="status"
        @create-draft="handleCreateDraft"
        @magic-cut="handleMagicCut"
        @save="handleSave"
      />

      <WorkspaceStateNotice
        :blocked-message="blockedMessage"
        :error-message="error?.message ?? null"
        :status="status"
        @create-draft="handleCreateDraft"
        @retry="handleRetry"
      />

      <div class="editing-workspace-runtime__body">
        <WorkspaceAssetRail />
        <WorkspacePreviewStage
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
        @select-clip="workspaceStore.selectClip"
        @select-track="workspaceStore.selectTrack"
      />
    </section>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, watch } from "vue";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import WorkspaceAssetRail from "@/modules/workspace/WorkspaceAssetRail.vue";
import WorkspaceInspector from "@/modules/workspace/WorkspaceInspector.vue";
import WorkspacePreviewStage from "@/modules/workspace/WorkspacePreviewStage.vue";
import WorkspaceStateNotice from "@/modules/workspace/WorkspaceStateNotice.vue";
import WorkspaceTimeline from "@/modules/workspace/WorkspaceTimeline.vue";
import WorkspaceToolbar from "@/modules/workspace/WorkspaceToolbar.vue";
import { useEditingWorkspaceStore } from "@/stores/editing-workspace";
import { useProjectStore } from "@/stores/project";

const projectStore = useProjectStore();
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

watch(
  currentProjectId,
  (projectId) => {
    if (projectId) {
      void workspaceStore.load(projectId);
    }
  },
  { immediate: true }
);

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
</script>
