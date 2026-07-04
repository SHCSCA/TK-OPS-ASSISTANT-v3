import { computed, onBeforeUnmount, onMounted, watch, type ComputedRef, type Ref } from "vue";

import type { MagicCutReadiness } from "@/modules/workspace/useMagicCutReadiness";
import { buildSourceRecoveryViewModel } from "@/modules/workspace/workspaceRecoveryViewModel";
import {
  cleanWorkspaceText,
  formatWorkspaceTime,
  summarizeManagedTrackSync,
  workspaceStatusLabel
} from "@/modules/workspace/workspaceTimelineViewModel";
import { isMagicCutRecoveryMessage, type EditingWorkspaceStatus } from "@/stores/editing-workspace";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import type { RuntimeRequestErrorShape, TimelinePrecheckDto, WorkspaceAssemblyStateDto, WorkspaceTimelineClipDto, WorkspaceTimelineDto, WorkspaceTimelineTrackDto } from "@/types/runtime";
import type { TaskInfo } from "@/types/task-events";

type UseWorkspaceShellDetailContextOptions = {
  activeTask: ComputedRef<TaskInfo | null>;
  assemblyState: Ref<WorkspaceAssemblyStateDto | null>;
  blockedMessage: Ref<string | null>;
  currentProjectName: ComputedRef<string>;
  error: Ref<RuntimeRequestErrorShape | null>;
  hasTimeline: Ref<boolean>;
  magicCutReadiness: ComputedRef<MagicCutReadiness>;
  orderedTracks: Ref<WorkspaceTimelineTrackDto[]>;
  precheck: Ref<TimelinePrecheckDto | null>;
  resolveTimelineDurationMs: () => number;
  selectedClip: Ref<WorkspaceTimelineClipDto | null>;
  selectedTrack: Ref<WorkspaceTimelineTrackDto | null>;
  status: Ref<EditingWorkspaceStatus>;
  timeline: Ref<WorkspaceTimelineDto | null>;
  timelineName: ComputedRef<string>;
};

export function useWorkspaceShellDetailContext(options: UseWorkspaceShellDetailContextOptions) {
  const shellUiStore = useShellUiStore();

  const assemblyLabel = computed(() => {
    if (!options.assemblyState.value) return "未汇入";
    return options.assemblyState.value.status === "ready" ? "已接入" : "需处理";
  });
  const precheckLabel = computed(() => {
    if (!options.precheck.value) return "未检查";
    return options.precheck.value.status === "ready" ? "通过" : "有问题";
  });
  const magicCutUnavailableMessage = computed(() => {
    if (!options.timeline.value || options.magicCutReadiness.value.available) return "";
    return options.magicCutReadiness.value.message;
  });
  const magicCutBlockedRecoveryMessage = computed(() => {
    const message = options.blockedMessage.value ?? "";
    return isMagicCutRecoveryMessage(message) ? message : "";
  });
  const magicCutRecoveryMessage = computed(() => {
    return magicCutBlockedRecoveryMessage.value || magicCutUnavailableMessage.value;
  });
  const managedTrackSyncRecovery = computed(() => {
    if (!options.timeline.value) {
      return {
        message: "",
        visible: false
      };
    }

    const declaredDurationMs = Math.max(0, (options.timeline.value.durationSeconds ?? 0) * 1000);
    const summary = summarizeManagedTrackSync(
      options.timeline.value.tracks,
      options.resolveTimelineDurationMs(),
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
      assemblyState: options.assemblyState.value,
      hasTimeline: Boolean(options.timeline.value),
      trackCount: options.orderedTracks.value.length
    });
  });
  const selectionLabel = computed(() => {
    if (options.selectedClip.value) {
      return `片段：${cleanWorkspaceText(options.selectedClip.value.label, "未命名片段")}`;
    }
    if (options.selectedTrack.value) return `轨道：${options.selectedTrack.value.name}`;
    if (options.hasTimeline.value) return "尚未选择轨道或片段";
    return "等待创建时间线";
  });
  const inspectorBlockedMessage = computed(() => {
    return options.blockedMessage.value || magicCutUnavailableMessage.value;
  });

  onMounted(() => {
    shellUiStore.closeDetailPanel();
  });

  watch(
    [
      options.currentProjectName,
      options.timeline,
      options.selectedTrack,
      options.selectedClip,
      options.status,
      options.blockedMessage,
      options.error,
      options.activeTask,
      magicCutRecoveryMessage
    ],
    () => {
      shellUiStore.setDetailContext(
        createRouteDetailContext("asset", {
          icon: "movie_edit",
          eyebrow: "AI 剪辑工作台",
          title: options.currentProjectName.value,
          description: options.hasTimeline.value ? "时间线与检查器保持联动。" : "等待创建主时间线。",
          badge: {
            label: options.activeTask.value ? "处理中" : workspaceStatusLabel(options.status.value),
            tone: options.error.value
              ? "danger"
              : options.blockedMessage.value
                ? "warning"
                : magicCutRecoveryMessage.value
                  ? "warning"
                  : options.activeTask.value
                    ? "brand"
                    : "neutral"
          },
          metrics: [
            { id: "timeline", label: "时间线", value: options.timelineName.value },
            { id: "tracks", label: "轨道数", value: String(options.timeline.value?.tracks.length ?? 0) },
            { id: "selection", label: "当前选择", value: selectionLabel.value },
            { id: "assembly", label: "汇入", value: assemblyLabel.value },
            { id: "precheck", label: "预检", value: precheckLabel.value }
          ],
          sections: [
            {
              id: "selection",
              title: "当前选择",
              fields: [
                { id: "track", label: "轨道", value: options.selectedTrack.value?.name ?? "未选择" },
                {
                  id: "clip",
                  label: "片段",
                  value: options.selectedClip.value
                    ? cleanWorkspaceText(options.selectedClip.value.label, "未命名片段")
                    : "未选择"
                },
                { id: "status", label: "片段状态", value: workspaceStatusLabel(options.selectedClip.value?.status) }
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
                  value: (options.blockedMessage.value ?? magicCutRecoveryMessage.value) || "无",
                  multiline: true
                },
                {
                  id: "error",
                  label: "错误",
                  value: options.error.value?.message ?? "无",
                  multiline: true
                },
                {
                  id: "task",
                  label: "活跃任务",
                  value: options.activeTask.value
                    ? `${options.activeTask.value.message}（${options.activeTask.value.progress}%）`
                    : "无"
                },
                {
                  id: "precheck",
                  label: "本地预检",
                  value: options.precheck.value?.message ?? "未执行",
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

  return {
    assemblyLabel,
    inspectorBlockedMessage,
    magicCutBlockedRecoveryMessage,
    magicCutRecoveryMessage,
    magicCutUnavailableMessage,
    managedTrackSyncRecovery,
    precheckLabel,
    selectionLabel,
    sourceRecovery
  };
}
