<template>
  <div class="page-container h-full">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 创作与媒体</div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">配音中心</h1>
          <div class="page-header__subtitle">把脚本文本组织成可追溯的配音版本。</div>
        </div>
        <div class="page-header__actions">
          <Button variant="secondary" :disabled="!currentProjectId || store.status === 'loading'" @click="reloadVoiceStudio">
            <template #leading><span class="material-symbols-outlined">refresh</span></template>
            {{ store.status === "loading" ? "刷新中..." : "重新读取" }}
          </Button>
          <Button variant="ai" :running="store.status === 'generating'" :disabled="generateDisabled" @click="handleGenerate">
            <template #leading><span class="material-symbols-outlined">auto_awesome</span></template>
            {{ generateButtonLabel }}
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
    <div v-else-if="pageStateTone === 'loading'" class="dashboard-alert" data-tone="brand">
      <span class="material-symbols-outlined spinning">sync</span>
      <span>{{ bannerTitle }} - {{ bannerMessage }}</span>
    </div>

    <div class="summary-grid">
      <Card class="summary-card">
        <span class="sc-label">当前项目</span>
        <strong class="sc-val">{{ currentProjectName }}</strong>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">脚本段落</span>
        <strong class="sc-val">{{ store.paragraphs.length }} 段</strong>
        <p class="sc-hint">{{ scriptStateLabel }}</p>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">音色状态</span>
        <strong class="sc-val">{{ profileStateLabel }}</strong>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">配音版本</span>
        <strong class="sc-val">{{ store.tracks.length }} 条</strong>
        <p class="sc-hint">{{ versionStateLabel }}</p>
      </Card>
    </div>

    <div v-if="!currentProject" class="empty-state">
      <span class="material-symbols-outlined">mic_off</span>
      <strong>请先选择项目</strong>
      <p>配音中心必须读取当前项目的脚本文本和版本记录后，才能进入真实工作台。</p>
    </div>

    <div v-else class="voice-workspace">
      <VoiceScriptPanel
        :active-index="store.activeParagraphIndex"
        :error-message="store.error?.message ?? null"
        :paragraphs="store.paragraphs"
        :state-message="panelStateMessage"
        :status="presentationStatus"
        @select="store.activeParagraphIndex = $event"
      />

      <VoicePreviewStage
        :active-paragraph="activeParagraph"
        :generation-message="store.generationResult?.message ?? null"
        :selected-profile="selectedProfile"
        :selected-track="store.selectedTrack"
        :state-message="panelStateMessage"
        :status="presentationStatus"
      />

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
  if (!currentProject.value) return "生成入口已锁定";
  if (store.status === "generating") return "生成中...";
  if (store.status === "blocked" || hasBlockedTrack.value) return "重新保存阻断草稿";
  if (!hasEnabledProfile.value) return "音色未就绪";
  return "生成配音版本";
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
  const map: Record<string, string> = { blocked: "能力阻断", empty: "空态", error: "错误", loading: "加载中", ready: "已就绪", disabled: "不可用" };
  return map[pageStateTone.value];
});

const scriptStateLabel = computed(() => {
  if (store.status === "loading") return "读取中";
  if (store.status === "error") return "异常";
  if (!hasScript.value) return "空态";
  return "已读取";
});

const profileStateLabel = computed(() => {
  if (store.status === "loading") return "读取中";
  if (store.status === "error") return "异常";
  if (!selectedProfile.value) return "未选中";
  if (!selectedProfile.value.enabled) return "已禁用";
  if (hasBlockedTrack.value) return "阻断";
  return "可用";
});

const versionStateLabel = computed(() => {
  if (store.status === "generating") return "生成中";
  if (store.status === "blocked" || hasBlockedTrack.value) return "阻断草稿";
  if (store.status === "error") return "异常";
  if (!store.tracks.length) return "空态";
  return "已保存";
});

const bannerTitle = computed(() => {
  if (!currentProject.value) return "配音入口被阻断";
  if (store.status === "loading") return "正在同步上下文";
  if (store.status === "error") return "配音工作台读取失败";
  if (!hasScript.value) return "脚本为空";
  if (!hasEnabledProfile.value) return "音色不可用";
  if (store.status === "blocked" || hasBlockedTrack.value) return "仅保存阻断草稿";
  if (store.status === "generating") return "正在生成音频";
  return "配音服务已就绪";
});

const bannerMessage = computed(() => {
  if (!currentProject.value) return "先选择真实项目，再读取脚本文本和音色。";
  if (store.status === "loading") return "脚本、音色和历史版本正在从 Runtime 拉取。";
  if (store.status === "error") return store.error?.message ?? "配音工作台读取失败，请稍后重试。";
  if (!hasScript.value) return "脚本文本为空，先在脚本与选题中心写入内容，再继续做配音版本。";
  if (!hasEnabledProfile.value) return "当前选中的音色不可用，生成入口会保持禁用，直到有可用音色。";
  if (store.status === "blocked" || hasBlockedTrack.value) return store.generationResult?.message ?? "没有可用 TTS Provider，当前只保存阻断草稿，不生成真实音频。";
  if (store.status === "generating") return "正在把脚本文本整理成真实配音版本记录。";
  return "脚本、音色和配音版本记录都来自真实 Runtime 返回值。";
});

const panelStateMessage = computed(() => {
  if (!currentProject.value) return "当前项目未就绪，工作台保持阻断。";
  if (store.status === "loading") return "正在读取 Runtime 数据。";
  if (store.status === "error") return store.error?.message ?? "读取失败。";
  if (!hasScript.value) return "脚本文本为空。";
  if (!hasEnabledProfile.value) return "当前没有可用音色，参数面板保持锁定。";
  if (store.status === "blocked" || hasBlockedTrack.value) return store.generationResult?.message ?? "TTS Provider 未接通，当前版本为阻断草稿。";
  if (store.status === "generating") return "正在生成配音版本。";
  return "真实音色和版本记录已接通。";
});

const parameterLocked = computed(() => {
  if (!currentProject.value) return true;
  if (store.status === "loading" || store.status === "error") return true;
  return !hasScript.value || !hasEnabledProfile.value;
});

const parameterLockedReason = computed(() => {
  if (!currentProject.value) return "请先选择项目。";
  if (store.status === "loading") return "正在读取脚本和音色列表。";
  if (store.status === "error") return store.error?.message ?? "读取失败。";
  if (!hasScript.value) return "脚本文本为空。";
  if (!hasEnabledProfile.value) return "没有可用音色，参数暂不可编辑。";
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
