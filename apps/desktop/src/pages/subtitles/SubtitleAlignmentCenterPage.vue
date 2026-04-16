<template>
  <section class="subtitle-page">
    <header class="subtitle-toolbar">
      <div class="toolbar-copy">
        <span class="page-kicker">M08 字幕对齐中心</span>
        <h1>字幕对齐中心</h1>
        <p>把脚本文本整理成可校对、可追踪、可回流时间线的字幕版本。</p>
      </div>

      <div class="toolbar-actions">
        <span class="project-pill">
          {{ currentProject?.projectName ?? "请先选择项目" }}
        </span>
        <button
          class="primary-action"
          data-testid="subtitle-generate-button"
          :disabled="!canGenerate"
          type="button"
          @click="handleGenerate"
        >
          <span class="material-symbols-outlined">
            {{ store.status === "aligning" ? "sync" : "auto_awesome" }}
          </span>
          {{ store.status === "aligning" ? "生成中" : "生成字幕草稿" }}
        </button>
      </div>
    </header>

    <div v-if="!currentProject" class="guide-panel">
      <span class="material-symbols-outlined">subtitles_off</span>
      <div>
        <h2>请先选择项目</h2>
        <p>字幕对齐中心需要读取当前项目的脚本文本后才能创建字幕草稿。</p>
      </div>
    </div>

    <main v-else class="subtitle-workbench">
      <SubtitleSegmentList
        :active-index="store.activeSegmentIndex"
        :error-message="store.error?.message ?? null"
        :segments="store.draftSegments"
        :status="store.status"
        @select="store.selectSegment"
        @update-segment="store.updateDraftSegment"
      />

      <SubtitlePreviewStage
        :active-segment="store.activeSegment"
        :generation-message="store.generationResult?.message ?? null"
        :selected-track="store.selectedTrack"
        :status="store.status"
        :style-config="store.style"
      />

      <aside class="subtitle-side-rail">
        <SubtitleTimingPanel
          :segment="store.activeSegment"
          @update-segment="handleActiveSegmentUpdate"
        />
        <SubtitleStylePanel
          :style-config="store.style"
          @update-style="store.updateStyle"
        />
        <button
          class="save-action"
          :disabled="!store.selectedTrackId || store.status === 'saving'"
          type="button"
          @click="store.updateSelectedTrack"
        >
          {{ store.status === "saving" ? "保存中" : "保存字幕校正" }}
        </button>
        <SubtitleVersionPanel
          :selected-track-id="store.selectedTrackId"
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

const canGenerate = computed(
  () =>
    Boolean(currentProject.value) &&
    store.paragraphs.length > 0 &&
    store.status !== "loading" &&
    store.status !== "aligning" &&
    store.status !== "saving"
);

async function loadProjectSubtitles(): Promise<void> {
  const projectId = currentProject.value?.projectId;
  if (!projectId) return;
  await store.load(projectId);
}

async function handleGenerate(): Promise<void> {
  if (!canGenerate.value) return;
  await store.generate();
}

function handleActiveSegmentUpdate(patch: Partial<SubtitleSegmentDto>): void {
  store.updateDraftSegment(store.activeSegmentIndex, patch);
}

onMounted(loadProjectSubtitles);

watch(
  () => currentProject.value?.projectId,
  async (projectId, previousProjectId) => {
    if (projectId && projectId !== previousProjectId) {
      await loadProjectSubtitles();
    }
  }
);
</script>

<style scoped>
.subtitle-page {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 20px;
  min-height: 100%;
  padding: 28px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 10%, transparent), transparent 34%),
    var(--bg-base);
  color: var(--text-primary);
  overflow: hidden;
}

.subtitle-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 20px;
}

.toolbar-copy {
  display: grid;
  gap: 8px;
}

.page-kicker {
  color: var(--brand-primary);
  font-size: 13px;
  font-weight: 900;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  font-size: 34px;
  line-height: 1.1;
}

.toolbar-copy p,
.guide-panel p {
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.7;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.project-pill {
  max-width: 280px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-elevated);
  color: var(--text-secondary);
  font-size: 13px;
  padding: 9px 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.primary-action,
.save-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  border: 0;
  border-radius: 8px;
  background: var(--brand-primary);
  color: #061010;
  cursor: pointer;
  font-size: 14px;
  font-weight: 900;
  padding: 0 16px;
  transition: opacity 160ms ease, transform 160ms ease;
}

.primary-action:hover:not(:disabled),
.save-action:hover:not(:disabled) {
  transform: translateY(-1px);
}

.primary-action:disabled,
.save-action:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.guide-panel {
  display: grid;
  grid-template-columns: auto minmax(0, 520px);
  place-content: center;
  align-items: center;
  gap: 18px;
  min-height: 360px;
  border: 1px dashed var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
}

.guide-panel .material-symbols-outlined {
  color: var(--brand-primary);
  font-size: 42px;
}

.guide-panel h2 {
  font-size: 24px;
}

.subtitle-workbench {
  display: grid;
  grid-template-columns: minmax(260px, 0.82fr) minmax(420px, 1.5fr) minmax(260px, 0.78fr);
  gap: 16px;
  min-height: 0;
}

.subtitle-side-rail {
  display: grid;
  align-content: start;
  gap: 12px;
  min-height: 0;
  overflow: auto;
}

.save-action {
  width: 100%;
}

@media (max-width: 1180px) {
  .subtitle-page {
    overflow: auto;
  }

  .subtitle-workbench {
    grid-template-columns: minmax(0, 1fr);
  }

  .subtitle-side-rail {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    overflow: visible;
  }
}

@media (max-width: 760px) {
  .subtitle-page {
    padding: 20px;
  }

  .subtitle-toolbar {
    grid-template-columns: 1fr;
  }

  .toolbar-actions,
  .subtitle-side-rail {
    align-items: stretch;
    flex-direction: column;
    grid-template-columns: 1fr;
  }

  .project-pill {
    max-width: none;
  }

  .guide-panel {
    grid-template-columns: 1fr;
    justify-items: start;
    padding: 24px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .primary-action,
  .save-action {
    transition: none;
  }

  .primary-action:hover:not(:disabled),
  .save-action:hover:not(:disabled) {
    transform: none;
  }
}
</style>
