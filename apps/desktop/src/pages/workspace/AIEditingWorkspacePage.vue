<template>
  <ProjectContextGuard>
    <div class="editing-workspace-page h-full">
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
              variant="ai"
              data-testid="workspace-assemble-button"
              :running="status === 'saving' && !timeline"
              :disabled="assembleDisabled"
              @click="handleAssemble"
            >
              <template #leading><span class="material-symbols-outlined">hub</span></template>
              汇入创作链路
            </Button>
            <Button
              variant="secondary"
              data-testid="workspace-precheck-button"
              :disabled="precheckDisabled"
              @click="handlePrecheck"
            >
              <template #leading><span class="material-symbols-outlined">rule_settings</span></template>
              本地预检
            </Button>
            <Button
              variant="primary"
              data-testid="workspace-save-button"
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
              智能粗剪
            </Button>
          </div>
        </div>

        <div class="workspace-context-bar">
          <Chip variant="default" size="sm">当前项目：{{ currentProjectName }}</Chip>
          <Chip variant="default" size="sm">时间线：{{ timelineName }}</Chip>
          <Chip variant="default" size="sm">当前选择：{{ selectionLabel }}</Chip>
          <Chip variant="default" size="sm">汇入：{{ assemblyLabel }}</Chip>
          <Chip variant="default" size="sm">预检：{{ precheckLabel }}</Chip>
        </div>
      </header>

      <div v-if="currentProjectId" class="workspace-semantic-labels">
        <span>素材池</span>
        <span>播放器</span>
        <span>基础属性</span>
        <span>基础工具</span>
        <span>时间线</span>
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
      <div v-else-if="precheck?.message" class="dashboard-alert" data-tone="brand">
        <span class="material-symbols-outlined">rule_settings</span>
        <span>{{ precheck.message }}</span>
      </div>

      <div v-if="status === 'loading' && !timeline" class="empty-state">
        <span class="material-symbols-outlined spinning">progress_activity</span>
        <strong>正在加载剪辑工作台</strong>
        <p>正在同步当前项目的时间线与可用状态。</p>
      </div>

      <div v-if="!timeline && currentProjectId && status !== 'loading'" class="empty-state empty-state--inline">
        <span class="material-symbols-outlined">movie_edit</span>
        <strong>时间线尚未创建</strong>
        <p>{{ blockedMessage || "当前项目还没有时间线草稿。" }}</p>
        <div class="empty-state__actions">
          <Button
            variant="primary"
            data-testid="workspace-create-draft-button"
            :disabled="status === 'saving'"
            @click="handleCreateDraft"
          >
            创建主时间线
          </Button>
          <Button
            variant="ai"
            :running="status === 'saving'"
            :disabled="assembleDisabled"
            @click="handleAssemble"
          >
            汇入创作链路
          </Button>
        </div>
      </div>

      <transition name="workspace-pop" appear>
        <div v-if="currentProjectId && status !== 'loading'" class="workspace-editor scroll-area">
          <div class="workspace-stage">
            <div class="stage-panel-wrapper stage-panel-wrapper--asset">
              <p class="panel-label">素材池</p>
              <WorkspaceAssetRail
                class="stage-panel"
                :assembly-state="assemblyState"
                :asset-error="assetError"
                :asset-status="assetStatus"
                :assets="assets"
                :project-id="currentProjectId"
                :selected-clip="selectedClip"
                :timeline="timeline"
                @asset-insert="handleAssetInsert"
                @asset-replace="handleAssetReplace"
                @select-source-clip="handleSelectClip"
                @sync-assets="handleSyncAssets"
              />
            </div>

            <div class="stage-panel-wrapper preview-panel-wrapper">
              <p class="panel-label">播放器</p>
              <WorkspacePreviewStage
                class="stage-panel preview-panel"
                :preview-context="previewContext"
                :timeline="timeline"
              />
            </div>

            <div class="stage-panel-wrapper stage-panel-wrapper--inspector">
              <p class="panel-label">基础属性</p>
              <WorkspaceInspector
                class="stage-panel"
                :assembly-state="assemblyState"
                :blocked-message="inspectorBlockedMessage"
                :error-message="error?.message ?? null"
                :last-command-result="lastCommandResult"
                :precheck="precheck"
                :preview-context="previewContext"
                :save-state="saveState"
                :selected-clip="selectedClip"
                :selected-track="selectedTrack"
                :status="status"
                :timeline="timeline"
                @focus-precheck-issue="handleFocusPrecheckIssue"
              />
            </div>
          </div>

          <div class="workspace-timeline-area-wrapper">
            <p class="panel-label">时间线</p>
            <div class="workspace-timeline-area">
              <WorkspaceTimelineToolbar
                :can-delete="canDeleteSelectedClip"
                :can-move="canMoveSelectedClip"
                :can-split="canSplitSelectedClip"
                :can-trim="canTrimSelectedClip"
                :disabled="status === 'loading' || isGenerating"
                :status-label="toolBarStatus"
                @delete="handleDeleteSelectedClip"
                @move="handleMoveSelectedClip"
                @split="handleSplitSelectedClip"
                @trim="handleTrimSelectedClip"
              />
              <WorkspaceTimeline
                :playhead-ms="playheadMs"
                :selected-clip-id="selectedClipId"
                :selected-track-id="selectedTrackId"
                :status="status"
                :timeline="timeline"
                :tracks="orderedTracks"
                @drag-cancel="handleTimelineDragCancel"
                @playhead="handleSetPlayhead"
                @move-commit="handleTimelineMoveCommit"
                @move-preview="handleTimelineMovePreview"
                @select-clip="handleSelectClip"
                @select-track="handleSelectTrack"
                @trim="handleTimelineTrim"
                @trim-commit="handleTimelineTrimCommit"
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import Button from "@/components/ui/Button/Button.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import WorkspaceAssetRail from "@/modules/workspace/WorkspaceAssetRail.vue";
import WorkspaceInspector from "@/modules/workspace/WorkspaceInspector.vue";
import WorkspacePreviewStage from "@/modules/workspace/WorkspacePreviewStage.vue";
import WorkspaceTimeline from "@/modules/workspace/WorkspaceTimeline.vue";
import WorkspaceTimelineToolbar from "@/modules/workspace/WorkspaceTimelineToolbar.vue";
import type {
  WorkspaceTimelineDragPreview,
  WorkspaceTimelineMovePreview,
  WorkspaceTimelineTrimPreview
} from "@/modules/workspace/useWorkspaceTimelineDrag";
import { cleanWorkspaceText, workspaceStatusLabel } from "@/modules/workspace/workspaceTimelineViewModel";
import { useEditingWorkspaceStore } from "@/stores/editing-workspace";
import { useProjectStore } from "@/stores/project";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import { useTaskBusStore } from "@/stores/task-bus";

