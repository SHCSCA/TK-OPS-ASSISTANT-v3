<template>
  <aside class="workspace-inspector" aria-label="时间线检查器">
    <div class="workspace-inspector__heading">
      <span class="material-symbols-outlined">tune</span>
      <div>
        <strong>基础属性</strong>
        <p>{{ headingDescription }}</p>
      </div>
    </div>

    <transition name="msg-fade">
      <div v-if="errorMessage" key="error" class="workspace-inspector__message workspace-inspector__message--error">
        {{ errorMessage }}
      </div>
      <div v-else-if="blockedMessage" key="blocked" class="workspace-inspector__message workspace-inspector__message--warning">
        {{ blockedMessage }}
      </div>
    </transition>

    <WorkspaceInspectorClipActions
      :precheck="precheck"
      :preview-context="previewContext"
      :save-state="saveState"
      :selected-clip="selectedClip"
      :timeline="timeline"
      @seek-clip-start="emit('seek-clip-start')"
    />

    <section class="workspace-inspector__section">
      <h3>片段信息</h3>
      <dl class="workspace-inspector__facts">
        <div class="fact-item">
          <dt>工作台状态</dt>
          <dd>
            <strong>{{ statusLabel }}</strong>
            <span>{{ statusDescription }}</span>
          </dd>
        </div>
        <div class="fact-item">
          <dt>时间线</dt>
          <dd>{{ timeline?.name ?? "未创建" }}</dd>
        </div>
        <div class="fact-item">
          <dt>轨道</dt>
          <dd>{{ selectedTrack?.name ?? "未选择" }}</dd>
        </div>
        <div class="fact-item">
          <dt>片段</dt>
          <dd>{{ selectedClip?.label ?? "未选择" }}</dd>
        </div>
        <div class="fact-item">
          <dt>当前片段</dt>
          <dd>{{ currentClipLabel }}</dd>
        </div>
        <div class="fact-item">
          <dt>片段状态</dt>
          <dd>{{ workspaceStatusLabel(selectedClip?.status) }}</dd>
        </div>
        <div class="fact-item">
          <dt>保存状态</dt>
          <dd>
            <strong>{{ saveStateTitle }}</strong>
            <span>{{ saveStateDescription }}</span>
          </dd>
        </div>
      </dl>
    </section>

    <section class="workspace-inspector__section">
      <h3>时间参数</h3>
      <dl class="workspace-inspector__facts workspace-inspector__facts--compact">
        <div class="fact-item">
          <dt>起点</dt>
          <dd>{{ clipStartLabel }}</dd>
        </div>
        <div class="fact-item">
          <dt>时长</dt>
          <dd>{{ clipDurationLabel }}</dd>
        </div>
      </dl>
    </section>

    <section class="workspace-inspector__section">
      <h3>素材来源</h3>
      <p>{{ sourceDescription }}</p>
    </section>

    <section class="workspace-inspector__section">
      <h3>预检提醒</h3>
      <strong>{{ precheckTitle }}</strong>
      <p>{{ precheckDescription }}</p>
      <TransitionGroup v-if="precheckIssues.length > 0" tag="ul" name="issue-slide" class="workspace-inspector__issue-list">
        <li v-for="(issue, index) in precheckIssues" :key="precheckIssueKey(issue, index)">
          <div class="workspace-inspector__issue-content">
            <strong>{{ precheckIssueMessage(issue) }}</strong>
            <span v-if="precheckIssueTargetLabel(issue)">{{ precheckIssueTargetLabel(issue) }}</span>
            <p v-if="precheckIssueSuggestion(issue)">{{ precheckIssueSuggestion(issue) }}</p>
          </div>
          <button type="button" data-testid="workspace-precheck-issue" @click="emit('focus-precheck-issue', issue)">
            {{ precheckIssueActionLabel(issue) }}
          </button>
        </li>
      </TransitionGroup>
    </section>

    <section
      class="workspace-inspector__card workspace-inspector__card--export"
      data-testid="workspace-export-readiness"
    >
      <small>导出就绪</small>
      <strong>{{ exportReadiness.title }}</strong>
      <p>{{ exportReadiness.description }}</p>
      <button
        class="workspace-inspector__export-action"
        data-testid="workspace-export-readiness-action"
        :disabled="!canRequestExport"
        type="button"
        @click="handleRequestExport"
      >
        <span class="material-symbols-outlined">output</span>
        送往渲染与导出中心
      </button>
    </section>

    <details class="workspace-inspector__details" data-testid="workspace-ai-suggestion-details">
      <summary>
        <span>AI 粗剪建议</span>
        <em>默认折叠</em>
      </summary>
      <WorkspaceMagicCutSuggestions
        :error-message="magicCutSuggestionErrorMessage"
        :status="magicCutSuggestionStatus"
        :suggestion="magicCutSuggestion"
        @apply="(operationIds) => emit('apply-magic-cut-suggestion', operationIds)"
        @dismiss="emit('dismiss-magic-cut-suggestion')"
        @focus="(payload) => emit('focus-magic-cut-suggestion', payload)"
        @reload="emit('reload-magic-cut-suggestion')"
        @regenerate="emit('regenerate-magic-cut-suggestion')"
      />
    </details>

    <section v-if="assemblyState" class="workspace-inspector__card">
      <small>创作链路</small>
      <strong>{{ assemblyState.status === "ready" ? "来源已接入" : "来源需处理" }}</strong>
      <p>{{ assemblySummary }}</p>
    </section>

    <section class="workspace-inspector__card">
      <small>基础工具</small>
      <strong>{{ actionBoundaryTitle }}</strong>
      <p>{{ actionBoundaryDescription }}</p>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { EditingWorkspaceStatus } from "@/stores/editing-workspace";
