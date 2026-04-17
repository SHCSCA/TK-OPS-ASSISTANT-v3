<template>
  <section class="subtitle-page" data-testid="subtitle-alignment-page">
    <header class="hero">
      <div class="hero__copy">
        <span class="hero__kicker">M08 字幕对齐中心</span>
        <h1>把脚本文本整理成可校对、可追踪、可回流的字幕版本。</h1>
        <p>
          当前只保留真实脚本文本、真实字幕段和真实样式草稿。
          没有可用字幕对齐 Provider 时，只保存阻断草稿，不会伪造准确时间码。
        </p>
        <div class="hero__meta">
          <span class="pill pill--brand">{{ currentProjectName }}</span>
          <span class="pill" :data-state="pageStateTone">{{ pageStateLabel }}</span>
          <span class="pill">{{ store.draftSegments.length }} 段草稿</span>
          <span class="pill">{{ store.tracks.length }} 条字幕版本</span>
        </div>
      </div>

      <div class="hero__actions">
        <button
          class="action-button action-button--primary"
          data-testid="subtitle-generate-button"
          :disabled="generateDisabled"
          type="button"
          @click="handleGenerate"
        >
          {{ generateButtonLabel }}
        </button>
        <button
          class="action-button action-button--secondary"
          :disabled="saveDisabled"
          type="button"
          @click="handleSave"
        >
          {{ saveButtonLabel }}
        </button>
      </div>
    </header>

    <section class="state-banner" :data-state="pageStateTone">
      <div class="state-banner__body">
        <strong>{{ bannerTitle }}</strong>
        <p>{{ bannerMessage }}</p>
      </div>
      <div class="state-banner__tags">
        <span>脚本：{{ scriptStateLabel }}</span>
        <span>样式：{{ styleStateLabel }}</span>
        <span>版本：{{ versionStateLabel }}</span>
      </div>
    </section>

    <div v-if="!currentProject" class="guide-panel">
      <span class="material-symbols-outlined">subtitles_off</span>
      <div>
        <strong>请先选择项目</strong>
        <span>字幕对齐中心需要先读取当前项目脚本，才能进入真实草稿和版本工作台。</span>
      </div>
    </div>

    <main v-else class="subtitle-workbench">
      <SubtitleSegmentList
        :active-index="store.activeSegmentIndex"
        :error-message="store.error?.message ?? null"
        :segments="store.draftSegments"
        :state-message="panelStateMessage"
        :status="presentationStatus"
        @select="store.selectSegment"
        @update-segment="store.updateDraftSegment"
      />

      <SubtitlePreviewStage
        :active-segment="store.activeSegment"
        :generation-message="store.generationResult?.message ?? null"
        :selected-track="store.selectedTrack"
        :state-message="panelStateMessage"
        :status="presentationStatus"
        :style-config="store.style"
      />

      <aside class="subtitle-side-rail">
        <SubtitleTimingPanel
          :locked="timingLocked"
          :locked-reason="timingLockedReason"
          :segment="store.activeSegment"
          @update-segment="handleActiveSegmentUpdate"
        />
        <SubtitleStylePanel
          :locked="styleLocked"
          :locked-reason="styleLockedReason"
          :style-config="store.style"
          @update-style="store.updateStyle"
        />
        <button
          class="save-action"
          :disabled="saveDisabled"
          type="button"
          @click="handleSave"
        >
          {{ saveButtonLabel }}
        </button>
        <SubtitleVersionPanel
          :error-message="store.error?.message ?? null"
          :selected-track-id="store.selectedTrackId"
          :state-message="panelStateMessage"
          :status="presentationStatus"
          :tracks="store.tracks"
          @delete="store.deleteTrack"
          @select="store.selectTrack"
        />
      </aside>
    </main>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";

