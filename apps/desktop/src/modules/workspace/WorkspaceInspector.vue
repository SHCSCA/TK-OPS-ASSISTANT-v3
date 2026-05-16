<template>
  <aside class="workspace-inspector" aria-label="时间线检查器">
    <div class="workspace-inspector__heading">
      <span class="material-symbols-outlined">tune</span>
      <div>
        <strong>基础属性</strong>
        <p>{{ headingDescription }}</p>
      </div>
    </div>

    <div v-if="errorMessage" class="workspace-inspector__message workspace-inspector__message--error">
      {{ errorMessage }}
    </div>
    <div v-else-if="blockedMessage" class="workspace-inspector__message workspace-inspector__message--warning">
      {{ blockedMessage }}
    </div>

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
          <dt>片段状态</dt>
          <dd>{{ selectedClip?.status ?? "未选择" }}</dd>
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
    </section>

    <details class="workspace-inspector__details" data-testid="workspace-ai-suggestion-details">
      <summary>
        <span>AI 粗剪建议</span>
        <em>默认折叠</em>
      </summary>
      <p>{{ aiSuggestionDescription }}</p>
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
  WorkspaceAICommandResultDto,
  WorkspaceAssemblyStateDto,
  WorkspaceSaveStateDto,
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";

const props = defineProps<{
  assemblyState: WorkspaceAssemblyStateDto | null;
  blockedMessage: string | null;
  errorMessage: string | null;
  lastCommandResult: WorkspaceAICommandResultDto | null;
  precheck: TimelinePrecheckDto | null;
  saveState: WorkspaceSaveStateDto | null;
  selectedClip: WorkspaceTimelineClipDto | null;
  selectedTrack: WorkspaceTimelineTrackDto | null;
  status: EditingWorkspaceStatus;
  timeline: WorkspaceTimelineDto | null;
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

const actionBoundaryTitle = computed(() => {
  if (!props.timeline) return "先创建时间线";
  if (!props.selectedClip) return "先选中片段";
  return "当前片段已联动";
});

const actionBoundaryDescription = computed(() => {
  if (!props.timeline) return "没有时间线时，基础工具保持不可用。";
  if (!props.selectedClip) return "选择片段后显示起点、时长和来源。";
  return `片段状态：${props.selectedClip.status}，来源：${sourceKindLabel(clipSourceKind.value)}。`;
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
    return "该片段来自资产中心素材，可在后续功能中替换或重新定位。";
  }
  return `该片段来自${sourceKindLabel(clipSourceKind.value)}。`;
});

const aiSuggestionDescription = computed(() => {
  return props.lastCommandResult?.message ?? "暂无可应用建议。AI 建议必须经确认后才会修改时间线。";
});

const precheckTitle = computed(() => {
  if (!props.precheck) return "未执行";
  return props.precheck.status === "ready" ? "通过" : "需处理";
});

const precheckDescription = computed(() => {
  if (!props.precheck) return "点击本地预检后显示时间线检查结果。";
  if (props.precheck.issues.length === 0) return props.precheck.message ?? "时间线本地预检通过。";
  return props.precheck.issues.join(" ");
});

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
</script>

<style scoped>
.workspace-inspector {
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
  display: grid;
  gap: 14px;
  padding: 18px;
}

.workspace-inspector__heading {
  align-items: center;
  display: flex;
  gap: 12px;
}

.workspace-inspector__heading p,
.workspace-inspector__message,
.workspace-inspector__card p,
.workspace-inspector__section p,
.workspace-inspector__details p {
  color: var(--text-secondary);
  margin: 0;
}

.workspace-inspector__message,
.workspace-inspector__card,
.workspace-inspector__section,
.workspace-inspector__details {
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  padding: 14px;
}

.workspace-inspector__message--error {
  border-color: color-mix(in srgb, var(--color-danger) 35%, var(--border-default));
  color: var(--color-danger);
}

.workspace-inspector__message--warning {
  border-color: color-mix(in srgb, var(--color-warning) 35%, var(--border-default));
  color: var(--color-warning);
}

.workspace-inspector__card small {
  color: var(--text-tertiary);
}

.workspace-inspector__section h3 {
  font-size: 14px;
  margin: 0;
}

.workspace-inspector__section strong {
  color: var(--text-primary);
}

.workspace-inspector__facts {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
}

.workspace-inspector__facts--compact {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.scroll-area {
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-strong) transparent;
}

.scroll-area::-webkit-scrollbar {
  width: 4px;
}
.scroll-area::-webkit-scrollbar-thumb {
  background: var(--color-border-strong);
  border-radius: 99px;
}

.workspace-inspector__facts div {
  display: grid;
  gap: 4px;
}

.workspace-inspector__facts dt {
  color: var(--text-tertiary);
  font-size: 12px;
}

.workspace-inspector__facts dd {
  display: grid;
  gap: 4px;
  margin: 0;
}

.workspace-inspector__facts dd span {
  color: var(--text-secondary);
}

.workspace-inspector__details summary {
  align-items: center;
  cursor: pointer;
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.workspace-inspector__details summary::marker {
  color: var(--text-tertiary);
}

.workspace-inspector__details em {
  background: color-mix(in srgb, var(--surface-secondary) 86%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-tertiary);
  font-size: 12px;
  font-style: normal;
  padding: 2px 8px;
}

.workspace-inspector__details p {
  padding-top: 8px;
}
</style>