import type {
  TimelinePrecheckDto,
  TimelinePrecheckIssueDetailDto,
  MagicCutSuggestionDraftDto,
  WorkspaceAICommandResultDto,
  WorkspaceAssemblyStateDto,
  WorkspaceSaveStateDto,
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";
import type { WorkspacePreviewContext } from "./workspacePreviewContext";
import WorkspaceInspectorClipActions from "./WorkspaceInspectorClipActions.vue";
import WorkspaceMagicCutSuggestions from "./WorkspaceMagicCutSuggestions.vue";
import { resolveTimelinePrecheckIssueCount, resolveWorkspaceExportReadiness } from "./workspaceExportReadiness";
import { workspaceStatusLabel } from "./workspaceTimelineViewModel";

const props = withDefaults(defineProps<{
  assemblyState: WorkspaceAssemblyStateDto | null;
  blockedMessage: string | null;
  errorMessage: string | null;
  lastCommandResult: WorkspaceAICommandResultDto | null;
  magicCutSuggestion?: MagicCutSuggestionDraftDto | null;
  magicCutSuggestionErrorMessage?: string | null;
  magicCutSuggestionStatus?: "idle" | "loading" | "ready" | "applying" | "error";
  precheck: TimelinePrecheckDto | null;
  previewContext: WorkspacePreviewContext;
  saveState: WorkspaceSaveStateDto | null;
  selectedClip: WorkspaceTimelineClipDto | null;
  selectedTrack: WorkspaceTimelineTrackDto | null;
  status: EditingWorkspaceStatus;
  timeline: WorkspaceTimelineDto | null;
}>(), {
  magicCutSuggestion: null,
  magicCutSuggestionErrorMessage: null,
  magicCutSuggestionStatus: "idle"
});

const emit = defineEmits<{
  "focus-precheck-issue": [issue: TimelinePrecheckIssueDetailDto | string];
  "apply-magic-cut-suggestion": [operationIds: string[]];
  "dismiss-magic-cut-suggestion": [];
  "focus-magic-cut-suggestion": [payload: { clipId: string; trackId?: string | null }];
  "reload-magic-cut-suggestion": [];
  "regenerate-magic-cut-suggestion": [];
  "request-export": [];
  "seek-clip-start": [];
}>();

const statusLabel = computed(() => {
  const map: Record<EditingWorkspaceStatus, string> = {
    blocked: "能力阻断",
    empty: "空态",
    error: "请求失败",
    idle: "待加载",
    loading: "加载中",
    ready: "已就绪",
    saving: "保存中"
  };
  return map[props.status];
});

const headingDescription = computed(() => {
  if (props.timeline) return props.saveState?.message ?? "围绕当前时间线、轨道和片段给出真实上下文。";
  return "等待时间线草稿进入工作台。";
});

const statusDescription = computed(() => {
  if (props.status === "blocked") return "AI 命令走真实 blocked 语义，不会生成假任务。";
  if (props.status === "error") return props.errorMessage ?? "请求失败，请稍后重试。";
  if (props.status === "empty") return "当前没有时间线草稿。";
  if (props.status === "saving") return "正在将当前时间线草稿写回 Runtime。";
  if (props.status === "loading") return "正在读取当前项目的时间线。";
  return "当前可继续在真实时间线草稿上选择、保存和查看上下文。";
});

const currentClipLabel = computed(() => {
  return props.previewContext.clip ? props.previewContext.detailText : "当前片段：未命中";
});

const saveStateTitle = computed(() => {
  if (props.status === "saving") return "保存中";
  if (!props.saveState) return "未保存";
  return props.saveState.saved ? "已保存" : "保存未完成";
});

const saveStateDescription = computed(() => {
  if (props.status === "saving") return "正在将当前时间线草稿写回 Runtime。";
  return props.saveState?.message ?? "保存时间线后显示 Runtime 返回结果。";
});

const actionBoundaryTitle = computed(() => {
  if (!props.timeline) return "先创建时间线";
  if (!props.selectedClip) return "先选中片段";
  return "当前片段已联动";
});

const actionBoundaryDescription = computed(() => {
  if (!props.timeline) return "没有时间线时，基础工具保持不可用。";
  if (!props.selectedClip) return "选择片段后显示起点、时长和来源。";
  return `片段状态：${workspaceStatusLabel(props.selectedClip.status)}，来源：${sourceKindLabel(clipSourceKind.value)}。`;
});

const clipStartLabel = computed(() => {
  if (!props.selectedClip) return "未选择";
  return formatMs(props.selectedClip.startMs);
});

const clipDurationLabel = computed(() => {
  if (!props.selectedClip) return "未选择";
  return formatMs(props.selectedClip.durationMs);
});

const clipSourceKind = computed(() => {
  return props.selectedClip?.metadata?.sourceKind ?? props.selectedClip?.sourceType ?? "";
});

const sourceDescription = computed(() => {
  if (!props.selectedClip) return "选中片段后显示资产中心或创作链路来源。";
  if (clipSourceKind.value === "asset") {
    return "该片段来自资产中心素材，可在后续功能中替换或在资产中心处理。";
  }
  return `该片段来自${sourceKindLabel(clipSourceKind.value)}。`;
});

const precheckTitle = computed(() => {
  if (!props.precheck) return "未执行";
  return props.precheck.status === "ready" ? "通过" : "需处理";
});

const precheckDescription = computed(() => {
  if (!props.precheck) return "点击本地预检后显示时间线检查结果。";
  if (precheckIssueCount.value === 0) return props.precheck.message ?? "时间线本地预检通过。";
  return props.precheck.message ?? "预检发现需要处理的问题。";
});

const precheckIssues = computed<Array<TimelinePrecheckIssueDetailDto | string>>(() => {
  const detailIssues = props.precheck?.issueDetails ?? [];
  return detailIssues.length > 0 ? detailIssues : props.precheck?.issues ?? [];
});

const precheckIssueCount = computed(() => resolveTimelinePrecheckIssueCount(props.precheck));

const exportReadiness = computed(() => {
  return resolveWorkspaceExportReadiness({
    issueCount: precheckIssueCount.value,
    precheck: props.precheck,
    saveState: props.saveState,
    timeline: props.timeline
  });
});
const canRequestExport = computed(() => exportReadiness.value.canRequestExport);

const assemblySummary = computed(() => {
  if (!props.assemblyState) return "";
  if (props.assemblyState.issues.length > 0) return props.assemblyState.issues.join(" ");
  return props.assemblyState.sources
    .map((source) => `${sourceKindLabel(source.kind)} ${source.segmentCount} 段`)
    .join(" · ");
});

function sourceKindLabel(kind: string): string {
  if (kind === "asset") return "资产中心";
  if (kind === "voice_track") return "配音中心";
  if (kind === "subtitle_track") return "字幕对齐";
  if (kind === "imported_video") return "视频拆解";
  if (kind === "manual") return "手动片段";
  if (kind === "script") return "脚本";
  if (kind === "storyboard") return "分镜";
  if (kind === "voice") return "配音";
  if (kind === "subtitle") return "字幕";
  return kind;
}

function formatMs(value: number): string {
  const totalSeconds = Math.max(0, Math.floor(value / 1000));
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function precheckIssueKey(issue: TimelinePrecheckIssueDetailDto | string, index: number): string {
  if (typeof issue === "string") return `legacy-${index}-${issue}`;
  return [
    issue.id ?? "detail",
    issue.code ?? "no-code",
    issue.targetId ?? issue.clipId ?? issue.trackId ?? "no-target",
    index
  ].join("-");
}

function precheckIssueMessage(issue: TimelinePrecheckIssueDetailDto | string): string {
  return typeof issue === "string" ? issue : issue.message;
}

function precheckIssueSuggestion(issue: TimelinePrecheckIssueDetailDto | string): string {
  if (typeof issue === "string") return "";
  return issue.suggestion?.trim() ?? "";
}

function precheckIssueTargetLabel(issue: TimelinePrecheckIssueDetailDto | string): string {
  if (typeof issue === "string") return "";
  const targetLabel = issue.targetLabel?.trim() || issue.targetId?.trim() || issue.clipId?.trim() || issue.trackId?.trim();
  const targetTypeLabel = precheckIssueTargetTypeLabel(issue);
  if (!targetLabel) return targetTypeLabel ? `${targetTypeLabel}：未标明对象` : "";
  return targetTypeLabel ? `${targetTypeLabel}：${targetLabel}` : targetLabel;
}

function precheckIssueTargetTypeLabel(issue: TimelinePrecheckIssueDetailDto): string {
  const targetType = issue.targetType?.trim();
  if (targetType === "clip" || issue.clipId) return "片段";
  if (targetType === "track" || issue.trackId) return "轨道";
  if (targetType === "timeline") return "时间线";
  if (targetType === "asset") return "素材";
  return targetType ? "对象" : "";
}

function precheckIssueActionLabel(issue: TimelinePrecheckIssueDetailDto | string): string {
  if (typeof issue === "string") return issue;
  return issue.actionLabel?.trim() || "定位问题";
}

function handleRequestExport(): void {
  if (!canRequestExport.value) return;
  emit("request-export");
}
</script>

<style scoped src="./WorkspaceInspector.css"></style>
