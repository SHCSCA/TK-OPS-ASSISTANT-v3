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
              同步 AI 三轨
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
        <span>预览与校验</span>
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
      <WorkspaceCommandFeedbackBar
        v-else-if="activeTask || (lastCommandResult && lastCommandResult.status !== 'blocked')"
        :active-task="activeTask"
        :cancel-pending="isCommandCancelPending"
        :last-command-result="lastCommandResult"
        :retry-disabled="generateDisabled"
        @cancel="handleCancelCommandTask"
        @retry="handleMagicCut"
      />
      <WorkspaceAICapabilityRecovery
        v-else-if="magicCutRecoveryMessage"
        :loading="aiCapabilityStore.status === 'loading'"
        :message="magicCutRecoveryMessage"
        @open-settings="handleOpenAISettings"
        @refresh="handleReloadAICapabilities"
      />
      <div v-else-if="blockedMessage" class="dashboard-alert" data-tone="warning">
        <span class="material-symbols-outlined">warning</span>
        <span>{{ blockedMessage }}</span>
      </div>
      <div v-else-if="precheck?.message" class="dashboard-alert" data-tone="brand">
        <span class="material-symbols-outlined">rule_settings</span>
        <span>{{ precheck.message }}</span>
      </div>
      <WorkspaceSyncRecovery
        v-if="managedTrackSyncRecovery.visible"
        :disabled="assembleDisabled"
        :message="managedTrackSyncRecovery.message"
        @sync="handleAssemble"
      />
      <WorkspaceSourceRecovery
        v-if="sourceRecovery.visible"
        :disabled="assembleDisabled"
        :heading="sourceRecovery.heading"
        :message="sourceRecovery.message"
        :next-step="sourceRecovery.nextStep"
        :show-tts-settings-action="sourceRecovery.showTtsSettingsAction"
        :show-voice-action="sourceRecovery.showVoiceAction"
        :sources="sourceRecovery.sources"
        :status-label="sourceRecovery.statusLabel"
        @open-tts-settings="handleOpenTtsSettings"
        @open-voice-studio="handleOpenVoiceStudio"
        @precheck="handlePrecheck"
        @sync="handleAssemble"
      />

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
            汇入并同步 AI 三轨
          </Button>
        </div>
      </div>

      <div v-if="currentProjectId && status !== 'loading'" class="workspace-editor">
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
            <p class="panel-label">预览与校验</p>
            <WorkspacePreviewStage
              class="stage-panel preview-panel"
              :preview-context="previewContext"
              :timeline="timeline"
              :is-playing="isPlaying"
              :play-progress="playProgress"
              @play="handlePlay"
              @pause="handlePause"
              @retry-preview="handleRetry"
            />
          </div>

          <div class="workspace-timeline-area-wrapper">
            <p class="panel-label">时间线</p>
            <div class="workspace-timeline-area">
              <WorkspaceTimelineToolbar
                :can-delete="canDeleteSelectedClip"
                :can-move="canMoveSelectedClip"
                :can-move-left="canMoveSelectedClipLeft"
                :can-move-right="canMoveSelectedClipRight"
                :can-split="canSplitSelectedClip"
                :can-trim="canTrimSelectedClip"
                :can-redo="canRedoTimelineEdit"
                :can-undo="canUndoTimelineEdit"
                :disabled="status === 'loading' || isGenerating"
                :status-label="toolBarStatus"
                :zoom-percent="zoomPercent"
                @delete="handleDeleteSelectedClip"
                @move="handleMoveSelectedClip"
                @split="handleSplitSelectedClip"
                @trim="handleTrimSelectedClip"
                @redo="handleRedoTimelineEdit"
                @undo="handleUndoTimelineEdit"
                @zoom-change="handleTimelineZoomChange"
              />
              <div
                v-if="timelineDragFeedback"
                class="workspace-timeline-drag-feedback"
                data-testid="workspace-timeline-drag-feedback"
                role="status"
                aria-live="polite"
              >
                <span class="material-symbols-outlined" aria-hidden="true">open_with</span>
                <strong>{{ timelineDragFeedback.title }}</strong>
                <span>{{ timelineDragFeedback.detail }}</span>
              </div>
              <WorkspaceTimeline
                :playhead-ms="playheadMs"
                :selected-clip-id="selectedClipId"
                :selected-track-id="selectedTrackId"
                :status="status"
                :timeline="timeline"
                :tracks="orderedTracks"
                :zoom-percent="zoomPercent"
                @drag-cancel="handleTimelineDragCancel"
                @playhead="handleSetPlayhead"
                @move-commit="handleTimelineMoveCommit"
                @move-preview="handleTimelineMovePreview"
                @select-clip="handleSelectClip"
                @select-track="handleSelectTrack"
                @trim="handleTimelineTrim"
                @trim-commit="handleTimelineTrimCommit"
                @trim-preview="handleTimelineTrimPreview"
              />
            </div>
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
              @request-export="handleOpenRenderExport"
              @seek-clip-start="selectedClip && handleSetPlayhead(selectedClip.startMs)"
            />
          </div>
        </div>
        <WorkspaceEditingStatusBar
          :active-task="activeTask"
          :is-playing="isPlaying"
          :last-command-result="lastCommandResult"
          :playhead-ms="playheadMs"
          :precheck="precheck"
          :preview-context="previewContext"
          :save-state="saveState"
          :selection-label="selectionLabel"
        />
      </div>
    </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { onBeforeRouteLeave, useRouter } from "vue-router";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import Button from "@/components/ui/Button/Button.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import { requestDesktopConfirm } from "@/composables/useDesktopConfirm";
