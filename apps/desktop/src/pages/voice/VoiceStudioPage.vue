<template>
  <div class="page-container h-full">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 媒体工作室</div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">M07 配音中心</h1>          <div class="page-header__subtitle">基于已采用的文案修订版本，为每一段文案配置专属的 AI 角色与音轨参数。</div>
        </div>
        <div class="page-header__actions">
          <Button variant="secondary" :disabled="!currentProjectId || store.status === 'loading'" @click="reloadVoiceStudio">
            <template #leading><span class="material-symbols-outlined">refresh</span></template>
            {{ store.status === "loading" ? "加载中..." : "重新加载" }}
          </Button>
          <Button
            variant="ai"
            data-testid="voice-generate-button"
            :running="store.status === 'generating'"
            :disabled="generateDisabled"
            @click="handleGenerate"
          >
            <template #leading><span class="material-symbols-outlined">auto_awesome</span></template>
            {{ generateButtonLabel }}
          </Button>
        </div>
      </div>
    </header>

    <!-- 顶部警告与状态横幅 -->
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

    <!-- 概览指标卡片 -->
    <div class="summary-grid">
      <Card class="summary-card">
        <span class="sc-label">当前项目</span>
        <strong class="sc-val">{{ currentProjectName }}</strong>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">文案段落</span>
        <strong class="sc-val">{{ store.paragraphs.length }} 段</strong>
        <p class="sc-hint">{{ scriptStateLabel }}</p>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">配音角色</span>
        <strong class="sc-val">{{ profileStateLabel }}</strong>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">配音音轨</span>
        <strong class="sc-val">{{ store.tracks.length }} 条</strong>
        <p class="sc-hint">{{ versionStateLabel }}</p>
      </Card>
    </div>

    <!-- 空状态 -->
    <div v-if="!currentProject" class="empty-state">
      <span class="material-symbols-outlined">mic_off</span>
      <strong>请先选择一个项目</strong>
      <p>配音工作室基于当前项目已采用的文案修订版本。请先前往策划中心完成创作。</p> 
    </div>

    <!-- 主工作区 -->
    <div v-else class="voice-workspace">
      <!-- 段落选择器 -->
      <VoiceScriptPanel
        :active-index="store.activeParagraphIndex"
        :error-message="store.error?.message ?? null"
        :paragraphs="store.paragraphs"
        :state-message="panelStateMessage"
        :status="presentationStatus"
        @select="store.activeParagraphIndex = $event"
      />

      <!-- 预览与试听 -->
      <VoicePreviewStage
        :active-paragraph="activeParagraph"
        :generation-message="store.generationResult?.message ?? null"
        :selected-profile="selectedProfile"
        :selected-track="store.selectedTrack"
        :state-message="panelStateMessage"
        :status="presentationStatus"
      />

      <!-- 参数与版本导轨 -->
      <aside class="voice-rail">
        <VoiceProfileRail
          :error-message="store.error?.message ?? null"
          :profiles="store.profiles"
          :selected-profile-id="store.selectedProfileId"
          :state-message="panelStateMessage"
          :status="presentationStatus"
          @select="store.selectProfile"
        />
        <VoiceParamsPanel
          :config="store.config"
          :locked="parameterLocked"
          :locked-reason="parameterLockedReason"
          @update:config="store.config = $event"
        />
        <VoiceVersionPanel
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

import VoiceParamsPanel from "@/modules/voice/VoiceParamsPanel.vue";
import VoicePreviewStage from "@/modules/voice/VoicePreviewStage.vue";
import VoiceProfileRail from "@/modules/voice/VoiceProfileRail.vue";
import VoiceScriptPanel from "@/modules/voice/VoiceScriptPanel.vue";
import VoiceVersionPanel from "@/modules/voice/VoiceVersionPanel.vue";
import { useProjectStore } from "@/stores/project";
import { useVoiceStudioStore } from "@/stores/voice-studio";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const projectStore = useProjectStore();
const store = useVoiceStudioStore();

const currentProject = computed(() => projectStore.currentProject);
const currentProjectId = computed(() => currentProject.value?.projectId ?? "");
const currentProjectName = computed(() => currentProject.value?.projectName ?? "未选择项目");
const selectedProfile = computed(() => store.selectedProfile);
const activeParagraph = computed(() => store.paragraphs[store.activeParagraphIndex] ?? null);
const hasBlockedTrack = computed(() => store.selectedTrack?.status === "blocked");
const presentationStatus = computed(() =>
  hasBlockedTrack.value && store.status === "ready" ? "blocked" : store.status
);

const hasEnabledProfile = computed(() => Boolean(selectedProfile.value?.enabled));
const hasScript = computed(() => store.paragraphs.length > 0);

const generateDisabled = computed(() => {
  if (!currentProject.value) return true;
  if (store.status === "loading" || store.status === "generating" || store.status === "error") {
    return true;
  }
  return !hasScript.value || !hasEnabledProfile.value;
});

const generateButtonLabel = computed(() => {
  if (!currentProject.value) return "等待项目选择";
  if (store.status === "generating") return "生成中...";
  if (store.status === "blocked" || hasBlockedTrack.value) return "重新保存阻断草稿";
  if (!hasEnabledProfile.value) return "重新保存阻断草稿";
  return "生成全片音轨";
});

