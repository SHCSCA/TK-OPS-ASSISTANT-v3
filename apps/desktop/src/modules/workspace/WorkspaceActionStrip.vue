<template>
  <section class="workspace-action-strip" aria-label="剪辑工作台行动提示">
    <div class="workspace-action-strip__item" data-tone="brand">
      <span class="material-symbols-outlined" aria-hidden="true">movie_edit</span>
      <div>
        <strong>{{ previewModeLabel }}</strong>
        <span>{{ previewDescription }}</span>
      </div>
    </div>

    <div class="workspace-action-strip__item" :data-tone="precheckTone">
      <span class="material-symbols-outlined" aria-hidden="true">rule_settings</span>
      <div>
        <strong>{{ precheckLabel }}</strong>
        <span>{{ precheckDescription }}</span>
      </div>
    </div>

    <div class="workspace-action-strip__item" :data-tone="historyTone">
      <span class="material-symbols-outlined" aria-hidden="true">history</span>
      <div>
        <strong>{{ historyLabel }}</strong>
        <span>{{ historyDescription }}</span>
      </div>
    </div>

    <div class="workspace-action-strip__next">
      <span class="workspace-action-strip__eyebrow">下一步</span>
      <strong>{{ nextStepTitle }}</strong>
      <span>{{ nextStepDescription }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { TimelinePrecheckDto } from "@/types/runtime";
import type { WorkspacePreviewContext } from "./workspacePreviewContext";
import type { WorkspaceExportReadiness } from "./workspaceExportReadiness";

const props = defineProps<{
  canRedo: boolean;
  canUndo: boolean;
  exportReadiness: WorkspaceExportReadiness;
  isGenerating: boolean;
  precheck: TimelinePrecheckDto | null;
  previewContext: WorkspacePreviewContext;
}>();

const previewModeLabel = computed(() => {
  switch (props.previewContext.previewMode) {
    case "media":
      return "真实素材预览";
    case "structure":
      return "结构预览";
    case "unavailable":
      return "媒体不可用";
    default:
      return "等待预览";
  }
});

const previewDescription = computed(() => {
  if (props.previewContext.previewMode === "media") return props.previewContext.mediaInfoText || "可播放源文件。";
  if (props.previewContext.runtimePreviewErrorMessage) return "预览同步需要重新检查。";
  return "按时间线播放头检查节奏。";
});

const precheckTone = computed(() => {
  if (!props.precheck) return "neutral";
  if (props.precheck.status === "blocked" || props.precheck.status === "error") return "danger";
  if (props.precheck.status === "warning") return "warning";
  return "success";
});

const precheckLabel = computed(() => {
  if (!props.precheck) return "尚未预检";
  if (props.exportReadiness.status === "precheck_required" && props.precheck.status === "ready") {
    return props.exportReadiness.title;
  }
  return props.precheck.message || props.exportReadiness.title;
});
const precheckDescription = computed(() => {
  if (props.exportReadiness.status === "missing_timeline") return "创建或汇入时间线后再检查。";
  if (props.exportReadiness.status === "ready") return "预检已匹配当前时间线。";
  return props.exportReadiness.description;
});

const historyTone = computed(() => (props.canUndo || props.canRedo ? "info" : "neutral"));
const historyLabel = computed(() => {
  if (props.canUndo) return "可撤销最近编辑";
  if (props.canRedo) return "可重做最近编辑";
  return "暂无撤销项";
});
const historyDescription = computed(() => {
  if (props.canUndo) return "删除、移动、裁剪等操作可回退。";
  if (props.canRedo) return "撤销后可以恢复刚才的编辑。";
  return "编辑时间线后会自动记录。";
});

const nextStepTitle = computed(() => {
  if (props.isGenerating) return "等待智能粗剪完成";
  switch (props.exportReadiness.status) {
    case "missing_timeline":
      return "创建或同步时间线";
    case "unsaved":
      return "先保存时间线";
    case "precheck_required":
      return "运行本地预检";
    case "precheck_blocked":
      return "处理预检问题";
    case "ready":
      return "准备渲染导出";
    default:
      return props.exportReadiness.title;
  }
});

const nextStepDescription = computed(() => {
  if (props.isGenerating) return "智能粗剪结果会先进入审阅，不会直接覆盖时间线。";
  switch (props.exportReadiness.status) {
    case "missing_timeline":
      return "让脚本、分镜、配音和字幕先进入同一条主时间线。";
    case "unsaved":
      return "保存后再运行预检，避免导出旧版本。";
    case "precheck_required":
      return props.exportReadiness.description;
    case "precheck_blocked":
      return props.exportReadiness.description;
    case "ready":
      return "导出中心会沿用当前项目和时间线。";
    default:
      return props.exportReadiness.description;
  }
});
</script>

<style scoped>
.workspace-action-strip {
  align-items: stretch;
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(3, minmax(0, 1fr)) minmax(260px, 1.15fr);
}

.workspace-action-strip__item,
.workspace-action-strip__next {
  background: color-mix(in srgb, var(--color-bg-surface) 92%, transparent);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  min-width: 0;
  padding: var(--space-3) var(--space-4);
}

.workspace-action-strip__item {
  align-items: center;
  display: flex;
  gap: var(--space-3);
}

.workspace-action-strip__item .material-symbols-outlined {
  color: var(--color-text-secondary);
  font-size: 20px;
}

.workspace-action-strip__item[data-tone="brand"] .material-symbols-outlined {
  color: var(--color-brand-primary);
}

.workspace-action-strip__item[data-tone="success"] .material-symbols-outlined {
  color: var(--color-status-success);
}

.workspace-action-strip__item[data-tone="warning"] .material-symbols-outlined {
  color: var(--color-status-warning);
}

.workspace-action-strip__item[data-tone="danger"] .material-symbols-outlined {
  color: var(--color-status-danger);
}

.workspace-action-strip__item[data-tone="info"] .material-symbols-outlined {
  color: var(--color-status-info);
}

.workspace-action-strip strong,
.workspace-action-strip span {
  display: block;
  min-width: 0;
}

.workspace-action-strip strong {
  color: var(--color-text-primary);
  font: var(--font-label);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-action-strip span {
  color: var(--color-text-secondary);
  font: var(--font-caption);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-action-strip__next {
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--color-brand-primary) 14%, transparent), transparent 72%),
    var(--color-bg-surface);
}

.workspace-action-strip__eyebrow {
  color: var(--color-brand-primary) !important;
  font-weight: 700 !important;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

@media (max-width: 1320px) {
  .workspace-action-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .workspace-action-strip {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