import WorkspaceAICapabilityRecovery from "@/modules/workspace/WorkspaceAICapabilityRecovery.vue";
import WorkspaceAssetRail from "@/modules/workspace/WorkspaceAssetRail.vue";
import WorkspaceCommandFeedbackBar from "@/modules/workspace/WorkspaceCommandFeedbackBar.vue";
import WorkspaceEditingStatusBar from "@/modules/workspace/WorkspaceEditingStatusBar.vue";
import WorkspaceInspector from "@/modules/workspace/WorkspaceInspector.vue";
import WorkspacePreviewStage from "@/modules/workspace/WorkspacePreviewStage.vue";
import WorkspaceSourceRecovery from "@/modules/workspace/WorkspaceSourceRecovery.vue";
import WorkspaceSyncRecovery from "@/modules/workspace/WorkspaceSyncRecovery.vue";
import WorkspaceTimeline from "@/modules/workspace/WorkspaceTimeline.vue";
import WorkspaceTimelineToolbar from "@/modules/workspace/WorkspaceTimelineToolbar.vue";
import { useMagicCutReadiness } from "@/modules/workspace/useMagicCutReadiness";
import { useWorkspacePlayback } from "@/modules/workspace/useWorkspacePlayback";
import { buildWorkspaceExportRoute } from "@/modules/workspace/workspaceExportReadiness";
import type {
  WorkspaceTimelineDragPreview,
  WorkspaceTimelineMovePreview,
  WorkspaceTimelineTrimPreview
} from "@/modules/workspace/useWorkspaceTimelineDrag";
import { buildSourceRecoveryViewModel } from "@/modules/workspace/workspaceRecoveryViewModel";
import { evaluateTimelineClipActions } from "@/modules/workspace/workspaceTimelineActions";
import { normalizeTimelineZoomPercent } from "@/modules/workspace/workspaceTimelineGeometry";
import {
  cleanWorkspaceText,
  formatWorkspaceTime,
  summarizeManagedTrackSync,
  workspaceStatusLabel
} from "@/modules/workspace/workspaceTimelineViewModel";
import { useAICapabilityStore } from "@/stores/ai-capability";
import { isMagicCutRecoveryMessage, useEditingWorkspaceStore } from "@/stores/editing-workspace";
import { useProjectStore } from "@/stores/project";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import { useTaskBusStore } from "@/stores/task-bus";
import type { TaskInfo } from "@/types/task-events";
import type { TimelinePrecheckIssueDetailDto } from "@/types/runtime";

const projectStore = useProjectStore();
const router = useRouter();
const shellUiStore = useShellUiStore();
const workspaceStore = useEditingWorkspaceStore();
const taskBusStore = useTaskBusStore();
const aiCapabilityStore = useAICapabilityStore();