const pageStateTone = computed(() => {
  if (!currentProject.value) return "blocked";
  if (store.status === "loading") return "loading";
  if (store.status === "generating") return "loading";
  if (store.status === "error") return "error";
  if (!hasScript.value) return "empty";
  if (!hasEnabledProfile.value) return "disabled";
  if (store.status === "blocked" || hasBlockedTrack.value) return "blocked";
  return "ready";
});

const pageStateLabel = computed(() => {
  const map: Record<string, string> = { blocked: "能力阻断", empty: "空态", error: "错误", loading: "加载中", ready: "已就绪", disabled: "服务禁用" };
  return map[pageStateTone.value];
});

const scriptStateLabel = computed(() => {
  if (store.status === "loading") return "读取中";
  if (store.status === "error") return "加载失败";
  if (!hasScript.value) return "空态";
  return "已解析";
});

const profileStateLabel = computed(() => {
  if (store.status === "loading") return "加载中";
  if (store.status === "error") return "异常";
  if (!selectedProfile.value) return "未选择";
  if (!selectedProfile.value.enabled) return "不可用";
  if (hasBlockedTrack.value) return "需要配置";
  return selectedProfile.value.name;
});

const versionStateLabel = computed(() => {
  if (store.status === "generating") return "生成中";
  if (store.status === "blocked" || hasBlockedTrack.value) return "重新尝试生成";
  if (store.status === "error") return "加载失败";
  if (!store.tracks.length) return "暂无历史";
  return "历史就绪";
});

const bannerTitle = computed(() => {
  if (!currentProject.value) return "生成入口已锁定";
  if (store.status === "loading") return "正在读取环境配置";
  if (store.status === "error") return "配音工作室遇到异常";
  if (!hasScript.value) return "文案缺失";
  if (!hasEnabledProfile.value) return "角色配置未开启";
  if (store.status === "blocked" || hasBlockedTrack.value) return "生成任务被阻塞";
  if (store.status === "generating") return "正在生成音轨";
  return "音轨环境已就绪";
});

const bannerMessage = computed(() => {
  if (!currentProject.value) return "请先选择项目";
  if (store.status === "loading") return "正在同步文案修订版本和历史音轨...";
  if (store.status === "error") return store.error?.message ?? "请求异常";
  if (!hasScript.value) return "脚本文本为空";
  if (!hasEnabledProfile.value) return "没有可用 TTS Provider，但会保存阻断草稿，不会生成真实音频。";
  if (store.status === "blocked" || hasBlockedTrack.value) {
    const msg = store.generationResult?.message || "";
    const base = "已保存阻断草稿，但没有生成真实音频。";
    if (msg.includes("尚未配置")) return msg.replace("尚未配置", "没有") + " " + base;
    return msg || base;
  }
  if (store.status === "generating") return "正在生成音轨...";
  return "准备就绪";
});

const panelStateMessage = computed(() => {
  if (!currentProject.value) return "环境未就绪";
  if (store.status === "loading") return "加载中";
  if (store.status === "error") return store.error?.message ?? "请求异常";
  if (!hasScript.value) return "文案缺失";
  if (!hasEnabledProfile.value) return "角色未配置";
  if (store.status === "blocked" || hasBlockedTrack.value) return store.generationResult?.message ?? "需要配置 Provider";
  if (store.status === "generating") return "生成中";
  return "准备就绪";
});

const parameterLocked = computed(() => {
  if (!currentProject.value) return true;
  if (store.status === "loading" || store.status === "error") return true;
  return !hasScript.value || !hasEnabledProfile.value;
});

const parameterLockedReason = computed(() => {
  if (!currentProject.value) return "未选择项目";
  if (store.status === "loading") return "加载中";
  if (store.status === "error") return store.error?.message ?? "加载失败";
  if (!hasScript.value) return "文案缺失";
  if (!hasEnabledProfile.value) return "配音能力未配置";
  return "";
});

watch(() => store.paragraphs.length, (count) => {
  if (count === 0) store.activeParagraphIndex = 0;
  else if (store.activeParagraphIndex >= count) store.activeParagraphIndex = 0;
});

onMounted(() => { loadProjectVoice(); });
watch(() => currentProject.value?.projectId, () => { loadProjectVoice(); });

async function loadProjectVoice() {
  const projectId = currentProjectId.value;
  if (!projectId) return;
  await store.load(projectId);
}

async function reloadVoiceStudio() {
  if (!currentProjectId.value) return;
  await store.load(currentProjectId.value);
}

async function handleGenerate() {
  if (generateDisabled.value) return;
  await store.generate();
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

.voice-workspace {
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) minmax(420px, 1.35fr) minmax(280px, 0.8fr);
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
}

.voice-rail {
  display: grid;
  align-content: start;
  gap: var(--space-4);
  min-height: 0;
  overflow-y: auto;
}

@media (max-width: 1200px) {
  .voice-workspace {
    grid-template-columns: minmax(240px, 1fr) minmax(360px, 1fr);
  }
  .voice-rail {
    grid-column: 1 / -1;
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 860px) {
  .voice-workspace {
    grid-template-columns: 1fr;
  }
  .voice-rail {
    grid-template-columns: 1fr;
  }
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