const projectStore = useProjectStore();
const shellUiStore = useShellUiStore();
const workspaceStore = useEditingWorkspaceStore();
const taskBusStore = useTaskBusStore();
const movePreview = ref<WorkspaceTimelineMovePreview | null>(null);

const {
  assemblyState,
  assetError,
  assetStatus,
  assets,
  blockedMessage,
  error,
  hasTimeline,
  lastCommandResult,
  orderedTracks,
  playheadMs,
  precheck,
  previewContext,
  saveState,
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
const assemblyLabel = computed(() => {
  if (!assemblyState.value) return "未汇入";
  return assemblyState.value.status === "ready" ? "已接入" : "需处理";
});
const precheckLabel = computed(() => {
  if (!precheck.value) return "未检查";
  return precheck.value.status === "ready" ? "通过" : "有问题";
});

const selectionLabel = computed(() => {
  if (selectedClip.value) return `片段：${cleanWorkspaceText(selectedClip.value.label, "未命名片段")}`;
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
const assembleDisabled = computed(() => !currentProjectId.value || status.value === "loading" || isGenerating.value);
const precheckDisabled = computed(() => !timeline.value || status.value === "loading" || isGenerating.value);
const generateDisabled = computed(
  () => !timeline.value || status.value === "loading" || isGenerating.value
);
const toolBarStatus = computed(() => {
  if (!timeline.value) return "等待时间线";
  return "选择工具 · 磁吸开启";
});
const canDeleteSelectedClip = computed(() => Boolean(selectedClip.value));
const canMoveSelectedClip = computed(() => Boolean(selectedClip.value));
const canSplitSelectedClip = computed(() => {
  return Boolean(selectedClip.value && selectedClip.value.durationMs >= 2);
});
const canTrimSelectedClip = computed(() => Boolean(selectedClip.value));

const inspectorBlockedMessage = computed(() => {
  return blockedMessage.value;
});

onMounted(() => {
  shellUiStore.closeDetailPanel();

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
          label: activeTask.value ? "处理中" : workspaceStatusLabel(status.value),
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
          { id: "selection", label: "当前选择", value: selectionLabel.value },
          { id: "assembly", label: "汇入", value: assemblyLabel.value },
          { id: "precheck", label: "预检", value: precheckLabel.value }
        ],
        sections: [
          {
            id: "selection",
            title: "当前选择",
            fields: [
              { id: "track", label: "轨道", value: selectedTrack.value?.name ?? "未选择" },
              {
                id: "clip",
                label: "片段",
                value: selectedClip.value ? cleanWorkspaceText(selectedClip.value.label, "未命名片段") : "未选择"
              },
              { id: "status", label: "片段状态", value: workspaceStatusLabel(selectedClip.value?.status) }
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
              },
              {
                id: "precheck",
                label: "本地预检",
                value: precheck.value?.message ?? "未执行",
                multiline: true
              }
            ]
          }
        ]
      })
    );

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

