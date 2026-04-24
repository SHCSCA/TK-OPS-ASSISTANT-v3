<template>
  <ProjectContextGuard>
    <div class="page-container h-full">
      <header class="page-header">
        <div class="page-header__crumb">首页 / 创作中枢</div>
        <div class="page-header__row">
          <div class="page-header__copy">
            <h1 class="page-header__title">M05 AI 剪辑工作台</h1>
            <p class="page-header__subtitle">
              基于真实素材与时间线草稿，完成 AI 粗剪、预览校验与人工微调。
            </p>
          </div>
          <div class="page-header__actions">
            <Button
              variant="secondary"
              :disabled="!currentProjectId || status === 'loading'"
              @click="handleRetry"
            >
              <template #leading><span class="material-symbols-outlined">refresh</span></template>
              刷新工作台
            </Button>
            <Button
              variant="primary"
              :running="status === 'saving'"
              :disabled="saveDisabled"
              @click="handleSave"
            >
              <template #leading><span class="material-symbols-outlined">save</span></template>
              保存时间线
            </Button>
            <Button
              variant="ai"
              data-testid="workspace-magic-cut-button"
              :running="isGenerating"
              :disabled="generateDisabled"
              @click="handleMagicCut"
            >
              <template #leading><span class="material-symbols-outlined">auto_awesome</span></template>
              一键 AI 粗剪
            </Button>
          </div>
        </div>

        <div class="workspace-context-bar">
          <Chip variant="default" size="sm">当前项目：{{ currentProjectName }}</Chip>
          <Chip variant="default" size="sm">时间线：{{ timelineName }}</Chip>
          <Chip variant="default" size="sm">当前选择：{{ selectionLabel }}</Chip>
        </div>
      </header>

      <div v-if="currentProjectId" class="workspace-semantic-labels">
        <span>核心创作中枢</span>
        <span>片段来源</span>
        <span>预览区</span>
        <span>AI 工具栏</span>
        <span>检查器</span>
        <span>运行能力待接入</span>
      </div>

      <div v-if="!currentProjectId" class="dashboard-alert" data-tone="warning">
        <span class="material-symbols-outlined">warning</span>
        <span>未选择项目，请先在创作总览中选中一个真实项目。</span>
      </div>
      <div v-else-if="error?.message" class="dashboard-alert" data-tone="danger">
        <span class="material-symbols-outlined">error</span>
        <span>工作台请求失败：{{ error.message }}</span>
      </div>
      <div v-else-if="activeTask" class="dashboard-alert" data-tone="brand">
        <span class="material-symbols-outlined spinning">sync</span>
        <span>{{ activeTask.message }}（{{ activeTask.progress }}%）</span>
      </div>
      <div v-else-if="blockedMessage" class="dashboard-alert" data-tone="warning">
        <span class="material-symbols-outlined">warning</span>
        <span>{{ blockedMessage }}</span>
      </div>

      <div v-if="status === 'loading' && !timeline" class="empty-state">
        <span class="material-symbols-outlined spinning">progress_activity</span>
        <strong>正在加载剪辑工作台</strong>
        <p>正在同步当前项目的时间线与可用状态。</p>
      </div>

      <div v-else-if="!timeline && currentProjectId" class="empty-state">
        <span class="material-symbols-outlined">movie_edit</span>
        <strong>时间线尚未创建</strong>
        <p>{{ blockedMessage || "当前项目还没有时间线草稿。" }}</p>
        <Button
          variant="primary"
          data-testid="workspace-create-draft-button"
          :disabled="status === 'saving'"
          @click="handleCreateDraft"
        >
          创建主时间线
        </Button>
      </div>

      <transition name="workspace-pop" appear>
        <div v-if="timeline" class="workspace-grid scroll-area">
          <div class="workspace-stage">
            <div class="stage-panel-wrapper">
              <p class="panel-label">片段来源</p>
              <WorkspaceAssetRail
                class="stage-panel"
                :selected-clip="selectedClip"
                :timeline="timeline"
              />
            </div>

            <div class="stage-panel-wrapper preview-panel-wrapper">
              <p class="panel-label">预览区</p>
              <WorkspacePreviewStage
                class="stage-panel preview-panel"
                :blocked-message="blockedMessage"
                :selected-clip="selectedClip"
                :selected-track="selectedTrack"
                :timeline="timeline"
              />
            </div>

            <div class="stage-panel-wrapper">
              <p class="panel-label">检查器</p>
              <WorkspaceInspector
                class="stage-panel"
                :blocked-message="inspectorBlockedMessage"
                :error-message="error?.message ?? null"
                :selected-clip="selectedClip"
                :selected-track="selectedTrack"
                :status="status"
                :timeline="timeline"
              />
            </div>
          </div>

          <div class="workspace-timeline-area-wrapper">
            <p class="panel-label">核心创作中枢</p>
            <div class="workspace-timeline-area">
              <WorkspaceTimeline
                :selected-clip-id="selectedClipId"
                :selected-track-id="selectedTrackId"
                :status="status"
                :timeline="timeline"
                :tracks="orderedTracks"
                @select-clip="handleSelectClip"
                @select-track="handleSelectTrack"
              />
            </div>
          </div>
        </div>
      </transition>
    </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, onMounted, watch } from "vue";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import Button from "@/components/ui/Button/Button.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import WorkspaceAssetRail from "@/modules/workspace/WorkspaceAssetRail.vue";
