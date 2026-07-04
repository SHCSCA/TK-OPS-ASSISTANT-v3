import { onBeforeUnmount, onMounted, ref, type ComputedRef, type Ref } from "vue";
import { onBeforeRouteLeave, useRouter } from "vue-router";

import { requestDesktopConfirm } from "@/composables/useDesktopConfirm";
import type {
  WorkspaceTimelineDragPreview,
  WorkspaceTimelineMovePreview,
  WorkspaceTimelineTrimPreview
} from "@/modules/workspace/useWorkspaceTimelineDrag";
import { buildWorkspaceExportRoute } from "@/modules/workspace/workspaceExportReadiness";
import { normalizeTimelineZoomPercent } from "@/modules/workspace/workspaceTimelineGeometry";
import { formatWorkspaceTime } from "@/modules/workspace/workspaceTimelineViewModel";
import { useEditingWorkspaceStore } from "@/stores/editing-workspace";
import type { TimelinePrecheckIssueDetailDto, WorkspaceTimelineDto } from "@/types/runtime";

type UseAIEditingWorkspaceActionsOptions = {
  currentProjectId: ComputedRef<string>;
  isPlaying: Ref<boolean>;
  pause: () => void;
  play: () => void;
  timeline: Ref<WorkspaceTimelineDto | null>;
  workspaceStore: ReturnType<typeof useEditingWorkspaceStore>;
};

