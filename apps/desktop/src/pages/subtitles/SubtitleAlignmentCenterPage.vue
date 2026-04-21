<template>
  <div class="page-container h-full">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 媒体工作室</div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">字幕对齐中心</h1>
          <div class="page-header__subtitle">基于已采用的文案与配音音轨生成对齐的字幕，并提供微调与样式设置。</div>
        </div>
        <div class="page-header__actions">
          <Button variant="ai" :running="store.status === 'aligning'" :disabled="generateDisabled" @click="handleGenerate">
            <template #leading><span class="material-symbols-outlined">auto_awesome</span></template>
            {{ generateButtonLabel }}
          </Button>
          <Button variant="primary" :running="store.status === 'saving'" :disabled="saveDisabled" @click="handleSave">
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

    <div class="summary-grid">
      <Card class="summary-card">
        <span class="sc-label">当前项目</span>
        <strong class="sc-val">{{ currentProjectName }}</strong>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">字幕片段</span>
        <strong class="sc-val">{{ store.draftSegments.length }} 段</strong>
        <p class="sc-hint">{{ scriptStateLabel }}</p>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">样式配置</span>
        <strong class="sc-val">{{ styleStateLabel }}</strong>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">字幕音轨</span>
        <strong class="sc-val">{{ store.tracks.length }} 条</strong>
        <p class="sc-hint">{{ versionStateLabel }}</p>
      </Card>
    </div>

    <div v-if="!currentProject" class="empty-state">
      <span class="material-symbols-outlined">subtitles_off</span>
      <strong>请先选择一个项目</strong>
      <p>字幕对齐中心依赖于当前项目及其配音音轨，请在侧边栏选择项目后开始工作。</p>  
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

import SubtitlePreviewStage from "@/modules/subtitles/SubtitlePreviewStage.vue";
import SubtitleSegmentList from "@/modules/subtitles/SubtitleSegmentList.vue";
import SubtitleStylePanel from "@/modules/subtitles/SubtitleStylePanel.vue";
import SubtitleTimingPanel from "@/modules/subtitles/SubtitleTimingPanel.vue";
import SubtitleVersionPanel from "@/modules/subtitles/SubtitleVersionPanel.vue";
import { useProjectStore } from "@/stores/project";
import { useSubtitleAlignmentStore } from "@/stores/subtitle-alignment";
import type { SubtitleSegmentDto } from "@/types/runtime";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const projectStore = useProjectStore();
const store = useSubtitleAlignmentStore();

const currentProject = computed(() => projectStore.currentProject);
const currentProjectId = computed(() => currentProject.value?.projectId ?? "");
const currentProjectName = computed(() => currentProject.value?.projectName ?? "未选择项目");
const hasScript = computed(() => store.paragraphs.length > 0);
const hasSelectedTrack = computed(() => Boolean(store.selectedTrackId));
const hasBlockedTrack = computed(() => store.selectedTrack?.status === "blocked");
const presentationStatus = computed(() =>
  hasBlockedTrack.value && store.status === "ready" ? "blocked" : store.status
);

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
  if (store.status === "blocked" || hasBlockedTrack.value) return "重新尝试生成";
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

const pageStateLabel = computed(() => {
  const map: Record<string, string> = { blocked: "能力阻断", empty: "空态", error: "错误", loading: "加载中", ready: "已就绪" };
  return map[pageStateTone.value];
});

const scriptStateLabel = computed(() => {
  if (store.status === "loading") return "加载中";
  if (store.status === "error") return "异常";
  if (!hasScript.value) return "文案空";
  return "已就绪";
});

const styleStateLabel = computed(() => {
  if (store.status === "loading") return "加载中";
  if (store.status === "error") return "异常";
  if (store.status === "blocked" || hasBlockedTrack.value) return "需重新生成";
  return "可调整";
});

const versionStateLabel = computed(() => {
  if (store.status === "aligning") return "对齐中";
  if (store.status === "saving") return "保存中";
  if (store.status === "blocked" || hasBlockedTrack.value) return "需重新生成";
  if (store.status === "error") return "加载失败";
  if (!store.tracks.length) return "暂无版本";
  return "版本就绪";
});

