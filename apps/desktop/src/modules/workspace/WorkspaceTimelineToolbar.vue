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
        disabled
      >
        <span class="workspace-timeline-toolbar__icon" :data-icon="tool.icon" aria-hidden="true"></span>
        <span class="workspace-timeline-toolbar__label">{{ tool.label }}</span>
      </button>

      <div class="workspace-timeline-toolbar__zoom" aria-label="缩放视觉状态">
        <span class="workspace-timeline-toolbar__zoom-mark">-</span>
        <span class="workspace-timeline-toolbar__zoom-track">
          <span class="workspace-timeline-toolbar__zoom-fill"></span>
        </span>
        <span class="workspace-timeline-toolbar__zoom-mark">+</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  statusLabel: string;
}>();

const tools = [
  { id: "select", label: "选择", icon: "select", active: true },
  { id: "move", label: "移动", icon: "move", active: false },
  { id: "split", label: "分割", icon: "split", active: false },
  { id: "delete", label: "删除", icon: "delete", active: false },
  { id: "snap", label: "磁吸", icon: "snap", active: true }
] as const;
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

.workspace-timeline-toolbar__icon[data-icon="move"]::before,
.workspace-timeline-toolbar__icon[data-icon="move"]::after {
  background: currentColor;
  border-radius: 99px;
  left: 2px;
  top: 7px;
}

.workspace-timeline-toolbar__icon[data-icon="move"]::before {
  height: 2px;
  width: 12px;
}

.workspace-timeline-toolbar__icon[data-icon="move"]::after {
  height: 12px;
  left: 7px;
  top: 2px;
  width: 2px;
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
  gap: 8px;
  height: 30px;
  padding: 0 10px;
}

.workspace-timeline-toolbar__zoom-mark {
  color: rgb(219 231 247 / 58%);
  font: var(--font-body-sm);
}

.workspace-timeline-toolbar__zoom-track {
  background: rgb(219 231 247 / 16%);
  border-radius: 99px;
  display: inline-flex;
  height: 4px;
  overflow: hidden;
  width: 62px;
}

.workspace-timeline-toolbar__zoom-fill {
  background: linear-gradient(90deg, #62b7ff, #9ed2ff);
  border-radius: inherit;
  width: 58%;
}

@container editing-workspace (max-width: 860px) {
  .workspace-timeline-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .workspace-timeline-toolbar__tools {
    justify-content: flex-start;
  }
}
</style>
