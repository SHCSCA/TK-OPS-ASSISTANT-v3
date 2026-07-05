<template>
  <ProjectContextGuard>
    <div class="editing-workspace-page h-full">
      <header class="page-header">
        <div class="page-header__crumb">首页 / 创作中枢</div>
        <div class="page-header__row">
          <div class="page-header__copy">
            <h1 class="page-header__title">AI 剪辑工作台</h1>
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
              @open-asset-library="handleOpenAssetLibrary"
              @select-source-clip="handleSelectClip"
              @sync-assets="handleSyncAssets"
            />
          </div>

          <div class="stage-panel-wrapper preview-panel-wrapper">
            <p class="panel-label">预览与校验</p>
            <WorkspacePreviewStage
              class="stage-panel preview-panel"
              :preview-context="previewContext"
              :preview-ratio="previewRatio"
              :timeline="timeline"
              :is-playing="isPlaying"
              :play-progress="playProgress"
              :playhead-ms="playheadMs"
              @play="handlePlay"
              @pause="handlePause"
              @ratio-change="workspaceStore.setPreviewRatio"
              @seek="handleSetPlayhead"
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
              :magic-cut-suggestion="magicCutSuggestion"
              :magic-cut-suggestion-error-message="magicCutSuggestionError?.message ?? null"
              :magic-cut-suggestion-status="magicCutSuggestionStatus"
              :precheck="precheck"
              :preview-context="previewContext"
              :save-state="saveState"
              :selected-clip="selectedClip"
              :selected-track="selectedTrack"
              :status="status"
              :timeline="timeline"
              @apply-magic-cut-suggestion="handleApplyMagicCutSuggestion"
              @dismiss-magic-cut-suggestion="handleDismissMagicCutSuggestion"
              @focus-magic-cut-suggestion="handleFocusMagicCutSuggestion"
              @focus-precheck-issue="handleFocusPrecheckIssue"
              @reload-magic-cut-suggestion="handleReloadMagicCutSuggestion"
              @regenerate-magic-cut-suggestion="handleMagicCut"
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
import { computed, onMounted, watch } from "vue";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import Button from "@/components/ui/Button/Button.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
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
import { useAIEditingWorkspaceActions } from "@/modules/workspace/useAIEditingWorkspaceActions";
import { useWorkspaceCommandTasks } from "@/modules/workspace/useWorkspaceCommandTasks";
import { useMagicCutReadiness } from "@/modules/workspace/useMagicCutReadiness";
import { useWorkspacePlayback } from "@/modules/workspace/useWorkspacePlayback";
import { useWorkspaceShellDetailContext } from "@/modules/workspace/useWorkspaceShellDetailContext";
import { evaluateTimelineClipActions } from "@/modules/workspace/workspaceTimelineActions";
import { useAICapabilityStore } from "@/stores/ai-capability";
import { isMagicCutRecoveryMessage, useEditingWorkspaceStore } from "@/stores/editing-workspace";
import { useProjectStore } from "@/stores/project";

const projectStore = useProjectStore();
const workspaceStore = useEditingWorkspaceStore();
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
  magicCutSuggestion,
  magicCutSuggestionError,
  magicCutSuggestionStatus,
  orderedTracks,
  playheadMs,
  precheck,
  previewContext,
  previewRatio,
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
const {
  handleAssemble,
  handleAssetInsert,
  handleAssetReplace,
  handleCreateDraft,
  handleDeleteSelectedClip,
  handleFocusPrecheckIssue,
  handleMoveSelectedClip,
  handleOpenAISettings,
  handleOpenAssetLibrary,
  handleOpenRenderExport,
  handleOpenTtsSettings,
  handleOpenVoiceStudio,
  handlePrecheck,
  handleRedoTimelineEdit,
  handleRetry,
  handleSave,
  handleSelectClip,
  handleSelectTrack,
  handleSplitSelectedClip,
  handleSyncAssets,
  handleTimelineDragCancel,
  handleTimelineMoveCommit,
  handleTimelineMovePreview,
  handleTimelineTrim,
  handleTimelineTrimCommit,
  handleTimelineTrimPreview,
  handleTimelineZoomChange,
  handleTrimSelectedClip,
  handleUndoTimelineEdit,
  timelineDragFeedback,
  zoomPercent
} = useAIEditingWorkspaceActions({
  currentProjectId,
  isPlaying,
  pause: handlePause,
  play: handlePlay,
  timeline,
  workspaceStore
});
const {
  activeTask,
  handleCancelCommandTask,
  handleMagicCut,
  isCommandCancelPending,
  isGenerating
} = useWorkspaceCommandTasks({
  currentProjectId,
  magicCutReadiness,
  workspaceStore
});
const {
  assemblyLabel,
  inspectorBlockedMessage,
  magicCutRecoveryMessage,
  managedTrackSyncRecovery,
  precheckLabel,
  selectionLabel,
  sourceRecovery
} = useWorkspaceShellDetailContext({
  activeTask,
  assemblyState,
  blockedMessage,
  currentProjectName,
  error,
  hasTimeline,
  magicCutReadiness,
  orderedTracks,
  precheck,
  resolveTimelineDurationMs: () => workspaceStore.resolveTimelineDurationMs(),
  selectedClip,
  selectedTrack,
  status,
  timeline,
  timelineName
});

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

onMounted(() => {
  if (aiCapabilityStore.status === "idle" || aiCapabilityStore.settings === null) {
    void aiCapabilityStore.load();
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

async function handleReloadAICapabilities(): Promise<void> {
  await aiCapabilityStore.load();
  if (magicCutReadiness.value.available && isMagicCutRecoveryMessage(blockedMessage.value ?? "")) {
    workspaceStore.clearMagicCutBlockedMessage(blockedMessage.value ?? undefined);
  }
}

async function handleApplyMagicCutSuggestion(operationIds: string[]): Promise<void> {
  await workspaceStore.applyMagicCutSuggestion(operationIds);
}

async function handleDismissMagicCutSuggestion(): Promise<void> {
  await workspaceStore.dismissMagicCutSuggestion();
}

async function handleReloadMagicCutSuggestion(): Promise<void> {
  await workspaceStore.loadMagicCutSuggestion();
}

function handleFocusMagicCutSuggestion(payload: { clipId: string; trackId?: string | null }): void {
  const clip = workspaceStore.findClipById(payload.clipId);
  if (clip) {
    workspaceStore.selectTimelineClip({
      clipId: clip.id,
      trackId: payload.trackId || clip.trackId
    });
    handleSetPlayhead(clip.startMs);
    return;
  }

  if (payload.trackId) {
    workspaceStore.selectTimelineClip({
      clipId: payload.clipId,
      trackId: payload.trackId
    });
  } else {
    workspaceStore.selectClip(payload.clipId);
  }
}

</script>

<style scoped src="./AIEditingWorkspacePage.css"></style>