export function useAIEditingWorkspaceActions(options: UseAIEditingWorkspaceActionsOptions) {
  const router = useRouter();
  const timelineDragFeedback = ref<{ detail: string; title: string } | null>(null);
  const zoomPercent = ref(100);

  onMounted(() => {
    document.addEventListener("keydown", handleKeydown);
  });

  onBeforeUnmount(() => {
    document.removeEventListener("keydown", handleKeydown);
  });

  onBeforeRouteLeave(async () => {
    if (options.workspaceStore.saveState?.saved !== true && options.workspaceStore.timeline) {
      return confirmUnsavedTimelineLeave();
    }
  });

  function confirmUnsavedTimelineLeave(): Promise<boolean> {
    return requestDesktopConfirm("时间线有未保存的更改，确定要离开吗？", {
      title: "离开 AI 剪辑工作台"
    });
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (isInteractiveShortcutTarget(event.target)) return;

    if (event.key === "Delete" || event.key === "Backspace") {
      if (options.workspaceStore.selectedClipId) {
        event.preventDefault();
        void handleDeleteSelectedClip();
      }
    }

    if (event.key === " ") {
      event.preventDefault();
      if (options.isPlaying.value) {
        options.pause();
      } else {
        options.play();
      }
    }
  }

  function isInteractiveShortcutTarget(target: EventTarget | null): boolean {
    if (!(target instanceof Element)) return false;
    return Boolean(target.closest("input, textarea, select, button, a, [role='button'], [contenteditable='true']"));
  }

  async function handleCreateDraft(): Promise<void> {
    if (options.currentProjectId.value) {
      await options.workspaceStore.createDraft(options.currentProjectId.value, "主时间线");
    }
  }

  async function handleSave(): Promise<void> {
    await options.workspaceStore.saveTimeline();
  }

  async function handleAssemble(): Promise<void> {
    if (options.currentProjectId.value) {
      await options.workspaceStore.assembleTimeline(options.currentProjectId.value);
    }
  }

  async function handlePrecheck(): Promise<void> {
    await options.workspaceStore.runPrecheck();
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
    const exportRoute = buildWorkspaceExportRoute(options.currentProjectId.value, options.timeline.value);
    if (exportRoute) void router.push(exportRoute);
  }

  async function handleRetry(): Promise<void> {
    if (options.currentProjectId.value) {
      await options.workspaceStore.load(options.currentProjectId.value);
    }
  }

  async function handleSyncAssets(): Promise<void> {
    if (options.currentProjectId.value) {
      await options.workspaceStore.loadAssets(options.currentProjectId.value);
    }
  }

  async function handleAssetInsert(assetId: string): Promise<void> {
    const result = await options.workspaceStore.insertAssetAtPlayhead(assetId);
    if (result) {
      await options.workspaceStore.runPrecheck();
    }
  }

  async function handleAssetReplace(assetId: string): Promise<void> {
    const result = await options.workspaceStore.replaceSelectedClipWithAsset(assetId);
    if (result) {
      await options.workspaceStore.runPrecheck();
    }
  }

  async function handleDeleteSelectedClip(): Promise<void> {
    await options.workspaceStore.deleteSelectedClip();
  }

  async function handleSplitSelectedClip(): Promise<void> {
    await options.workspaceStore.splitSelectedClip();
  }

  async function handleMoveSelectedClip(deltaMs: number): Promise<void> {
    await options.workspaceStore.moveSelectedClipBy(deltaMs);
  }

  async function handleTrimSelectedClip(edge: "left" | "right", deltaMs: number): Promise<void> {
    await options.workspaceStore.trimSelectedClip(edge, deltaMs);
  }

  async function handleUndoTimelineEdit(): Promise<void> {
    const result = await options.workspaceStore.undoTimelineEdit();
    if (result) {
      await options.workspaceStore.runPrecheck();
    }
  }

  async function handleRedoTimelineEdit(): Promise<void> {
    const result = await options.workspaceStore.redoTimelineEdit();
    if (result) {
      await options.workspaceStore.runPrecheck();
    }
  }

  function handleTimelineZoomChange(nextZoomPercent: number): void {
    zoomPercent.value = normalizeTimelineZoomPercent(nextZoomPercent);
  }

  function handleFocusPrecheckIssue(issue: TimelinePrecheckIssueDetailDto | string): void {
    options.workspaceStore.focusPrecheckIssue(issue);
  }

  async function handleTimelineTrim(payload: { clipId: string; edge: "left" | "right"; deltaMs: number }): Promise<void> {
    options.workspaceStore.selectClip(payload.clipId);
    await options.workspaceStore.trimSelectedClip(payload.edge, payload.deltaMs);
  }

  function handleTimelineMovePreview(payload: WorkspaceTimelineMovePreview): void {
    timelineDragFeedback.value = {
      title: "正在调整位置",
      detail: `目标起点：${formatWorkspaceTime(payload.startMs)} · 时长：${formatWorkspaceTime(payload.durationMs)}`
    };
  }

  async function handleTimelineMoveCommit(payload: WorkspaceTimelineMovePreview): Promise<void> {
    timelineDragFeedback.value = null;
    const result = await options.workspaceStore.commitMovePreview(payload);
    if (result) {
      await options.workspaceStore.runPrecheck();
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
    const result = await options.workspaceStore.commitTrimPreview(payload);
    if (result) {
      await options.workspaceStore.runPrecheck();
    }
  }

  function handleTimelineDragCancel(_payload: WorkspaceTimelineDragPreview): void {
    timelineDragFeedback.value = null;
  }

  function handleSelectTrack(trackId: string): void {
    options.workspaceStore.selectTrack(trackId);
  }

  function handleSelectClip(payload: { clipId: string; trackId: string }): void {
    options.workspaceStore.selectTimelineClip(payload);
    const clip = options.timeline.value?.tracks
      .flatMap((track) => track.clips)
      .find((candidate) => candidate.id === payload.clipId);

    if (clip) {
      options.workspaceStore.setPlayheadMs(clip.startMs);
      void options.workspaceStore.refreshTimelinePreview();
    }
  }

  return {
    handleAssemble,
    handleAssetInsert,
    handleAssetReplace,
    handleCreateDraft,
    handleDeleteSelectedClip,
    handleFocusPrecheckIssue,
    handleMoveSelectedClip,
    handleOpenAISettings,
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
  };
}
