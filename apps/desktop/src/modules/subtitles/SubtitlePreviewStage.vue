<template>
  <section class="subtitle-preview-stage" data-testid="subtitle-preview-stage">
    <div class="stage-kicker">字幕校对台</div>
    <h2>{{ title }}</h2>
    <p class="stage-copy">{{ stageCopy }}</p>

    <div class="preview-frame" :class="{ 'preview-frame--busy': status === 'aligning' }">
      <div class="safe-area">
        <span class="preview-label">预览画面</span>
        <p class="subtitle-overlay" :style="overlayStyle">
          {{ activeSegment?.text ?? "选中字幕段后在这里预览叠字效果" }}
        </p>
      </div>
    </div>

    <div class="stage-status" :class="`stage-status--${status}`">
      <strong>{{ statusLabel }}</strong>
      <span>{{ generationMessage || statusMessage }}</span>
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
  status: SubtitleAlignmentStatus;
  styleConfig: SubtitleStyleDto;
}>();

const title = computed(() => {
  if (props.status === "aligning") return "正在创建字幕草稿";
  if (props.status === "blocked") return "待配置 Provider";
  return "校对字幕段落和叠字位置";
});

const stageCopy = computed(() => {
  if (props.selectedTrack) {
    return `当前版本 ${props.selectedTrack.id}，来源 ${props.selectedTrack.source}，语言 ${props.selectedTrack.language}。`;
  }
  return "读取项目脚本后，可以生成真实字幕草稿并逐段校正。";
});

const statusLabel = computed(() => {
  if (props.status === "loading") return "读取中";
  if (props.status === "aligning") return "生成中";
  if (props.status === "blocked") return "待配置 Provider";
  if (props.status === "saving") return "保存中";
  if (props.status === "error") return "需要处理";
  return "准备就绪";
});

const statusMessage = computed(() => {
  if (props.status === "aligning") return "正在把脚本文本整理为字幕轨草稿记录。";
  if (props.status === "blocked") return "尚未配置可用字幕对齐 Provider，字幕草稿已保存，可继续人工校对。";
  if (props.status === "saving") return "正在保存字幕段落和样式校正。";
  if (props.status === "error") return "请根据页面提示修正后重试。";
  return "字幕预览仅展示叠字效果，不伪造真实视频播放或精准时间码。";
});

const overlayStyle = computed(() => ({
  background: props.styleConfig.background,
  color: props.styleConfig.textColor,
  fontSize: `${props.styleConfig.fontSize}px`,
  top: props.styleConfig.position === "top" ? "16%" : props.styleConfig.position === "center" ? "50%" : "auto",
  bottom: props.styleConfig.position === "bottom" ? "14%" : "auto",
  transform: props.styleConfig.position === "center" ? "translate(-50%, -50%)" : "translateX(-50%)"
}));
</script>

<style scoped>
.subtitle-preview-stage {
  display: grid;
  align-content: center;
  gap: 18px;
  min-height: 0;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 9%, transparent), transparent 42%),
    var(--bg-elevated);
  padding: 24px;
  overflow: hidden;
}

.stage-kicker {
  color: var(--brand-primary);
  font-size: 13px;
  font-weight: 900;
}

h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 28px;
  line-height: 1.2;
}

.stage-copy {
  margin: 0;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.75;
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
  background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--brand-primary) 24%, transparent), transparent);
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

.stage-status {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 13px;
}

.stage-status strong {
  color: var(--text-primary);
}

.stage-status--blocked strong {
  color: var(--warning, #b7791f);
}

.stage-status--error strong {
  color: var(--danger, #dc2626);
}

@keyframes subtitle-scan {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(100%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .preview-frame--busy::after {
    animation: none;
  }
}
</style>
