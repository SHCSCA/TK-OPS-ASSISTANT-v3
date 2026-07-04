<template>
  <section
    class="workspace-timeline-toolbar"
    data-testid="workspace-timeline-toolbar"
    aria-label="时间线基础工具"
  >
    <div class="workspace-timeline-toolbar__status">
      <strong>基础工具</strong>
      <span>{{ statusLabel }}</span>
    </div>

    <div class="workspace-timeline-toolbar__tools" aria-label="时间线工具状态">
      <button
        v-for="tool in tools"
        :key="tool.id"
        class="workspace-timeline-toolbar__button"
        :class="{ 'workspace-timeline-toolbar__button--active': tool.active }"
        :data-testid="`workspace-tool-${tool.id}`"
        :title="tool.label"
        type="button"
        :disabled="tool.disabled"
        @click="handleToolClick(tool.id)"
      >
        <span class="workspace-timeline-toolbar__icon" :data-icon="tool.icon" aria-hidden="true"></span>
        <span class="workspace-timeline-toolbar__label">{{ tool.label }}</span>
      </button>

      <div
        class="workspace-timeline-toolbar__zoom"
        :class="{ 'workspace-timeline-toolbar__zoom--disabled': props.disabled }"
        data-testid="workspace-timeline-zoom"
        aria-label="时间线视图缩放状态"
        :aria-disabled="props.disabled || undefined"
      >
        <button
          class="workspace-timeline-toolbar__zoom-button"
          data-testid="workspace-timeline-zoom-out"
          title="缩小时间线"
          type="button"
          :disabled="props.disabled || !previousZoomPercent"
          @click="handleZoomOut"
        >
          <span aria-hidden="true">-</span>
        </button>
        <input
          class="workspace-timeline-toolbar__zoom-slider"
          data-testid="workspace-timeline-zoom-slider"
          aria-label="时间线缩放比例"
          list="workspace-timeline-zoom-steps"
          max="300"
          min="50"
          type="range"
          :disabled="props.disabled"
          :value="safeZoomPercent"
          @input="handleZoomSlider"
        >
        <datalist id="workspace-timeline-zoom-steps">
          <option v-for="step in zoomSteps" :key="step" :value="step" />
        </datalist>
        <button
          class="workspace-timeline-toolbar__zoom-button"
          data-testid="workspace-timeline-zoom-in"
          title="放大时间线"
          type="button"
          :disabled="props.disabled || !nextZoomPercent"
          @click="handleZoomIn"
        >
          <span aria-hidden="true">+</span>
        </button>
        <span
          class="workspace-timeline-toolbar__zoom-mark"
          data-testid="workspace-timeline-zoom-value"
          data-default-label="100%"
        >
          {{ safeZoomPercent }}%
        </span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import {
  TIMELINE_ZOOM_STEPS,
  normalizeTimelineZoomPercent,
  type TimelineZoomPercent
} from "./workspaceTimelineGeometry";

const props = withDefaults(defineProps<{
  statusLabel: string;
  disabled?: boolean;
  canSplit?: boolean;
  canDelete?: boolean;
  canMove?: boolean;
  canMoveLeft?: boolean;
  canMoveRight?: boolean;
  canTrim?: boolean;
  canRedo?: boolean;
  canUndo?: boolean;
  zoomPercent?: number;
}>(), {
  disabled: false,
  canSplit: false,
  canDelete: false,
  canMove: false,
  canMoveLeft: undefined,
  canMoveRight: undefined,
  canTrim: false,
  canRedo: false,
  canUndo: false,
  zoomPercent: 100
});

const emit = defineEmits<{
  delete: [];
  move: [deltaMs: number];
  split: [];
  trim: [edge: "left" | "right", deltaMs: number];
  redo: [];
  undo: [];
  "zoom-change": [zoomPercent: TimelineZoomPercent];
}>();

type WorkspaceTimelineToolId =
  | "select"
  | "undo"
  | "redo"
  | "move-left"
  | "move-right"
  | "trim-left"
  | "trim-right"
  | "split"
  | "delete"
  | "snap";

