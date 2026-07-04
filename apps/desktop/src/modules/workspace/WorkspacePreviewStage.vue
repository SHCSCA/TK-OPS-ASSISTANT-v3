<template>
  <main class="workspace-preview-stage" aria-label="预览舞台">
    <header class="workspace-preview-stage__header">
      <div>
        <strong>{{ previewContext.truthLabel }}</strong>
        <p>{{ previewContext.truthDescription }}</p>
        <div
          v-if="previewContext.previewMode !== 'media'"
          class="workspace-preview-stage__compact-status"
          data-testid="workspace-preview-compact-status"
        >
          <span>播放头</span>
          <time>{{ transportTimeLabel }}</time>
          <div
            class="workspace-preview-stage__compact-progress"
            aria-label="紧凑预览进度条"
            role="progressbar"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-valuenow="safePlayProgress"
          >
            <span :style="{ width: safePlayProgress + '%' }"></span>
          </div>
          <time>{{ durationLabel }}</time>
        </div>
      </div>
      <div class="workspace-preview-stage__header-actions">
        <div class="workspace-preview-stage__ratio-switch" aria-label="预览画幅">
          <button
            data-testid="workspace-preview-ratio-9-16"
            type="button"
            :aria-pressed="String(previewRatio === '9:16')"
            @click="previewRatio = '9:16'"
          >
            9:16
          </button>
          <button
            data-testid="workspace-preview-ratio-16-9"
            type="button"
            :aria-pressed="String(previewRatio === '16:9')"
            @click="previewRatio = '16:9'"
          >
            16:9
          </button>
        </div>
        <span class="workspace-preview-stage__pill">
          {{ timelineStatusLabel }}
        </span>
      </div>
    </header>

    <div class="workspace-preview-stage__body">
      <div class="workspace-preview-stage__viewer">
        <div
          class="workspace-preview-stage__canvas"
          data-testid="workspace-preview-canvas"
          :data-ratio="previewRatio"
          aria-label="预览画布"
        >
          <div class="workspace-preview-stage__screen">
            <div class="workspace-preview-stage__canvas-meta">
              <span data-testid="workspace-preview-truth">{{ previewContext.truthLabel }}</span>
              <small>{{ previewRatio }}</small>
            </div>
            <video
              v-if="previewContext.previewMode === 'media' && previewContext.mediaKind === 'video' && previewContext.mediaUrl"
              class="workspace-preview-stage__video"
              controls
              data-testid="workspace-preview-video"
              :src="previewContext.mediaUrl"
            />
            <section v-else class="workspace-preview-stage__content">
              <strong>{{ headline }}</strong>
              <p>{{ previewContext.summaryText }}</p>
              <small class="workspace-preview-stage__time-badge">{{ previewContext.currentTimeLabel }}</small>
            </section>
            <div class="workspace-preview-stage__safe-area" aria-hidden="true"></div>
            <div class="workspace-preview-stage__caption">
              {{ previewContext.captionText }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <footer class="workspace-preview-stage__footer">
      <div
        v-if="previewContext.previewMode !== 'media'"
        class="workspace-preview-stage__transport"
        data-testid="workspace-preview-transport"
      >
        <button type="button" disabled>
          <span class="material-symbols-outlined" aria-hidden="true">skip_previous</span>
          <span>上一段</span>
        </button>
        <button type="button" @click="$emit(isPlaying ? 'pause' : 'play')">
          <span class="material-symbols-outlined" aria-hidden="true">{{ isPlaying ? 'pause' : 'play_arrow' }}</span>
          <span>{{ isPlaying ? '暂停' : '播放' }}</span>
        </button>
        <time>{{ transportTimeLabel }}</time>
        <input
          class="workspace-preview-stage__scrubber"
          data-testid="workspace-preview-scrubber"
          type="range"
          aria-label="预览播放头"
          min="0"
          :max="durationMs"
          step="100"
          :value="currentPlayheadMs"
          @input="handleSeekInput"
        />
        <div
          class="workspace-preview-stage__progress"
          aria-label="预览进度条"
          role="progressbar"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="safePlayProgress"
        >
          <span :style="{ width: safePlayProgress + '%' }"></span>
        </div>
        <time>{{ durationLabel }}</time>
      </div>
      <div
        v-else
        class="workspace-preview-stage__media-note"
        data-testid="workspace-preview-media-note"
      >
        可播放素材使用播放器控件检查；画幅切换只调整监看比例。{{ previewContext.mediaInfoText ? ` ${previewContext.mediaInfoText}` : "" }}
      </div>
      <p>{{ previewContext.previewMode === "media" ? previewContext.description : "按时间线播放头检查分镜、配音和字幕节奏。" }}</p>
      <section
        v-if="previewContext.previewMode !== 'media' && previewContext.manifestSummary"
        class="workspace-preview-stage__manifest-summary"
        data-testid="workspace-preview-manifest-summary"
      >
        <strong>{{ previewContext.manifestSummary.summaryText }}</strong>
        <div class="workspace-preview-stage__manifest-tracks">
          <div
            v-for="track in previewContext.manifestSummary.tracks"
            :key="track.id"
            class="workspace-preview-stage__manifest-track"
            data-testid="workspace-preview-manifest-track"
          >
            <span>{{ track.name }}</span> <span>{{ track.kindLabel }}</span> <span>{{ track.clipCountLabel }}</span> <time>{{ track.durationLabel }}</time>
          </div>
        </div>
      </section>
      <section
        v-if="previewContext.runtimePreviewErrorMessage"
        class="workspace-preview-stage__runtime-error"
        data-testid="workspace-preview-runtime-error"
        role="status"
      >
        <span class="material-symbols-outlined" aria-hidden="true">sync_problem</span>
        <div>
          <strong>{{ previewContext.previewMode === "unavailable" ? "媒体预览不可用" : "Runtime 预览同步失败" }}</strong>
          <p>{{ previewContext.runtimePreviewErrorMessage }}</p>
        </div>
        <button type="button" data-testid="workspace-preview-retry" @click="$emit('retry-preview')">
          <span class="material-symbols-outlined" aria-hidden="true">refresh</span>
          <span>重新同步预览</span>
        </button>
      </section>
      <div
        v-if="previewContext.previewMode === 'media' && previewContext.mediaKind === 'audio' && previewContext.mediaUrl"
        class="workspace-preview-stage__audio"
        data-testid="workspace-preview-audio-panel"
      >
        <span class="material-symbols-outlined">graphic_eq</span>
        <div>
          <strong>音频素材预览</strong>
          <p>{{ previewContext.description }}</p>
        </div>
        <audio controls data-testid="workspace-preview-audio" :src="previewContext.mediaUrl" />
      </div>
    </footer>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import type { WorkspaceTimelineDto } from "@/types/runtime";
import type { WorkspacePreviewContext } from "./workspacePreviewContext";
import { formatWorkspaceTime } from "./workspaceTimelineViewModel";

const props = defineProps<{
  previewContext: WorkspacePreviewContext;
  timeline: WorkspaceTimelineDto | null;
  isPlaying?: boolean;
  playProgress?: number;
}>();

const previewRatio = ref<"9:16" | "16:9">("9:16");

const headline = computed(() => {
  return props.previewContext.headline;
});

const durationLabel = computed(() => {
  if (durationMs.value <= 0) return "待定";
  return formatWorkspaceTime(durationMs.value);
});

const transportTimeLabel = computed(() => props.previewContext.currentTimeLabel.replace("当前时间：", ""));

const timelineStatusLabel = computed(() => (props.timeline ? props.previewContext.statusLabel : "未创建草稿"));

const safePlayProgress = computed(() => {
  const progress = props.playProgress ?? 0;
  if (!Number.isFinite(progress)) return 0;
  return Math.min(100, Math.max(0, progress));
});

const durationMs = computed(() => {
  const seconds = props.timeline?.durationSeconds;
  if (seconds === null || seconds === undefined) return 0;
  return Math.max(0, Math.round(seconds * 1000));
});

const currentPlayheadMs = computed(() => Math.round((safePlayProgress.value / 100) * durationMs.value));

const emit = defineEmits<{
  play: [];
  pause: [];
  seek: [positionMs: number];
  "retry-preview": [];
}>();

function handleSeekInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  const nextPositionMs = Number(input.value);
  if (!Number.isFinite(nextPositionMs)) return;
  emit("seek", Math.max(0, Math.min(durationMs.value, Math.round(nextPositionMs))));
}

</script>

<style scoped src="./WorkspacePreviewStage.css"></style>