import SubtitlePreviewStage from "@/modules/subtitles/SubtitlePreviewStage.vue";
import SubtitleSegmentList from "@/modules/subtitles/SubtitleSegmentList.vue";
import SubtitleStylePanel from "@/modules/subtitles/SubtitleStylePanel.vue";
import SubtitleTimingPanel from "@/modules/subtitles/SubtitleTimingPanel.vue";
import SubtitleVersionPanel from "@/modules/subtitles/SubtitleVersionPanel.vue";
import { useProjectStore } from "@/stores/project";
import { useSubtitleAlignmentStore } from "@/stores/subtitle-alignment";
import type { SubtitleSegmentDto } from "@/types/runtime";

const projectStore = useProjectStore();
const store = useSubtitleAlignmentStore();

const currentProject = computed(() => projectStore.currentProject);
const currentProjectId = computed(() => currentProject.value?.projectId ?? "");
const currentProjectName = computed(() => currentProject.value?.projectName ?? "当前项目未就绪");
const hasScript = computed(() => store.paragraphs.length > 0);
const hasSelectedTrack = computed(() => Boolean(store.selectedTrackId));
const hasBlockedTrack = computed(() => store.selectedTrack?.status === "blocked");
const presentationStatus = computed(() =>
  hasBlockedTrack.value && store.status === "ready" ? "blocked" : store.status
);

const generateDisabled = computed(() => {
  if (!currentProject.value) return true;
  if (store.status === "loading" || store.status === "aligning" || store.status === "saving") {
    return true;
  }
  if (store.status === "error") return true;
  return !hasScript.value;
});

const saveDisabled = computed(() => {
  if (!currentProject.value) return true;
  if (store.status === "loading" || store.status === "saving") return true;
  if (store.status === "error") return true;
  return !hasSelectedTrack.value;
});

const generateButtonLabel = computed(() => {
  if (!currentProject.value) return "生成入口已锁定";
  if (store.status === "aligning") return "生成中";
  if (store.status === "blocked" || hasBlockedTrack.value) return "重新保存阻断草稿";
  return "生成字幕草稿";
});

const saveButtonLabel = computed(() => {
  if (store.status === "saving") return "保存中";
  if (!hasSelectedTrack.value) return "暂无可保存版本";
  return "保存字幕校正";
});

const pageStateTone = computed(() => {
  if (!currentProject.value) return "blocked";
  if (store.status === "loading") return "loading";
  if (store.status === "aligning" || store.status === "saving") return "loading";
  if (store.status === "error") return "error";
  if (!hasScript.value) return "empty";
  if (store.status === "blocked" || hasBlockedTrack.value) return "blocked";
  return "ready";
});

const pageStateLabel = computed(() => {
  if (!currentProject.value) return "blocked";
  if (store.status === "loading") return "loading";
  if (store.status === "aligning" || store.status === "saving") return "loading";
  if (store.status === "error") return "error";
  if (!hasScript.value) return "empty";
  if (store.status === "blocked" || hasBlockedTrack.value) return "blocked";
  return "ready";
});

const scriptStateLabel = computed(() => {
  if (store.status === "loading") return "读取中";
  if (store.status === "error") return "异常";
  if (!hasScript.value) return "空态";
  return "已读取";
});

const styleStateLabel = computed(() => {
  if (store.status === "loading") return "读取中";
  if (store.status === "error") return "异常";
  if (store.status === "blocked" || hasBlockedTrack.value) return "阻断草稿";
  return "可编辑";
});

const versionStateLabel = computed(() => {
  if (store.status === "aligning") return "生成中";
  if (store.status === "saving") return "保存中";
  if (store.status === "blocked" || hasBlockedTrack.value) return "阻断草稿";
  if (store.status === "error") return "异常";
  if (!store.tracks.length) return "空态";
  return "已保存";
});

const bannerTitle = computed(() => {
  if (!currentProject.value) return "字幕入口被阻断。";
  if (store.status === "loading") return "正在读取脚本和字幕版本。";
  if (store.status === "error") return "字幕工作台读取失败。";
  if (!hasScript.value) return "脚本文本为空，无法生成字幕草稿。";
  if (store.status === "blocked" || hasBlockedTrack.value) return "已保存阻断草稿，但没有生成真实时间码。";
  if (store.status === "aligning") return "正在生成字幕草稿。";
  if (store.status === "saving") return "正在保存字幕校正。";
  return "脚本、字幕段和样式草稿都已接通。";
});