const tools = computed(() => [
  { id: "select", label: "选择", icon: "select", active: true, disabled: true },
  { id: "undo", label: "撤销", icon: "undo", active: false, disabled: props.disabled || !props.canUndo },
  { id: "redo", label: "重做", icon: "redo", active: false, disabled: props.disabled || !props.canRedo },
  { id: "move-left", label: "左移", icon: "move-left", active: false, disabled: props.disabled || !(props.canMoveLeft ?? props.canMove) },
  { id: "move-right", label: "右移", icon: "move-right", active: false, disabled: props.disabled || !(props.canMoveRight ?? props.canMove) },
  { id: "trim-left", label: "左裁", icon: "trim-left", active: false, disabled: props.disabled || !props.canTrim },
  { id: "trim-right", label: "右裁", icon: "trim-right", active: false, disabled: props.disabled || !props.canTrim },
  { id: "split", label: "分割", icon: "split", active: false, disabled: props.disabled || !props.canSplit },
  { id: "delete", label: "删除", icon: "delete", active: false, disabled: props.disabled || !props.canDelete },
  { id: "snap", label: "磁吸", icon: "snap", active: true, disabled: true }
] as const);

const zoomSteps = TIMELINE_ZOOM_STEPS;
const safeZoomPercent = computed(() => normalizeTimelineZoomPercent(props.zoomPercent));
const currentZoomIndex = computed(() => zoomSteps.indexOf(safeZoomPercent.value));
const previousZoomPercent = computed(() => {
  const previous = zoomSteps[currentZoomIndex.value - 1];
  return previous ?? null;
});
const nextZoomPercent = computed(() => {
  const next = zoomSteps[currentZoomIndex.value + 1];
  return next ?? null;
});

function handleToolClick(toolId: WorkspaceTimelineToolId): void {
  if (toolId === "undo") {
    emit("undo");
    return;
  }
  if (toolId === "redo") {
    emit("redo");
    return;
  }
  if (toolId === "move-left") {
    emit("move", -500);
    return;
  }
  if (toolId === "move-right") {
    emit("move", 500);
    return;
  }
  if (toolId === "trim-left") {
    emit("trim", "left", 500);
    return;
  }
  if (toolId === "trim-right") {
    emit("trim", "right", -500);
    return;
  }
  if (toolId === "split") {
    emit("split");
    return;
  }
  if (toolId === "delete") {
    emit("delete");
  }
}

function handleZoomOut(): void {
  if (previousZoomPercent.value) emit("zoom-change", previousZoomPercent.value);
}

function handleZoomIn(): void {
  if (nextZoomPercent.value) emit("zoom-change", nextZoomPercent.value);
}

function handleZoomSlider(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  const value = Number(target?.value);

  emit("zoom-change", normalizeTimelineZoomPercent(value));
}
</script>

<style scoped>
.workspace-timeline-toolbar {
  align-items: center;
  background:
    linear-gradient(135deg, rgb(35 43 56 / 92%), rgb(15 20 29 / 96%)),
    var(--color-bg-surface);
  border: 1px solid rgb(117 139 166 / 24%);
  border-radius: 8px;
  box-shadow: 0 16px 40px rgb(0 0 0 / 22%);
  color: #dbe7f7;
  display: flex;
  gap: var(--space-3);
  justify-content: space-between;
  min-width: 0;
  padding: 8px 12px;
}

.workspace-timeline-toolbar__status {
  align-items: baseline;
  display: flex;
  gap: var(--space-3);
  min-width: 0;
}

.workspace-timeline-toolbar__status strong {
  color: #f7fbff;
  font: var(--font-title-sm);
  white-space: nowrap;
}

