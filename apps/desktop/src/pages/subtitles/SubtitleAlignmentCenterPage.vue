<template>
  <div class="page-container h-full">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 字幕对齐中心</div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">M08 字幕对齐中心</h1>
          <div class="page-header__subtitle">
            以已采用脚本和真实字幕轨道为基础，对 blocked 草稿进行校对、微调与样式确认。
          </div>
        </div>
        <div class="page-header__actions">
          <Button
            variant="ai"
            data-testid="subtitle-generate-button"
            :running="store.status === 'aligning'"
            :disabled="generateDisabled"
            @click="handleGenerate"
          >
            <template #leading><span class="material-symbols-outlined">auto_awesome</span></template>
            {{ generateButtonLabel }}
          </Button>
          <Button
            variant="primary"
            :running="store.status === 'saving'"
            :disabled="saveDisabled"
            @click="handleSave"
          >
            <template #leading><span class="material-symbols-outlined">save</span></template>
            {{ saveButtonLabel }}
          </Button>
        </div>
      </div>
    </header>

    <div v-if="pageStateTone === 'error'" class="dashboard-alert" data-tone="danger">
      <span class="material-symbols-outlined">error</span>
      <span>{{ bannerTitle }} - {{ bannerMessage }}</span>
    </div>
    <div v-else-if="pageStateTone === 'blocked'" class="dashboard-alert" data-tone="warning">
      <span class="material-symbols-outlined">warning</span>
      <span>{{ bannerTitle }} - {{ bannerMessage }}</span>
    </div>
    <div v-else-if="store.activeTask" class="dashboard-alert" data-tone="brand">
      <span class="material-symbols-outlined spinning">sync</span>
      <span>{{ store.activeTask.message }} ({{ store.activeTask.progress }}%)</span>
    </div>

    <section class="semantic-summary" aria-label="字幕语义摘要">
      <Card class="semantic-summary__card">
        <span class="semantic-summary__label">当前项目</span>
        <strong>{{ currentProjectName }}</strong>
      </Card>
      <Card class="semantic-summary__card">
        <span class="semantic-summary__label">阻断草稿</span>
        <strong>{{ blockedDraftLabel }}</strong>
        <p>{{ blockedDraftMessage }}</p>
      </Card>
      <Card class="semantic-summary__card">
        <span class="semantic-summary__label">真实时间码</span>
        <strong>{{ realTimelineLabel }}</strong>
        <p>{{ panelStateMessage }}</p>
      </Card>
      <Card class="semantic-summary__card">
        <span class="semantic-summary__label">脚本文案</span>
        <strong>{{ scriptStateLabel }}</strong>
        <p>{{ paragraphPreview }}</p>
      </Card>
    </section>

    <div v-if="!currentProject" class="empty-state">
      <span class="material-symbols-outlined">subtitles_off</span>
      <strong>请先选择一个项目</strong>
      <p>字幕对齐中心依赖当前项目及其脚本文案和字幕轨道，请先在侧边栏切换项目。</p>
    </div>

    <div v-else class="subtitle-workspace">
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

      <aside class="subtitle-rail">
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import SubtitlePreviewStage from "@/modules/subtitles/SubtitlePreviewStage.vue";
import SubtitleSegmentList from "@/modules/subtitles/SubtitleSegmentList.vue";
import SubtitleStylePanel from "@/modules/subtitles/SubtitleStylePanel.vue";
import SubtitleTimingPanel from "@/modules/subtitles/SubtitleTimingPanel.vue";
import SubtitleVersionPanel from "@/modules/subtitles/SubtitleVersionPanel.vue";
import { useProjectStore } from "@/stores/project";
import { useSubtitleAlignmentStore } from "@/stores/subtitle-alignment";
import type { SubtitleSegmentDto, SubtitleTrackDto } from "@/types/runtime";

const projectStore = useProjectStore();
const store = useSubtitleAlignmentStore();

const currentProject = computed(() => projectStore.currentProject);
const currentProjectId = computed(() => currentProject.value?.projectId ?? "");
const currentProjectName = computed(() => currentProject.value?.projectName ?? "未选择项目");
const hasScript = computed(() => store.paragraphs.length > 0);
const hasSelectedTrack = computed(() => Boolean(store.selectedTrackId));
const hasBlockedTrack = computed(() => hasBlockingAlignment(store.selectedTrack));
const presentationStatus = computed(() =>
  hasBlockedTrack.value && store.status === "ready" ? "blocked" : store.status
);