import WorkspaceInspector from "@/modules/workspace/WorkspaceInspector.vue";
import WorkspacePreviewStage from "@/modules/workspace/WorkspacePreviewStage.vue";
import WorkspaceTimeline from "@/modules/workspace/WorkspaceTimeline.vue";
import { useEditingWorkspaceStore } from "@/stores/editing-workspace";
import { useProjectStore } from "@/stores/project";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import { useTaskBusStore } from "@/stores/task-bus";

const projectStore = useProjectStore();
const shellUiStore = useShellUiStore();
const workspaceStore = useEditingWorkspaceStore();
const taskBusStore = useTaskBusStore();

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
const workspaceTaskTypes = new Set(["ai-workspace-command", "magic_cut", "ai-magic-cut"]);

const selectionLabel = computed(() => {
  if (selectedClip.value) return `片段：${selectedClip.value.label}`;
  if (selectedTrack.value) return `轨道：${selectedTrack.value.name}`;
  if (hasTimeline.value) return "尚未选择轨道或片段";
  return "等待创建时间线";
});

const activeTask = computed(() => {
  if (!currentProjectId.value) {
    return null;
  }

  for (const task of taskBusStore.tasks.values()) {
    if (
      task.project_id === currentProjectId.value &&
      workspaceTaskTypes.has(task.task_type) &&
      (task.status === "queued" || task.status === "running")
    ) {
      return task;
    }
  }

  return null;
});

const isGenerating = computed(() => {
  return Boolean(activeTask.value) || status.value === "saving";
});

const saveDisabled = computed(() => !timeline.value || status.value === "loading" || isGenerating.value);
const generateDisabled = computed(
  () => !timeline.value || status.value === "loading" || isGenerating.value
);

const inspectorBlockedMessage = computed(() => {
  return blockedMessage.value ?? (timeline.value ? "运行能力待接入" : null);
});

onMounted(() => {
  if (typeof WebSocket !== "undefined") {
    taskBusStore.connect();
  }
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
  [currentProjectName, timeline, selectedTrack, selectedClip, status, blockedMessage, error, activeTask],
  () => {
    shellUiStore.setDetailContext(
      createRouteDetailContext("asset", {
        icon: "movie_edit",
        eyebrow: "AI 剪辑工作台",
        title: currentProjectName.value,
        description: hasTimeline.value ? "时间线与检查器保持联动。" : "等待创建主时间线。",
        badge: {
          label: activeTask.value ? "处理中" : status.value === "ready" ? "已就绪" : status.value,
          tone: error.value
            ? "danger"
            : blockedMessage.value
              ? "warning"
              : activeTask.value
                ? "brand"
                : "neutral"
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
            id: "runtime",
            title: "运行监控",
            emptyLabel: "当前没有活跃任务或阻断。",
            fields: [
              {
                id: "blocked",
                label: "阻断提示",
                value: blockedMessage.value ?? "无",
                multiline: true
              },
              {
                id: "error",
                label: "错误",
                value: error.value?.message ?? "无",
                multiline: true
              },
              {
                id: "task",
                label: "活跃任务",
                value: activeTask.value
                  ? `${activeTask.value.message}（${activeTask.value.progress}%）`
                  : "无"
              }
            ]
          }
        ]
      })
    );

    if (error.value || blockedMessage.value) {
      shellUiStore.openDetailPanel();
    }
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("asset");
});

async function handleCreateDraft(): Promise<void> {
  if (currentProjectId.value) {
    await workspaceStore.createDraft(currentProjectId.value, "主时间线");
  }
}

async function handleSave(): Promise<void> {
  await workspaceStore.saveTimeline();
}

async function handleMagicCut(): Promise<void> {
  if (currentProjectId.value) {
    await workspaceStore.runMagicCut(currentProjectId.value);
  }
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

<style scoped src="./AIEditingWorkspacePage.css"></style>