.workspace-timeline-toolbar__status span {
  color: rgb(219 231 247 / 68%);
  font: var(--font-body-sm);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-timeline-toolbar__tools {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
  min-width: 0;
}

.workspace-timeline-toolbar__button {
  align-items: center;
  background: rgb(255 255 255 / 6%);
  border: 1px solid rgb(219 231 247 / 12%);
  border-radius: 8px;
  color: rgb(219 231 247 / 72%);
  display: inline-flex;
  gap: 6px;
  height: 30px;
  justify-content: center;
  min-width: 70px;
  padding: 0 10px;
}

.workspace-timeline-toolbar__button:disabled {
  cursor: not-allowed;
  opacity: 1;
}

.workspace-timeline-toolbar__button--active {
  background: rgb(82 170 255 / 18%);
  border-color: rgb(98 183 255 / 58%);
  box-shadow:
    inset 0 0 0 1px rgb(255 255 255 / 8%),
    0 0 18px rgb(69 162 255 / 18%);
  color: #f7fbff;
}

.workspace-timeline-toolbar__icon {
  display: inline-block;
  height: 16px;
  position: relative;
  width: 16px;
}

.workspace-timeline-toolbar__icon::before,
.workspace-timeline-toolbar__icon::after {
  content: "";
  position: absolute;
}

.workspace-timeline-toolbar__icon[data-icon="select"]::before {
  border: solid currentColor;
  border-width: 0 2px 2px 0;
  height: 10px;
  left: 5px;
  top: 1px;
  transform: rotate(-25deg);
  width: 5px;
}

.workspace-timeline-toolbar__icon[data-icon="select"]::after {
  background: currentColor;
  height: 6px;
  left: 9px;
  top: 9px;
  transform: rotate(-35deg);
  width: 2px;
}

.workspace-timeline-toolbar__icon[data-icon="move-left"]::before,
.workspace-timeline-toolbar__icon[data-icon="move-left"]::after,
.workspace-timeline-toolbar__icon[data-icon="move-right"]::before,
.workspace-timeline-toolbar__icon[data-icon="move-right"]::after,
.workspace-timeline-toolbar__icon[data-icon="undo"]::after,
.workspace-timeline-toolbar__icon[data-icon="redo"]::after {
  background: currentColor;
  border-radius: 99px;
  left: 3px;
  top: 7px;
}

.workspace-timeline-toolbar__icon[data-icon="move-left"]::before,
.workspace-timeline-toolbar__icon[data-icon="move-right"]::before {
  height: 2px;
  width: 10px;
}

.workspace-timeline-toolbar__icon[data-icon="move-left"]::after,
.workspace-timeline-toolbar__icon[data-icon="move-right"]::after {
  background: transparent;
  border: solid currentColor;
  border-width: 0 0 2px 2px;
  height: 6px;
  left: 3px;
  top: 5px;
  transform: rotate(45deg);
  width: 6px;
}

.workspace-timeline-toolbar__icon[data-icon="move-right"]::after {
  border-width: 2px 2px 0 0;
  left: 7px;
}

.workspace-timeline-toolbar__icon[data-icon="undo"]::before,
.workspace-timeline-toolbar__icon[data-icon="redo"]::before {
  border: 2px solid currentColor;
  border-left-color: transparent;
  border-radius: 999px;
  height: 10px;
  left: 3px;
  top: 3px;
  transform: rotate(-35deg);
  width: 10px;
}

.workspace-timeline-toolbar__icon[data-icon="undo"]::after {
  background: transparent;
  border: solid currentColor;
  border-width: 0 0 2px 2px;
  height: 5px;
  left: 2px;
  top: 4px;
  transform: rotate(45deg);
  width: 5px;
}

.workspace-timeline-toolbar__icon[data-icon="redo"]::before {
  border-left-color: currentColor;
  border-right-color: transparent;
  transform: rotate(35deg);
}

.workspace-timeline-toolbar__icon[data-icon="redo"]::after {
  background: transparent;
  border: solid currentColor;
  border-width: 0 2px 2px 0;
  height: 5px;
  left: 9px;
  top: 4px;
  transform: rotate(-45deg);
  width: 5px;
}

.workspace-timeline-toolbar__icon[data-icon="trim-left"]::before,
.workspace-timeline-toolbar__icon[data-icon="trim-right"]::before {
  background: currentColor;
  border-radius: 99px;
  height: 14px;
  left: 4px;
  top: 1px;
  width: 2px;
}

.workspace-timeline-toolbar__icon[data-icon="trim-left"]::after,
.workspace-timeline-toolbar__icon[data-icon="trim-right"]::after {
  border: 2px solid currentColor;
  border-radius: 3px;
  height: 10px;
  left: 7px;
  top: 3px;
  width: 6px;
}

.workspace-timeline-toolbar__icon[data-icon="trim-right"]::before {
  left: 10px;
}

.workspace-timeline-toolbar__icon[data-icon="trim-right"]::after {
  left: 3px;
}

.workspace-timeline-toolbar__icon[data-icon="split"]::before,
.workspace-timeline-toolbar__icon[data-icon="split"]::after {
  background: currentColor;
  border-radius: 99px;
  height: 14px;
  left: 7px;
  top: 1px;
  width: 2px;
}

.workspace-timeline-toolbar__icon[data-icon="split"]::before {
  transform: rotate(42deg);
}

.workspace-timeline-toolbar__icon[data-icon="split"]::after {
  transform: rotate(-42deg);
}

.workspace-timeline-toolbar__icon[data-icon="delete"]::before {
  border: 2px solid currentColor;
  border-radius: 2px;
  height: 9px;
  left: 4px;
  top: 5px;
  width: 8px;
}

.workspace-timeline-toolbar__icon[data-icon="delete"]::after {
  background: currentColor;
  border-radius: 99px;
  height: 2px;
  left: 3px;
  top: 2px;
  width: 10px;
}

.workspace-timeline-toolbar__icon[data-icon="snap"]::before {
  border: 2px solid currentColor;
  border-bottom: 0;
  border-radius: 7px 7px 0 0;
  height: 9px;
  left: 3px;
  top: 3px;
  width: 10px;
}

.workspace-timeline-toolbar__icon[data-icon="snap"]::after {
  background: currentColor;
  border-radius: 99px;
  height: 3px;
  left: 3px;
  top: 12px;
  width: 3px;
  box-shadow: 7px 0 0 currentColor;
}

.workspace-timeline-toolbar__label {
  font: var(--font-body-sm);
}

.workspace-timeline-toolbar__zoom {
  align-items: center;
  background: rgb(255 255 255 / 5%);
  border: 1px solid rgb(219 231 247 / 10%);
  border-radius: 8px;
  display: inline-flex;
  gap: 6px;
  height: 30px;
  padding: 0 8px;
}

.workspace-timeline-toolbar__zoom--disabled {
  opacity: 0.74;
}

.workspace-timeline-toolbar__zoom-button {
  align-items: center;
  background: rgb(255 255 255 / 7%);
  border: 1px solid rgb(219 231 247 / 12%);
  border-radius: 6px;
  color: rgb(219 231 247 / 78%);
  display: inline-flex;
  height: 22px;
  justify-content: center;
  padding: 0;
  width: 22px;
}

.workspace-timeline-toolbar__zoom-button:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.workspace-timeline-toolbar__zoom-mark {
  color: rgb(219 231 247 / 58%);
  font: var(--font-body-sm);
  white-space: nowrap;
}

.workspace-timeline-toolbar__zoom-slider {
  accent-color: #62b7ff;
  cursor: pointer;
  height: 22px;
  width: 92px;
}

.workspace-timeline-toolbar__zoom-slider:disabled {
  cursor: not-allowed;
}

@container editing-workspace (max-width: 1160px) {
  .workspace-timeline-toolbar {
    align-items: center;
    display: grid;
    gap: 8px;
    grid-template-columns: auto minmax(0, 1fr);
    overflow: hidden;
    padding: 6px 10px;
  }

  .workspace-timeline-toolbar__status span {
    display: none;
  }

  .workspace-timeline-toolbar__tools {
    flex-wrap: nowrap;
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 2px;
  }

  .workspace-timeline-toolbar__button,
  .workspace-timeline-toolbar__zoom {
    flex: 0 0 auto;
  }
}
</style>