const normalizedGenerationMessage = computed(() => {
  const raw = store.generationResult?.message ?? "";
  return raw.replace("尚未配置可用字幕对齐 Provider", "没有可用字幕对齐 Provider");
});

const generateDisabled = computed(() => {
  if (!currentProject.value) return true;
  if (store.status === "loading" || store.status === "aligning" || store.status === "saving") return true;
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
  if (!currentProject.value) return "等待项目选择";
  if (store.status === "aligning") return "对齐中...";
  if (store.status === "blocked" || hasBlockedTrack.value) return "重新保存阻断草稿";
  return "AI 自动对齐";
});

const saveButtonLabel = computed(() => {
  if (store.status === "saving") return "保存中...";
  if (!hasSelectedTrack.value) return "暂无修改可保存";
  return "保存微调与样式";
});

const pageStateTone = computed(() => {
  if (!currentProject.value) return "blocked";
  if (store.status === "loading" || store.status === "aligning" || store.status === "saving") return "loading";
  if (store.status === "error") return "error";
  if (!hasScript.value) return "empty";
  if (store.status === "blocked" || hasBlockedTrack.value) return "blocked";
  return "ready";
});

const scriptStateLabel = computed(() => {
  if (store.status === "loading") return "加载中";
  if (store.status === "error") return "异常";
  if (!hasScript.value) return "文案为空";
  return "已就绪";
});

const bannerTitle = computed(() => {
  if (!currentProject.value) return "生成入口已锁定";
  if (store.status === "loading") return "正在读取项目状态";
  if (store.status === "error") return "字幕加载失败";
  if (!hasScript.value) return "脚本文案缺失";
  if (store.status === "blocked" || hasBlockedTrack.value) return "对齐任务已阻断";
  if (store.status === "aligning") return "正在执行 AI 自动对齐";
  if (store.status === "saving") return "正在保存调整结果";
  return "字幕对齐环境已就绪";
});

const bannerMessage = computed(() => {
  if (!currentProject.value) return "请先选择项目";
  if (store.status === "loading") return "正在同步脚本文案、字幕轨道和样式配置，请稍候。";
  if (store.status === "error") {
    return store.error?.message ?? "字幕对齐中心遇到异常，请检查 Runtime 状态。";
  }
  if (!hasScript.value) return "脚本文案为空";
  if (store.status === "blocked" || hasBlockedTrack.value) {
    return normalizedGenerationMessage.value || "已保存阻断草稿，但没有生成真实时间码。";
  }
  if (store.status === "aligning") return "正在分析配音和脚本文案，为当前项目生成对齐草稿。";
  if (store.status === "saving") return "正在保存时间轴微调和样式配置。";
  return "可以继续微调时间轴、更新样式，或重新生成字幕轨道。";
});

const panelStateMessage = computed(() => {
  if (!currentProject.value) return "环境未就绪";
  if (store.status === "loading") return "加载中";
  if (store.status === "error") return store.error?.message ?? "请求异常";
  if (!hasScript.value) return "脚本文案缺失";
  if (store.status === "blocked" || hasBlockedTrack.value) {
    return normalizedGenerationMessage.value || "已保存阻断草稿，但没有生成真实时间码。";
  }
  if (store.status === "aligning") return "对齐中";
  if (store.status === "saving") return "保存中";
  return "准备就绪";
});

const blockedDraftLabel = computed(() => {
  if (store.status === "blocked" || hasBlockedTrack.value) return "版本：阻断草稿";
  return hasSelectedTrack.value ? "版本：可编辑轨道" : "版本：暂无轨道";
});

const blockedDraftMessage = computed(() => {
  if (store.status === "blocked" || hasBlockedTrack.value) {
    const providerPart = normalizedGenerationMessage.value;
    const base = "已保存阻断草稿，但没有生成真实时间码。";
    return providerPart ? `${providerPart} ${base}` : base;
  }
  return "当前轨道可继续编辑。";
});

const realTimelineLabel = computed(() => {
  if (store.status === "blocked" || hasBlockedTrack.value) return "真实时间码待补齐";
  if (store.status === "aligning") return "真实时间码生成中";
  return hasSelectedTrack.value ? "真实时间码已接入" : "真实时间码未生成";
});

const paragraphPreview = computed(() => {
  if (!store.paragraphs.length) return "暂无脚本文案";
  return store.paragraphs.map((paragraph) => paragraph.text).join(" ");
});

