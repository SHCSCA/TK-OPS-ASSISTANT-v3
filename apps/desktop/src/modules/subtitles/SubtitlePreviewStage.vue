<template>
  <section class="panel-shell" data-testid="subtitle-preview-stage">
    <div v-if="status === 'aligning'" class="ai-flow-bar" />
    <div
      ref="frameRef"
      class="preview-frame"
      data-ratio="9:16"
      data-testid="subtitle-preview-frame"
      :class="{ 'preview-frame--busy': status === 'aligning' }"
    >
      <div class="safe-area">
        <span class="preview-label">预览画面</span>
        <p
          class="subtitle-overlay"
          data-testid="subtitle-overlay"
          :class="{ 'subtitle-overlay--dragging': isDragging }"
          :style="overlayStyle"
          @pointerdown="handlePointerDown"
        >
          {{ activeSegment?.text ?? "选中字幕段后，这里会展示叠字效果。" }}
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";

import type { SubtitleAlignmentStatus } from "@/stores/subtitle-alignment";
import type { SubtitleSegmentDto, SubtitleStyleDto } from "@/types/runtime";

const props = defineProps<{
  activeSegment: SubtitleSegmentDto | null;
  status: SubtitleAlignmentStatus;
  styleConfig: SubtitleStyleDto;
}>();

const emit = defineEmits<{
  "update-style": [patch: Partial<SubtitleStyleDto>];
}>();

const frameRef = ref<HTMLElement | null>(null);
const isDragging = ref(false);

const basePositionPercent = computed(() => {
  if (props.styleConfig.position === "top") return 22;
  if (props.styleConfig.position === "center") return 50;
  return 78;
});

const overlayStyle = computed(() => ({
  background: props.styleConfig.background,
  color: props.styleConfig.textColor,
  fontSize: `${props.styleConfig.fontSize}px`,
  left: `${clamp(50 + (props.styleConfig.offsetX ?? 0), 8, 92)}%`,
  lineHeight: String(props.styleConfig.lineHeight ?? 1.35),
  top: `${clamp(basePositionPercent.value + (props.styleConfig.offsetY ?? 0), 8, 92)}%`,
  transform: "translate(-50%, -50%)",
  width: `${clamp(props.styleConfig.boxWidth ?? 88, 36, 96)}%`
}));

onBeforeUnmount(() => {
  stopDragging();
});

function handlePointerDown(event: PointerEvent): void {
  event.preventDefault();
  isDragging.value = true;
  (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
  updatePositionFromPointer(event);
  window.addEventListener("pointermove", handlePointerMove);
  window.addEventListener("pointerup", handlePointerUp, { once: true });
}

function handlePointerMove(event: PointerEvent): void {
  if (!isDragging.value) {
    return;
  }
  updatePositionFromPointer(event);
}

function handlePointerUp(event: PointerEvent): void {
  updatePositionFromPointer(event);
  stopDragging();
}

function updatePositionFromPointer(event: PointerEvent): void {
  const rect = frameRef.value?.getBoundingClientRect();
  if (!rect || rect.width <= 0 || rect.height <= 0) {
    return;
  }

  const xPercent = ((event.clientX - rect.left) / rect.width) * 100;
  const yPercent = ((event.clientY - rect.top) / rect.height) * 100;
  emit("update-style", {
    offsetX: Math.round(clamp(xPercent - 50, -45, 45)),
    offsetY: Math.round(clamp(yPercent - basePositionPercent.value, -45, 45))
  });
}

function stopDragging(): void {
  isDragging.value = false;
  window.removeEventListener("pointermove", handlePointerMove);
  window.removeEventListener("pointerup", handlePointerUp);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
</script>

<style scoped>
.panel-shell {
  display: grid;
  gap: 16px;
  place-items: center;
  min-height: 0;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 9%, transparent), transparent 42%),
    var(--bg-elevated);
  padding: 24px;
  overflow: hidden;
  position: relative;
}

.ai-flow-bar {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--gradient-ai-primary);
  background-size: 200% 200%;
  animation: ai-flow var(--motion-flow) linear infinite;
  z-index: 10;
}

.preview-frame {
  position: relative;
  overflow: hidden;
  width: min(100%, 360px);
  aspect-ratio: 9 / 16;
  border: 1px solid var(--border-subtle);
  border-radius: 28px;
  background:
    radial-gradient(circle at 50% 18%, rgba(34, 42, 42, 0.88), transparent 34%),
    linear-gradient(160deg, rgba(0, 0, 0, 0.98), rgba(13, 18, 18, 0.98)),
    #050808;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.28);
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
  animation: subtitle-scan var(--motion-pulse) ease-in-out infinite;
}

.safe-area {
  position: absolute;
  inset: 7% 8%;
  border: 1px dashed rgba(255, 255, 255, 0.18);
  border-radius: 22px;
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
  margin: 0;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: grab;
  text-align: center;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.85);
  touch-action: none;
  user-select: none;
}

.subtitle-overlay--dragging {
  cursor: grabbing;
}

@keyframes subtitle-scan {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(100%);
  }
}

/* 动效降级由 :root[data-reduced-motion="true"] 的 --motion-* 变量统一控制 */
</style>