async function handleAssemble(): Promise<void> {
  if (currentProjectId.value) {
    await workspaceStore.assembleTimeline(currentProjectId.value);
  }
}

async function handlePrecheck(): Promise<void> {
  await workspaceStore.runPrecheck();
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

async function handleSyncAssets(): Promise<void> {
  if (currentProjectId.value) {
    await workspaceStore.loadAssets(currentProjectId.value);
  }
}

async function handleAssetInsert(assetId: string): Promise<void> {
  const result = await workspaceStore.insertAssetAtPlayhead(assetId);
  if (result) {
    await workspaceStore.runPrecheck();
  }
}

async function handleAssetReplace(assetId: string): Promise<void> {
  const result = await workspaceStore.replaceSelectedClipWithAsset(assetId);
  if (result) {
    await workspaceStore.runPrecheck();
  }
}

async function handleDeleteSelectedClip(): Promise<void> {
  await workspaceStore.deleteSelectedClip();
}

async function handleSplitSelectedClip(): Promise<void> {
  await workspaceStore.splitSelectedClip();
}

async function handleMoveSelectedClip(deltaMs: number): Promise<void> {
  await workspaceStore.moveSelectedClipBy(deltaMs);
}

async function handleTrimSelectedClip(edge: "left" | "right", deltaMs: number): Promise<void> {
  await workspaceStore.trimSelectedClip(edge, deltaMs);
}

function handleSetPlayhead(positionMs: number): void {
  workspaceStore.setPlayheadMs(positionMs);
}

function handleFocusPrecheckIssue(issue: string): void {
  workspaceStore.focusPrecheckIssue(issue);
}

async function handleTimelineTrim(payload: { clipId: string; edge: "left" | "right"; deltaMs: number }): Promise<void> {
  workspaceStore.selectClip(payload.clipId);
  await workspaceStore.trimSelectedClip(payload.edge, payload.deltaMs);
}

function handleTimelineMovePreview(payload: WorkspaceTimelineMovePreview): void {
  movePreview.value = payload;
}

async function handleTimelineMoveCommit(payload: WorkspaceTimelineMovePreview): Promise<void> {
  movePreview.value = null;
  const result = await workspaceStore.commitMovePreview(payload);
  if (result) {
    await workspaceStore.runPrecheck();
  }
}

async function handleTimelineTrimCommit(payload: WorkspaceTimelineTrimPreview): Promise<void> {
  const result = await workspaceStore.commitTrimPreview(payload);
  if (result) {
    await workspaceStore.runPrecheck();
  }
}

function handleTimelineDragCancel(payload: WorkspaceTimelineDragPreview): void {
  if (payload.gesture === "move") {
    movePreview.value = null;
  }
}

function handleSelectTrack(trackId: string): void {
  workspaceStore.selectTrack(trackId);
}

function handleSelectClip(payload: { clipId: string; trackId: string }): void {
  workspaceStore.selectTrack(payload.trackId);
  workspaceStore.selectClip(payload.clipId);
}
</script>

<style scoped src="./AIEditingWorkspacePage.css"></style>