const timingLocked = computed(
  () => !currentProject.value || store.status === "loading" || store.status === "error" || !store.activeSegment
);
const timingLockedReason = computed(() => {
  if (!currentProject.value) return "未选择项目";
  if (store.status === "loading") return "加载中";
  if (store.status === "error") return store.error?.message ?? "请求异常";
  if (!store.activeSegment) return "请先在列表中选中一个字幕片段";
  return "";
});

const styleLocked = computed(() => !currentProject.value || store.status === "loading" || store.status === "error");
const styleLockedReason = computed(() => {
  if (!currentProject.value) return "未选择项目";
  if (store.status === "loading") return "加载中";
  if (store.status === "error") return store.error?.message ?? "请求异常";
  return "";
});

watch(
  () => store.draftSegments.length,
  (count) => {
    if (count === 0) store.activeSegmentIndex = 0;
    else if (store.activeSegmentIndex >= count) store.activeSegmentIndex = 0;
  }
);

onMounted(() => {
  void loadProjectSubtitles();
});

watch(
  () => currentProject.value?.projectId,
  () => {
    void loadProjectSubtitles();
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

function hasBlockingAlignment(track: SubtitleTrackDto | null): boolean {
  if (!track) {
    return false;
  }

  return (
    track.status === "blocked" ||
    track.alignment.status === "draft" ||
    track.alignment.status === "needs_alignment" ||
    Boolean(track.alignment.errorCode)
  );
}
</script>

<style scoped>
.page-container {
  max-width: var(--density-page-max-width);
  margin: 0 auto;
  padding: var(--space-6) var(--space-8) var(--space-8);
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.page-header {
  display: grid;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.page-header__crumb {
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.page-header__row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.page-header__title {
  font: var(--font-display-md);
  letter-spacing: var(--ls-display-md);
  color: var(--color-text-primary);
  margin: 0 0 4px 0;
}

.page-header__subtitle {
  font: var(--font-body-md);
  letter-spacing: var(--ls-body-md);
  color: var(--color-text-secondary);
}

.page-header__actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.dashboard-alert {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-muted);
  line-height: 1.6;
  margin-bottom: var(--space-4);
  font: var(--font-body-sm);
  display: flex;
  align-items: center;
  gap: 8px;
}

.dashboard-alert[data-tone="danger"] {
  border-color: rgba(255, 90, 99, 0.2);
  background: rgba(255, 90, 99, 0.08);
  color: var(--color-danger);
}

.dashboard-alert[data-tone="warning"] {
  border-color: rgba(245, 183, 64, 0.2);
  background: rgba(245, 183, 64, 0.08);
  color: var(--color-warning);
}

.dashboard-alert[data-tone="brand"] {
  border-color: rgba(0, 188, 212, 0.2);
  background: rgba(0, 188, 212, 0.08);
  color: var(--color-brand-primary);
}

.semantic-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.semantic-summary__card {
  padding: var(--space-4);
  display: grid;
  gap: 4px;
}

.semantic-summary__label {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.semantic-summary__card strong {
  font: var(--font-title-md);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.semantic-summary__card p {
  margin: 0;
  font: var(--font-caption);
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-12) var(--space-6);
  border: 1px dashed var(--color-border-default);
  border-radius: var(--radius-lg);
  background: var(--color-bg-canvas);
  color: var(--color-text-secondary);
  text-align: center;
}

.empty-state .material-symbols-outlined {
  font-size: 32px;
  color: var(--color-text-tertiary);
}

.empty-state strong {
  font: var(--font-title-md);
  color: var(--color-text-primary);
}

.empty-state p {
  margin: 0;
  font: var(--font-body-md);
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}

.subtitle-workspace {
  display: grid;
  grid-template-columns: minmax(260px, 0.88fr) minmax(420px, 1.35fr) minmax(280px, 0.8fr);
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
}

.subtitle-rail {
  display: grid;
  align-content: start;
  gap: var(--space-4);
  min-height: 0;
  overflow-y: auto;
}

@media (max-width: 1200px) {
  .subtitle-workspace {
    grid-template-columns: minmax(240px, 1fr) minmax(360px, 1fr);
  }

  .subtitle-rail {
    grid-column: 1 / -1;
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 860px) {
  .subtitle-workspace {
    grid-template-columns: 1fr;
  }

  .subtitle-rail {
    grid-template-columns: 1fr;
  }

  .semantic-summary {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