const bannerMessage = computed(() => {
  if (!currentProject.value) {
    return "先选择真实项目，再读取脚本文本和字幕版本。没有项目上下文时，不创建假字幕和假时间码。";
  }

  if (store.status === "loading") {
    return "脚本、字幕草稿和版本记录正在从 Runtime 拉取，当前只显示加载状态。";
  }

  if (store.status === "error") {
    return store.error?.message ?? "字幕工作台读取失败，请稍后重试。";
  }

  if (!hasScript.value) {
    return "脚本文本为空，先在脚本与选题中心写入内容，再继续做字幕对齐。";
  }

  if (store.status === "blocked" || hasBlockedTrack.value) {
    return store.generationResult?.message ?? "没有可用字幕对齐 Provider，当前只保存阻断草稿，不生成准确时间码。";
  }

  if (store.status === "aligning") {
    return "正在把脚本文本整理为字幕草稿，不会提前写入假时间码。";
  }

  if (store.status === "saving") {
    return "正在保存字幕段和样式校正，保存完成前保持当前状态。";
  }

  return "字幕段、样式草稿和版本记录都来自真实 Runtime 返回值。";
});

const panelStateMessage = computed(() => {
  if (!currentProject.value) return "当前项目未就绪，工作台保持阻断。";
  if (store.status === "loading") return "正在读取 Runtime 数据。";
  if (store.status === "error") return store.error?.message ?? "读取失败。";
  if (!hasScript.value) return "脚本文本为空。";
  if (store.status === "blocked" || hasBlockedTrack.value) {
    return store.generationResult?.message ?? "字幕对齐 Provider 未接通，当前版本为阻断草稿。";
  }
  if (store.status === "aligning") return "正在生成字幕草稿。";
  if (store.status === "saving") return "正在保存字幕校正。";
  return "真实字幕草稿和样式已接通。";
});

const timingLocked = computed(
  () =>
    !currentProject.value ||
    store.status === "loading" ||
    store.status === "error" ||
    !store.activeSegment
);

const timingLockedReason = computed(() => {
  if (!currentProject.value) return "请先选择项目。";
  if (store.status === "loading") return "正在读取脚本和字幕版本。";
  if (store.status === "error") return store.error?.message ?? "读取失败。";
  if (!store.activeSegment) return "当前没有可编辑的字幕段。";
  return "";
});

const styleLocked = computed(
  () => !currentProject.value || store.status === "loading" || store.status === "error"
);

const styleLockedReason = computed(() => {
  if (!currentProject.value) return "请先选择项目。";
  if (store.status === "loading") return "正在读取样式草稿。";
  if (store.status === "error") return store.error?.message ?? "读取失败。";
  return "";
});

watch(
  () => store.draftSegments.length,
  (count) => {
    if (count === 0) {
      store.activeSegmentIndex = 0;
    } else if (store.activeSegmentIndex >= count) {
      store.activeSegmentIndex = 0;
    }
  }
);

onMounted(() => {
  loadProjectSubtitles();
});

watch(
  () => currentProject.value?.projectId,
  () => {
    loadProjectSubtitles();
  }
);

async function loadProjectSubtitles(): Promise<void> {
  const projectId = currentProjectId.value;
  if (!projectId) return;
  await store.load(projectId);
}

async function handleGenerate(): Promise<void> {
  if (generateDisabled.value) return;
  await store.generate();
}

async function handleSave(): Promise<void> {
  if (saveDisabled.value) return;
  await store.updateSelectedTrack();
}

function handleActiveSegmentUpdate(patch: Partial<SubtitleSegmentDto>): void {
  store.updateDraftSegment(store.activeSegmentIndex, patch);
}
</script>