const {
  assemblyState,
  assetError,
  assetStatus,
  assets,
  blockedMessage,
  canRedoTimelineEdit,
  canUndoTimelineEdit,
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

const aiCapabilityRefs = storeToRefs(aiCapabilityStore);
const magicCutReadiness = useMagicCutReadiness({
  settings: aiCapabilityRefs.settings,
  supportMatrix: aiCapabilityRefs.supportMatrix,
  providerCatalog: aiCapabilityRefs.providerCatalog,
  status: aiCapabilityRefs.status
});

const currentProjectId = computed(() => projectStore.currentProject?.projectId ?? "");
const currentProjectName = computed(() => projectStore.currentProject?.projectName ?? "未选择项目");
const timelineName = computed(() => timeline.value?.name ?? "未创建时间线");
const workspaceTaskTypes = new Set(["ai-workspace-command", "magic_cut", "ai-magic-cut"]);
const zoomPercent = ref(100);
const {
  isPlaying,
  pause: handlePause,
  play: handlePlay,
  playProgress,
  seek: handleSetPlayhead
} = useWorkspacePlayback({
  hasTimeline,
  playheadMs,
  resolveDurationMs: () => workspaceStore.resolveTimelineDurationMs(),
  setPlayheadMs: (positionMs) => workspaceStore.setPlayheadMs(positionMs)
});
const assemblyLabel = computed(() => {
  if (!assemblyState.value) return "未汇入";
  return assemblyState.value.status === "ready" ? "已接入" : "需处理";
});
const precheckLabel = computed(() => {
  if (!precheck.value) return "未检查";
  return precheck.value.status === "ready" ? "通过" : "有问题";
});
const magicCutUnavailableMessage = computed(() => {
  if (!timeline.value || magicCutReadiness.value.available) return "";
  return magicCutReadiness.value.message;
});
const magicCutBlockedRecoveryMessage = computed(() => {
  const message = blockedMessage.value ?? "";
  return isMagicCutRecoveryMessage(message) ? message : "";
});
const magicCutRecoveryMessage = computed(() => {
  return magicCutBlockedRecoveryMessage.value || magicCutUnavailableMessage.value;
});
const managedTrackSyncRecovery = computed(() => {
  if (!timeline.value) {
    return {
      message: "",
      visible: false
    };
  }

  const declaredDurationMs = Math.max(0, (timeline.value.durationSeconds ?? 0) * 1000);
  const summary = summarizeManagedTrackSync(
    timeline.value.tracks,
    workspaceStore.resolveTimelineDurationMs(),
    declaredDurationMs
  );
  const targetLabel = formatWorkspaceTime(summary.targetDurationMs);
  return {
    message: `${summary.unsyncedCount} 条 AI 受管轨道未对齐到 ${targetLabel}，可重新同步脚本、分镜、配音和字幕生成的受管轨道。`,
    visible: summary.visible && summary.unsyncedCount > 0
  };
});
const sourceRecovery = computed(() => {
  return buildSourceRecoveryViewModel({
    assemblyState: assemblyState.value,
    hasTimeline: Boolean(timeline.value),
    trackCount: orderedTracks.value.length
  });
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
    if (isCurrentWorkspaceCommandTask(task) && (task.status === "queued" || task.status === "running")) {
      return task;
    }
  }

  return null;
});

const isGenerating = computed(() => {
  return Boolean(activeTask.value) || status.value === "saving";
});

const isCommandCancelPending = ref(false);
const timelineDragFeedback = ref<{ detail: string; title: string } | null>(null);
const handledCommandTerminalKeys = new Set<string>();

const saveDisabled = computed(() => !timeline.value || status.value === "loading" || isGenerating.value);
const assembleDisabled = computed(() => !currentProjectId.value || status.value === "loading" || isGenerating.value);
const precheckDisabled = computed(() => !timeline.value || status.value === "loading" || isGenerating.value);
const generateDisabled = computed(
  () => !timeline.value || status.value === "loading" || isGenerating.value || !magicCutReadiness.value.available
);
const timelineActionState = computed(() =>
  evaluateTimelineClipActions({
    timeline: timeline.value,
    selectedClipId: selectedClipId.value,
    playheadMs: playheadMs.value,
    stepMs: 500,
    minDurationMs: 500
  })
);
const toolBarStatus = computed(() => {
  if (!timeline.value) return "等待时间线";
  if (selectedClip.value && !timelineActionState.value.canSplit) {
    return `选择工具 · 磁吸开启 · ${timelineActionState.value.reason}`;
  }
  return "选择工具 · 磁吸开启";
});
const canDeleteSelectedClip = computed(() => Boolean(selectedClip.value));
const canMoveSelectedClip = computed(() => timelineActionState.value.canMoveLeft || timelineActionState.value.canMoveRight);
const canMoveSelectedClipLeft = computed(() => timelineActionState.value.canMoveLeft);
const canMoveSelectedClipRight = computed(() => timelineActionState.value.canMoveRight);
const canSplitSelectedClip = computed(() => timelineActionState.value.canSplit);
const canTrimSelectedClip = computed(() => timelineActionState.value.canTrim);