const bannerTitle = computed(() => {
  if (!currentProject.value) return "字幕环境尚未就绪";
  if (store.status === "loading") return "正在读取项目状态";
  if (store.status === "error") return "字幕加载失败";
  if (!hasScript.value) return "文案缺失";
  if (store.status === "blocked" || hasBlockedTrack.value) return "对齐任务被阻塞";  
  if (store.status === "aligning") return "正在进行 AI 自动对齐";
  if (store.status === "saving") return "正在保存您的更改";
  return "字幕对齐环境已就绪";
});

const bannerMessage = computed(() => {
  if (!currentProject.value) return "请在侧边栏选择一个项目，以读取该项目的文案与字幕配置。";
  if (store.status === "loading") return "正在同步文案修订版本和现有字幕轨道，请稍等...";       
  if (store.status === "error") return store.error?.message ?? "字幕对齐中心遇到异常，请检查网络或后端状态。"; 
  if (!hasScript.value) return "文案中心尚无已采用的版本。请先前往脚本中心生成并采用脚本。";
  if (store.status === "blocked" || hasBlockedTrack.value) return store.generationResult?.message ?? "缺少可用的配音 Provider，或自动对齐服务未开启。";
  if (store.status === "aligning") return "正在通过 AI 分析配音音轨，为您自动切割和对齐字幕时间轴。";
  if (store.status === "saving") return "正在保存微调后的时间轴和样式设置...";
  return "您可以手动微调时间轴、更改样式设置，或重新生成对齐轨道。";
});

const panelStateMessage = computed(() => {
  if (!currentProject.value) return "环境未就绪";
  if (store.status === "loading") return "加载中";
  if (store.status === "error") return store.error?.message ?? "请求异常";
  if (!hasScript.value) return "文案缺失";
  if (store.status === "blocked" || hasBlockedTrack.value) return store.generationResult?.message ?? "任务阻断";
  if (store.status === "aligning") return "对齐中";
  if (store.status === "saving") return "保存中";
  return "准备就绪";
});

const timingLocked = computed(() => !currentProject.value || store.status === "loading" || store.status === "error" || !store.activeSegment);
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

watch(() => store.draftSegments.length, (count) => {
  if (count === 0) store.activeSegmentIndex = 0;
  else if (store.activeSegmentIndex >= count) store.activeSegmentIndex = 0;
});

onMounted(() => { loadProjectSubtitles(); });
watch(() => currentProject.value?.projectId, () => { loadProjectSubtitles(); });

async function loadProjectSubtitles() {
  const projectId = currentProjectId.value;
  if (!projectId) return;
  await store.load(projectId);
}

async function handleGenerate() {
  if (generateDisabled.value) return;
  await store.generate();
}

async function handleSave() {
  if (saveDisabled.value) return;
  await store.updateSelectedTrack();
}

function handleActiveSegmentUpdate(patch: Partial<SubtitleSegmentDto>) {
  store.updateDraftSegment(store.activeSegmentIndex, patch);
}
</script>

<style scoped>
.page-container {
  max-width: 1440px;
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
  border-color: rgba(255, 90, 99, 0.20);
  background: rgba(255, 90, 99, 0.08);
  color: var(--color-danger);
}

.dashboard-alert[data-tone="warning"] {
  border-color: rgba(245, 183, 64, 0.20);
  background: rgba(245, 183, 64, 0.08);
  color: var(--color-warning);
}

.dashboard-alert[data-tone="brand"] {
  border-color: rgba(0, 188, 212, 0.20);
  background: rgba(0, 188, 212, 0.08);
  color: var(--color-brand-primary);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.summary-card {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: transform var(--motion-fast) var(--ease-spring);
}

.summary-card:active {
  transform: scale(0.98);
}

.sc-label {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.sc-val {
  font: var(--font-title-md);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sc-hint {
  font: var(--font-caption);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

@keyframes spin { 100% { transform: rotate(360deg); } }

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
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-strong) transparent;
}

.subtitle-rail::-webkit-scrollbar {
  width: 4px;
}
.subtitle-rail::-webkit-scrollbar-thumb {
  background: var(--color-border-strong);
  border-radius: 99px;
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
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
