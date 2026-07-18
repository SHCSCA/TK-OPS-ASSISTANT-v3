<template>
  <section class="workspace-ai-bar" aria-label="AI 工具条">
    <div class="workspace-ai-bar__copy">
      <span class="workspace-ai-bar__eyebrow">AI 工具条</span>
      <strong>{{ title }}</strong>
      <p>{{ description }}</p>
    </div>

    <div class="workspace-ai-bar__actions">
      <button
        class="workspace-ai-bar__button workspace-ai-bar__button--ai"
        data-testid="workspace-magic-cut-button"
        type="button"
        :disabled="magicCutDisabled"
        @click="$emit('magic-cut')"
      >
        <span class="material-symbols-outlined">auto_fix_high</span>
        智能粗剪
      </button>
      <button class="workspace-ai-bar__button workspace-ai-bar__button--ghost" type="button" disabled>
        <span class="material-symbols-outlined">record_voice_over</span>
        AI 替换旁白
      </button>
      <button class="workspace-ai-bar__button workspace-ai-bar__button--ghost" type="button" disabled>
        <span class="material-symbols-outlined">subtitles</span>
        AI 重对齐字幕
      </button>
    </div>

    <div class="workspace-ai-bar__status">
      <span class="workspace-ai-bar__pill">
        {{ statusLabel }}
      </span>
      <span class="workspace-ai-bar__pill workspace-ai-bar__pill--note">
        {{ note }}
      </span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { EditingWorkspaceStatus } from "@/stores/editing-workspace";
import type { WorkspaceTimelineClipDto } from "@/types/runtime";

const props = defineProps<{
  blockedMessage: string | null;
  hasTimeline: boolean;
  selectedClip: WorkspaceTimelineClipDto | null;
  status: EditingWorkspaceStatus;
}>();

defineEmits<{
  "magic-cut": [];
}>();

const isBusy = computed(() => props.status === "loading" || props.status === "saving");
const magicCutDisabled = computed(() => isBusy.value || !props.hasTimeline);
const title = computed(() => {
  if (props.selectedClip) return `当前选择：${props.selectedClip.label}`;
  if (props.hasTimeline) return "时间线草稿已接入";
  return "等待时间线草稿";
});
const description = computed(() => {
  if (!props.hasTimeline) return "先创建时间线草稿，智能粗剪会保持可恢复等待。";
  if (props.selectedClip) return `片段状态：${props.selectedClip.status}，智能粗剪不会伪造结果。`;
  return "当前只开放真实智能粗剪入口，能力未就绪时会显示可恢复原因。";
});
const statusLabel = computed(() => {
  if (props.status === "blocked") return "已阻断";
  if (isBusy.value) return "处理中";
  if (!props.hasTimeline) return "等待时间线";
  return "可用";
});
const note = computed(() => {
  if (props.blockedMessage) return props.blockedMessage;
  if (!props.hasTimeline) return "等待时间线草稿后可执行智能粗剪。";
  return "智能粗剪会先生成建议，审阅确认后再应用到时间线。";
});
</script>

<style scoped>
.workspace-ai-bar {
  align-items: center;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 12%, transparent), transparent 60%),
    color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 20px;
  box-shadow: var(--shadow-sm);
  display: grid;
  gap: 14px;
  padding: 18px;
}

.workspace-ai-bar__copy {
  display: grid;
  gap: 6px;
}

.workspace-ai-bar__copy p {
  color: var(--text-secondary);
  margin: 0;
}

.workspace-ai-bar__eyebrow {
  color: var(--text-tertiary);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.workspace-ai-bar__actions,
.workspace-ai-bar__status {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.workspace-ai-bar__button {
  align-items: center;
  border: 1px solid transparent;
  border-radius: 8px;
  display: inline-flex;
  gap: 8px;
  height: 38px;
  padding: 0 14px;
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
  will-change: transform;
}

.workspace-ai-bar__button:not(:disabled):active {
  transform: scale(0.95);
}

.workspace-ai-bar__button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.workspace-ai-bar__button--ai {
  background: var(--gradient-ai-primary);
  background-size: 200% 200%;
  animation: ai-shimmer var(--motion-flow) ease infinite;
  color: #fff;
  border: none;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--brand-primary) 20%, transparent);
}

.workspace-ai-bar__button--ai:not(:disabled):hover {
  box-shadow: 0 6px 16px color-mix(in srgb, var(--brand-primary) 32%, transparent);
  transform: translateY(-1px);
}

@keyframes ai-shimmer {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.workspace-ai-bar__button--ghost {
  background: transparent;
  border-color: var(--border-default);
  color: var(--text-primary);
}

.workspace-ai-bar__button--ghost:not(:disabled):hover {
  background: var(--surface-tertiary);
  border-color: var(--text-tertiary);
}

.workspace-ai-bar__pill {
  background: color-mix(in srgb, var(--surface-tertiary) 94%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 999px;
  color: var(--text-secondary);
  font-size: 12px;
  padding: 6px 12px;
}

.workspace-ai-bar__pill--note {
  color: var(--text-primary);
}
</style>