const inspectorBlockedMessage = computed(() => {
  return blockedMessage.value || magicCutUnavailableMessage.value;
});

function handleKeydown(event: KeyboardEvent): void {
  if (isInteractiveShortcutTarget(event.target)) return;

  if (event.key === "Delete" || event.key === "Backspace") {
    if (selectedClipId.value) {
      event.preventDefault();
      void handleDeleteSelectedClip();
    }
  }

  if (event.key === " ") {
    event.preventDefault();
    if (isPlaying.value) {
      handlePause();
    } else {
      handlePlay();
    }
  }
}

function isInteractiveShortcutTarget(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  return Boolean(target.closest("input, textarea, select, button, a, [role='button'], [contenteditable='true']"));
}

onMounted(() => {
  shellUiStore.closeDetailPanel();
  if (aiCapabilityStore.status === "idle" || aiCapabilityStore.settings === null) {
    void aiCapabilityStore.load();
  }

  if (typeof WebSocket !== "undefined") {
    taskBusStore.connect();
  }

  document.addEventListener("keydown", handleKeydown);
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
  [
    currentProjectName,
    timeline,
    selectedTrack,
    selectedClip,
    status,
    blockedMessage,
    error,
    activeTask,
    magicCutRecoveryMessage
  ],
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
              : magicCutRecoveryMessage.value
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
                value: (blockedMessage.value ?? magicCutRecoveryMessage.value) || "无",
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

watch(
  () => Array.from(taskBusStore.tasks.values()).map((task) => `${task.id}:${task.status}:${task.updated_at}:${task.message}`).join("|"),
  () => {
    for (const task of taskBusStore.tasks.values()) {
      if (!isCurrentWorkspaceCommandTask(task) || !isTerminalCommandStatus(task.status)) continue;

      const key = `${task.id}:${task.status}:${task.updated_at}:${task.message}`;
      if (handledCommandTerminalKeys.has(key)) continue;
      handledCommandTerminalKeys.add(key);
      void applyWorkspaceCommandTerminal(task);
    }
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("asset");
  document.removeEventListener("keydown", handleKeydown);
});

onBeforeRouteLeave(async () => {
  if (workspaceStore.saveState?.saved !== true && workspaceStore.timeline) {
    return confirmUnsavedTimelineLeave();
  }
});

function confirmUnsavedTimelineLeave(): Promise<boolean> {
  return requestDesktopConfirm("时间线有未保存的更改，确定要离开吗？", {
    title: "离开 AI 剪辑工作台"
  });
}

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
    if (!magicCutReadiness.value.available) {
      workspaceStore.applyBlockedMessage(magicCutReadiness.value.message);
      return;
    }

    const result = await workspaceStore.runMagicCut(currentProjectId.value);
    if (result?.task?.id) {
      const taskId = result.task.id;

      // 从 HTTP 响应直接写入 TaskBus，绕过 WebSocket 竞态窗口
      const raw = result.task;
      const now = new Date().toISOString();
      taskBusStore.tasks.set(taskId, {
        id: taskId,
        task_type: raw.task_type ?? "ai-workspace-command",
        project_id: currentProjectId.value ?? null,
        status: raw.status ?? "queued",
        progress: raw.progress ?? 0,
        message: raw.message ?? "AI 命令已进入任务队列。",
        created_at: raw.created_at ?? now,
        updated_at: now,
      });
    }
  }
}

async function handleCancelCommandTask(taskId: string): Promise<void> {
  if (!taskId || isCommandCancelPending.value) return;

  isCommandCancelPending.value = true;
  try {
    const result = await workspaceStore.cancelCommandTask(taskId);
    if (result?.task) {
      const existingTask = taskBusStore.tasks.get(taskId);
      taskBusStore.tasks.set(taskId, {
        ...(existingTask ?? result.task),
        status: result.task.status,
        progress: result.task.progress,
        message: result.message,
        updated_at: result.task.updated_at
      });
    }
  } finally {
    isCommandCancelPending.value = false;
  }
}

