<template>
  <section class="panel-shell" data-testid="subtitle-preview-stage">
    <div class="stage-copy">
      <span class="stage-copy__kicker">字幕校对台</span>
      <h2>{{ title }}</h2>
      <p>{{ stageCopy }}</p>
    </div>

    <div class="stage-meta">
      <span class="stage-meta__chip">{{ selectedTrack?.language ?? "zh-CN" }}</span>
      <span class="stage-meta__chip">{{ selectedTrack?.source ?? "script" }}</span>
      <span class="stage-meta__chip">{{ styleConfig.preset }}</span>
    </div>

    <div class="preview-frame" :class="{ 'preview-frame--busy': status === 'aligning' }">
      <div class="safe-area">
        <span class="preview-label">预览画面</span>
        <p class="subtitle-overlay" :style="overlayStyle">
          {{ activeSegment?.text ?? "选中字幕段后，这里会展示叠字效果。" }}
        </p>
      </div>
    </div>

    <div class="detail-surface">
      <div class="detail-surface__row">
        <strong>{{ statusLabel }}</strong>
        <span>{{ statusMessage }}</span>
      </div>
      <dl v-if="selectedTrack" class="detail-grid">
        <div>
          <dt>字幕来源</dt>
          <dd>{{ selectedTrack.source }}</dd>
        </div>
        <div>
          <dt>语言</dt>
          <dd>{{ selectedTrack.language }}</dd>
        </div>
        <div>
          <dt>创建时间</dt>
          <dd>{{ formatDate(selectedTrack.createdAt) }}</dd>
        </div>
        <div>
          <dt>轨道状态</dt>
          <dd>{{ selectedTrack.status }}</dd>
        </div>
      </dl>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { SubtitleAlignmentStatus } from "@/stores/subtitle-alignment";
import type { SubtitleSegmentDto, SubtitleStyleDto, SubtitleTrackDto } from "@/types/runtime";

const props = defineProps<{
  activeSegment: SubtitleSegmentDto | null;
  generationMessage: string | null;
  selectedTrack: SubtitleTrackDto | null;
  stateMessage: string;
  status: SubtitleAlignmentStatus;
  styleConfig: SubtitleStyleDto;
}>();

const title = computed(() => {
  if (props.status === "aligning") return "正在生成字幕草稿。";
  if (props.status === "blocked") return "字幕对齐能力被阻断。";
  if (props.status === "error") return "字幕工作台需要处理错误。";
  if (!props.selectedTrack) return "等待真实字幕版本。";
  return "脚本文本和字幕段已经接通。";
});

const stageCopy = computed(() => {
  const segmentText = props.activeSegment?.text ?? "选择字幕段后，这里会显示当前叠字上下文。";
  const trackText = props.selectedTrack
    ? `${props.selectedTrack.source} · ${props.selectedTrack.language}`
    : "当前没有选中的字幕版本。";
  return `${segmentText} 当前轨道：${trackText}`;
});

const statusLabel = computed(() => {
  if (props.status === "loading") return "读取中";
  if (props.status === "aligning") return "对齐中";
  if (props.status === "blocked") return "阻断";
  if (props.status === "saving") return "保存中";
  if (props.status === "error") return "错误";
  if (!props.selectedTrack) return "空态";
  return "可用";
});

const statusMessage = computed(() => {
  if (props.status === "loading") return "正在读取脚本文本、字幕版本和样式草稿。";
  if (props.status === "aligning") return "正在把脚本文本整理为字幕草稿，不会提前写入假时间码。";
  if (props.status === "blocked") {
    return props.generationMessage || props.stateMessage;
  }
  if (props.status === "saving") return "正在保存字幕段和样式校正。";
  if (props.status === "error") return props.stateMessage;
  if (!props.selectedTrack) {
    return "真实时间码尚未生成，先创建字幕版本。";
  }
  return props.stateMessage;
});

const overlayStyle = computed(() => ({
  background: props.styleConfig.background,
  color: props.styleConfig.textColor,
  fontSize: `${props.styleConfig.fontSize}px`,
  top:
    props.styleConfig.position === "top"
      ? "16%"
      : props.styleConfig.position === "center"
        ? "50%"
        : "auto",
  bottom: props.styleConfig.position === "bottom" ? "14%" : "auto",
  transform:
    props.styleConfig.position === "center" ? "translate(-50%, -50%)" : "translateX(-50%)"
}));

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    hour12: false,
    timeStyle: "short"
  }).format(date);
}
</script>

<style scoped>
.panel-shell {
  display: grid;
  gap: 16px;
  min-height: 0;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 9%, transparent), transparent 42%),
    var(--bg-elevated);
  padding: 24px;
  overflow: hidden;
}

.stage-copy {
  display: grid;
  gap: 8px;
}

.stage-copy__kicker {
  color: var(--brand-primary);
  font-size: 13px;
  font-weight: 800;
}

h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 28px;
  line-height: 1.2;
}

.stage-copy p {
  margin: 0;
  max-width: 760px;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.75;
}

.stage-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stage-meta__chip {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.preview-frame {
  position: relative;
  overflow: hidden;
  aspect-ratio: 16 / 9;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background:
    linear-gradient(160deg, rgba(0, 0, 0, 0.96), rgba(22, 28, 28, 0.98)),
    #050808;
}

.preview-frame--busy::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    color-mix(in srgb, var(--brand-primary) 24%, transparent),
    transparent
  );
  content: "";
  animation: subtitle-scan 1.2s ease-in-out infinite;
}

.safe-area {
  position: absolute;
  inset: 8%;
  border: 1px dashed rgba(255, 255, 255, 0.18);
  border-radius: 8px;
}

.preview-label {
  position: absolute;
  top: 12px;
  left: 12px;
  color: rgba(255, 255, 255, 0.54);
  font-size: 12px;
}

.subtitle-overlay {
  position: absolute;
  left: 50%;
  max-width: min(88%, 760px);
  margin: 0;
  padding: 5px 18px;
  border-radius: 6px;
  line-height: 1.35;
  text-align: center;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.85);
}

.detail-surface {
  display: grid;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
}

.detail-surface__row {
  display: grid;
  gap: 4px;
}

.detail-surface__row strong {
  color: var(--text-primary);
  font-size: 14px;
}

.detail-surface__row span {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-grid div {
  display: grid;
  gap: 4px;
}

.detail-grid dt {
  color: var(--text-tertiary);
  font-size: 12px;
}

.detail-grid dd {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}

@keyframes subtitle-scan {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(100%);
  }
}

/* Reduced Motion 降级由 :root[data-reduced-motion="true"] 的 --motion-* 变量统一控制 */
</style>