<style scoped>
.subtitle-page {
  display: grid;
  gap: 16px;
  min-height: 100%;
  padding: 28px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 8%, transparent), transparent 34%),
    var(--bg-base);
  color: var(--text-primary);
}

.hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 24px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
}

.hero__copy {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.hero__kicker {
  color: var(--brand-primary);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0;
}

h1,
h2,
h3,
p {
  margin: 0;
}

h1 {
  font-size: 32px;
  line-height: 1.15;
}

.hero__copy p,
.guide-panel span,
.state-surface p {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.hero__meta,
.state-banner__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.pill--brand {
  border-color: color-mix(in srgb, var(--brand-primary) 36%, transparent);
  background: color-mix(in srgb, var(--brand-primary) 10%, var(--bg-card));
  color: var(--brand-primary);
}

.pill[data-state="loading"] {
  border-color: color-mix(in srgb, var(--info) 28%, transparent);
  background: color-mix(in srgb, var(--info) 12%, var(--bg-card));
  color: var(--info);
}

.pill[data-state="blocked"] {
  border-color: color-mix(in srgb, var(--warning) 28%, transparent);
  background: color-mix(in srgb, var(--warning) 10%, var(--bg-card));
  color: var(--warning);
}

.pill[data-state="error"] {
  border-color: color-mix(in srgb, var(--danger) 28%, transparent);
  background: color-mix(in srgb, var(--danger) 10%, var(--bg-card));
  color: var(--danger);
}

.pill[data-state="empty"] {
  border-color: color-mix(in srgb, var(--text-tertiary) 28%, transparent);
  background: var(--bg-card);
  color: var(--text-tertiary);
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.action-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  transition:
    transform 160ms ease,
    opacity 160ms ease,
    border-color 160ms ease,
    background-color 160ms ease;
}

.action-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.action-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.action-button--primary {
  background: var(--brand-primary);
  color: #041414;
}

.action-button--secondary {
  border-color: var(--border-default);
  background: var(--bg-card);
  color: var(--text-primary);
}

.state-banner {
  display: grid;
  gap: 12px;
  padding: 16px 18px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
}

.state-banner[data-state="blocked"] {
  border-color: color-mix(in srgb, var(--warning) 32%, transparent);
}

.state-banner[data-state="error"] {
  border-color: color-mix(in srgb, var(--danger) 32%, transparent);
}

.state-banner[data-state="loading"] {
  border-color: color-mix(in srgb, var(--info) 26%, transparent);
}

.state-banner[data-state="empty"] {
  border-color: color-mix(in srgb, var(--text-tertiary) 26%, transparent);
}

.state-banner__body {
  display: grid;
  gap: 4px;
}

.state-banner__body strong {
  font-size: 16px;
}

.guide-panel {
  display: grid;
  grid-template-columns: auto minmax(0, 520px);
  align-items: center;
  gap: 16px;
  padding: 20px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
}

.guide-panel .material-symbols-outlined {
  color: var(--brand-primary);
  font-size: 42px;
}

.guide-panel strong {
  display: block;
  margin-bottom: 4px;
  font-size: 16px;
}

.subtitle-workbench {
  display: grid;
  grid-template-columns: minmax(260px, 0.88fr) minmax(420px, 1.35fr) minmax(280px, 0.8fr);
  gap: 16px;
  min-height: 0;
}

.subtitle-side-rail {
  display: grid;
  align-content: start;
  gap: 12px;
  min-height: 0;
}

.save-action {
  width: 100%;
  min-height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: var(--brand-primary);
  color: #041414;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  transition:
    transform 160ms ease,
    opacity 160ms ease;
}

.save-action:hover:not(:disabled) {
  transform: translateY(-1px);
}

.save-action:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

@media (max-width: 1160px) {
  .subtitle-page {
    padding: 20px;
  }

  .hero {
    flex-direction: column;
  }

  .subtitle-workbench {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  h1 {
    font-size: 28px;
  }

  .guide-panel {
    grid-template-columns: 1fr;
  }
}
</style>
