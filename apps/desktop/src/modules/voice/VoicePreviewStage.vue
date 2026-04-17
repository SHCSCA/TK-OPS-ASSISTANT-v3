<template>
  <section class="panel-shell" data-testid="voice-preview-stage">
    <div class="stage-copy">
      <span class="stage-copy__kicker">配音导演台</span>
      <h2>{{ title }}</h2>
      <p>{{ stageCopy }}</p>
    </div>

    <div class="stage-meta">
      <span class="stage-meta__chip">
        {{ selectedProfile?.displayName ?? "未选音色" }}
      </span>
      <span class="stage-meta__chip">
        {{ selectedTrack?.status ?? "未生成" }}
      </span>
      <span class="stage-meta__chip">
        {{ selectedTrack?.segments.length ?? 0 }} 段配音片段
      </span>
    </div>

    <div class="wave-stage" :class="{ 'wave-stage--busy': status === 'generating' }">
      <span
        v-for="bar in bars"
        :key="bar.index"
        class="wave-bar"
        :style="{ height: `${bar.height}px` }"
      />
    </div>

    <div class="detail-surface">
      <div class="detail-surface__row">
        <strong>{{ statusLabel }}</strong>
        <span>{{ statusMessage }}</span>
      </div>
      <dl v-if="selectedTrack" class="detail-grid">
        <div>
          <dt>版本来源</dt>
          <dd>{{ selectedTrack.source }}</dd>
        </div>
        <div>
          <dt>Provider</dt>
          <dd>{{ selectedTrack.provider ?? "pending_provider" }}</dd>
        </div>
        <div>
          <dt>创建时间</dt>
          <dd>{{ formatDate(selectedTrack.createdAt) }}</dd>
        </div>
        <div>
          <dt>文件路径</dt>
          <dd>{{ selectedTrack.filePath ?? "未生成真实音频" }}</dd>
        </div>
      </dl>
    </div>

    <audio
      v-if="selectedTrack?.filePath"
      class="audio-preview"
      controls
      :src="selectedTrack.filePath"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { Paragraph, VoiceStudioStatus } from "@/stores/voice-studio";
import type { VoiceProfileDto, VoiceTrackDto } from "@/types/runtime";

const props = defineProps<{
  activeParagraph: Paragraph | null;
  generationMessage: string | null;
  selectedProfile: VoiceProfileDto | null;
  selectedTrack: VoiceTrackDto | null;
  stateMessage: string;
  status: VoiceStudioStatus;
}>();

const bars = Array.from({ length: 36 }, (_, index) => ({
  height: 14 + Math.round(Math.abs(Math.sin(index * 0.78) * 42)),
  index
}));

const title = computed(() => {
  if (props.status === "generating") return "正在生成配音版本。";
  if (props.status === "blocked") return "配音能力被阻断。";
  if (props.status === "error") return "配音工作台需要处理错误。";
  if (!props.selectedTrack) return "等待真实配音版本。";
  return "脚本文本与音色已经接通。";
});

const stageCopy = computed(() => {
  const paragraphText = props.activeParagraph?.text ?? "选择脚本文本段落后，这里会显示当前配音上下文。";
  const profileText = props.selectedProfile
    ? `${props.selectedProfile.displayName} · ${props.selectedProfile.locale}`
    : "当前没有选中的音色。";
  return `${paragraphText} 当前音色：${profileText}`;
});

const statusLabel = computed(() => {
  if (props.status === "loading") return "读取中";
  if (props.status === "generating") return "生成中";
  if (props.status === "blocked") return "阻断";
  if (props.status === "error") return "错误";
  if (!props.selectedTrack) return "空态";
  return "可用";
});

const statusMessage = computed(() => {
  if (props.status === "loading") return "正在读取脚本文本、音色列表和配音版本。";
  if (props.status === "generating") return "正在把脚本文本整理为真实配音版本记录。";
  if (props.status === "blocked") {
    return props.generationMessage || props.stateMessage;
  }
  if (props.status === "error") return props.stateMessage;
  if (!props.selectedTrack) {
    return "真实音频尚未生成，先选择可用音色并创建 Runtime 版本。";
  }
  return props.stateMessage;
});

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
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 10%, transparent), transparent 42%),
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

.wave-stage {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 120px;
  padding: 18px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: color-mix(in srgb, var(--bg-base) 80%, transparent);
}

.wave-bar {
  width: 7px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--brand-primary) 78%, var(--text-primary));
  opacity: 0.72;
}

.wave-stage--busy .wave-bar {
  animation: voice-pulse 1.1s ease-in-out infinite alternate;
}

.wave-stage--busy .wave-bar:nth-child(2n) {
  animation-delay: 120ms;
}

.wave-stage--busy .wave-bar:nth-child(3n) {
  animation-delay: 220ms;
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

.audio-preview {
  width: 100%;
}

@keyframes voice-pulse {
  from {
    opacity: 0.46;
    transform: scaleY(0.72);
  }
  to {
    opacity: 0.96;
    transform: scaleY(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .wave-stage--busy .wave-bar {
    animation: none;
  }
}
</style>