function isCurrentWorkspaceCommandTask(task: TaskInfo): boolean {
  return task.project_id === currentProjectId.value && workspaceTaskTypes.has(task.task_type);
}

function isTerminalCommandStatus(status: TaskInfo["status"]): boolean {
  return status === "succeeded" || status === "failed" || status === "cancelled";
}

async function applyWorkspaceCommandTerminal(task: TaskInfo): Promise<void> {
  await workspaceStore.applyCommandTerminalTask(task);
}

async function handleReloadAICapabilities(): Promise<void> {
  await aiCapabilityStore.load();
  if (magicCutReadiness.value.available && isMagicCutRecoveryMessage(blockedMessage.value ?? "")) {
    workspaceStore.clearMagicCutBlockedMessage(blockedMessage.value ?? undefined);
  }
}

function handleOpenAISettings(): void {
  void router.push({
    path: "/settings/ai-system",
    query: { section: "capability", capability: "magic_cut", from: "workspace" }
  });
}

function handleOpenTtsSettings(): void {
  void router.push({
    path: "/settings/ai-system",
    query: { section: "capability", capability: "tts", from: "workspace" }
  });
}

function handleOpenVoiceStudio(): void {
  void router.push({
    path: "/voice/studio",
    query: { from: "workspace", missing: "voice" }
  });
}

function handleOpenRenderExport(): void {
  const exportRoute = buildWorkspaceExportRoute(currentProjectId.value, timeline.value);
  if (exportRoute) void router.push(exportRoute);
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

async function handleUndoTimelineEdit(): Promise<void> {
  const result = await workspaceStore.undoTimelineEdit();
  if (result) {
    await workspaceStore.runPrecheck();
  }
}

async function handleRedoTimelineEdit(): Promise<void> {
  const result = await workspaceStore.redoTimelineEdit();
  if (result) {
    await workspaceStore.runPrecheck();
  }
}

function handleTimelineZoomChange(nextZoomPercent: number): void {
  zoomPercent.value = normalizeTimelineZoomPercent(nextZoomPercent);
}

function handleFocusPrecheckIssue(issue: TimelinePrecheckIssueDetailDto | string): void {
  workspaceStore.focusPrecheckIssue(issue);
}

async function handleTimelineTrim(payload: { clipId: string; edge: "left" | "right"; deltaMs: number }): Promise<void> {
  workspaceStore.selectClip(payload.clipId);
  await workspaceStore.trimSelectedClip(payload.edge, payload.deltaMs);
}

function handleTimelineMovePreview(_payload: WorkspaceTimelineMovePreview): void {
  timelineDragFeedback.value = {
    title: "正在调整位置",
    detail: `目标起点：${formatWorkspaceTime(_payload.startMs)} · 时长：${formatWorkspaceTime(_payload.durationMs)}`
  };
}

async function handleTimelineMoveCommit(payload: WorkspaceTimelineMovePreview): Promise<void> {
  timelineDragFeedback.value = null;
  const result = await workspaceStore.commitMovePreview(payload);
  if (result) {
    await workspaceStore.runPrecheck();
  }
}

function handleTimelineTrimPreview(payload: WorkspaceTimelineTrimPreview): void {
  timelineDragFeedback.value = {
    title: "正在裁剪片段",
    detail: `起点：${formatWorkspaceTime(payload.startMs)} · 结束：${formatWorkspaceTime(payload.startMs + payload.durationMs)} · 时长：${formatWorkspaceTime(payload.durationMs)}`
  };
}

async function handleTimelineTrimCommit(payload: WorkspaceTimelineTrimPreview): Promise<void> {
  timelineDragFeedback.value = null;
  const result = await workspaceStore.commitTrimPreview(payload);
  if (result) {
    await workspaceStore.runPrecheck();
  }
}

function handleTimelineDragCancel(_payload: WorkspaceTimelineDragPreview): void {
  timelineDragFeedback.value = null;
}

function handleSelectTrack(trackId: string): void {
  workspaceStore.selectTrack(trackId);
}

function handleSelectClip(payload: { clipId: string; trackId: string }): void {
  workspaceStore.selectTimelineClip(payload);
  const clip = timeline.value?.tracks
    .flatMap((track) => track.clips)
    .find((candidate) => candidate.id === payload.clipId);

  if (clip) {
    workspaceStore.setPlayheadMs(clip.startMs);
  }
}

</script>

<style scoped src="./AIEditingWorkspacePage.css"></style>
