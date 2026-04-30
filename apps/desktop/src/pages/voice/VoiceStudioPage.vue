<template>
  <div class="page-container h-full">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 配音中心</div>
      <div class="page-header__row">
        <div class="page-header__copy">
          <h1 class="page-header__title">M07 配音中心</h1>
          <p class="page-header__subtitle">
            基于当前项目已采用的脚本文稿，为每一段文本选择角色并生成配音版本。
          </p>
        </div>
        <div class="page-header__actions">
          <Button
            variant="secondary"
            :disabled="!currentProjectId || store.status === 'loading'"
            @click="reloadVoiceStudio"
          >
            <template #leading><span class="material-symbols-outlined">refresh</span></template>
            {{ store.status === "loading" ? "加载中…" : "重新加载" }}
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

    <div v-if="pageStateTone === 'error'" class="dashboard-alert" data-tone="danger">
      <span class="material-symbols-outlined">error</span>
      <span>{{ bannerTitle }}：{{ bannerMessage }}</span>
    </div>
    <div v-else-if="pageStateTone === 'blocked'" class="dashboard-alert" data-tone="warning">
      <span class="material-symbols-outlined">warning</span>
      <span>{{ bannerTitle }}：{{ bannerMessage }}</span>
    </div>
    <div v-else-if="store.activeTask" class="dashboard-alert" data-tone="brand">
      <span class="material-symbols-outlined spinning">sync</span>
      <span>{{ store.activeTask.message }}（{{ store.activeTask.progress }}%）</span>
    </div>

    <div class="summary-grid">
      <Card class="summary-card">
        <span class="sc-label">当前项目</span>
        <strong class="sc-val">{{ currentProjectName }}</strong>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">文稿段落</span>
        <strong class="sc-val">{{ store.paragraphs.length }} 段</strong>
        <p class="sc-hint">{{ scriptStateLabel }}</p>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">配音角色</span>
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
      <strong>请先选择一个项目</strong>
      <p>配音中心依赖当前项目的脚本文稿，请先回到创作总览完成项目选择。</p>
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
        :generation-message="normalizedGenerationMessage"
        :selected-profile="selectedProfile"
        :selected-track="store.selectedTrack"
        :state-message="panelStateMessage"
        :status="presentationStatus"
      />

      <aside class="voice-rail">
        <VoiceProfileRail
          :error-message="store.error?.message ?? null"
          :profiles="store.profiles"
          :refreshing="store.profileSyncing"
          :selected-profile-id="store.selectedProfileId"
          :state-message="panelStateMessage"
          :status="presentationStatus"
          @refresh="store.refreshProfiles()"
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

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import VoiceParamsPanel from "@/modules/voice/VoiceParamsPanel.vue";
import VoicePreviewStage from "@/modules/voice/VoicePreviewStage.vue";
import VoiceProfileRail from "@/modules/voice/VoiceProfileRail.vue";
import VoiceScriptPanel from "@/modules/voice/VoiceScriptPanel.vue";
import VoiceVersionPanel from "@/modules/voice/VoiceVersionPanel.vue";
import { useProjectStore } from "@/stores/project";
import { useVoiceStudioStore } from "@/stores/voice-studio";

const projectStore = useProjectStore();
const store = useVoiceStudioStore();

const currentProject = computed(() => projectStore.currentProject);
const currentProjectId = computed(() => currentProject.value?.projectId ?? "");
const currentProjectName = computed(() => currentProject.value?.projectName ?? "未选择项目");
const selectedProfile = computed(() => store.selectedProfile);
const activeParagraph = computed(() => store.paragraphs[store.activeParagraphIndex] ?? null);
const hasBlockedTrack = computed(() => store.selectedTrack?.status === "blocked");
const normalizedGenerationMessage = computed(() =>
  normalizeBlockedProviderMessage(store.generationResult?.message ?? null)
);

const presentationStatus = computed(() => {
  return hasBlockedTrack.value && store.status === "ready" ? "blocked" : store.status;
});

const hasEnabledProfile = computed(() => Boolean(selectedProfile.value?.enabled));
const hasScript = computed(() => store.paragraphs.length > 0);

const generateDisabled = computed(() => {
  if (!currentProject.value) {
    return true;
  }
  if (store.status === "loading" || store.status === "generating" || store.status === "error") {
    return true;
  }
  return !hasScript.value || !hasEnabledProfile.value;
});

const generateButtonLabel = computed(() => {
  if (!currentProject.value) return "等待项目选择";
  if (store.status === "generating") return "生成中…";
  if (store.status === "blocked" || hasBlockedTrack.value || !hasEnabledProfile.value) {
    return "重新保存阻断草稿";
  }
  return "生成整片音轨";
});

const pageStateTone = computed(() => {
  if (!currentProject.value) return "blocked";
  if (store.status === "loading" || store.status === "generating") return "loading";
  if (store.status === "error") return "error";
  if (!hasScript.value) return "empty";
  if (!hasEnabledProfile.value) return "disabled";
  if (store.status === "blocked" || hasBlockedTrack.value) return "blocked";
  return "ready";
});

const scriptStateLabel = computed(() => {
  if (store.status === "loading") return "读取中";
  if (store.status === "error") return "加载失败";
  if (!hasScript.value) return "空状态";
  return "已解析";
});

const profileStateLabel = computed(() => {
  if (store.status === "loading") return "加载中";
  if (store.status === "error") return "异常";
  if (!selectedProfile.value) return "未选择";
  if (!selectedProfile.value.enabled) return "不可用";
  if (hasBlockedTrack.value) return "需要配置";
  return selectedProfile.value.displayName;
});

const versionStateLabel = computed(() => {
  if (store.status === "generating") return "生成中";
  if (store.status === "blocked" || hasBlockedTrack.value) return "等待能力接入";
  if (store.status === "error") return "加载失败";
  if (!store.tracks.length) return "暂无历史";
  return "历史就绪";
});

const bannerTitle = computed(() => {
  if (!currentProject.value) return "生成入口已锁定";
  if (store.status === "loading") return "正在读取配音环境";
  if (store.status === "error") return "配音中心出现异常";
  if (!hasScript.value) return "文稿缺失";
  if (!hasEnabledProfile.value) return "角色配置未开启";
  if (store.status === "blocked" || hasBlockedTrack.value) return "生成任务被阻断";
  if (store.status === "generating") return "正在生成音轨";
  return "音轨环境已就绪";
});

const bannerMessage = computed(() => {
  if (!currentProject.value) return "请先选择项目。";
  if (store.status === "loading") return "正在同步脚本文稿和历史音轨。";
  if (store.status === "error") return store.error?.message ?? "请求异常。";
  if (!hasScript.value) return "脚本文本为空。";
  if (!hasEnabledProfile.value) {
    return "当前没有可用的 TTS Provider，只会保留阻断草稿，不会生成真实音频。";
  }
  if (store.status === "blocked" || hasBlockedTrack.value) {
    return (
      normalizedGenerationMessage.value ??
      "已保存阻断草稿，但没有生成真实音频。"
    );
  }
  if (store.status === "generating") return "正在生成音轨，请稍候。";
  return "可以开始生成配音。";
});

const panelStateMessage = computed(() => {
  if (!currentProject.value) return "环境未就绪";
  if (store.status === "loading") return "加载中";
  if (store.status === "error") return store.error?.message ?? "请求异常";
  if (!hasScript.value) return "文稿缺失";
  if (!hasEnabledProfile.value) return "角色未配置";
  if (store.status === "blocked" || hasBlockedTrack.value) {
    return normalizedGenerationMessage.value ?? "需要先接入 Provider";
  }
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
  if (!hasScript.value) return "文稿缺失";
  if (!hasEnabledProfile.value) return "配音能力未配置";
  return "";
});

watch(
  () => store.paragraphs.length,
  (count) => {
    if (count === 0 || store.activeParagraphIndex >= count) {
      store.activeParagraphIndex = 0;
    }
  }
);

onMounted(() => {
  void loadProjectVoice();
});

watch(
  () => currentProject.value?.projectId,
  () => {
    void loadProjectVoice();
  }
);

async function loadProjectVoice(): Promise<void> {
  if (!currentProjectId.value) {
    return;
  }
  await store.load(currentProjectId.value);
}

async function reloadVoiceStudio(): Promise<void> {
  if (!currentProjectId.value) {
    return;
  }
  await store.load(currentProjectId.value);
}

async function handleGenerate(): Promise<void> {
  if (generateDisabled.value) {
    return;
  }
  await store.generate();
}

function normalizeBlockedProviderMessage(message: string | null): string | null {
  if (!message) {
    return null;
  }

  if (message.includes("TTS Provider") && message.includes("尚未配置可用")) {
    return "没有可用 TTS Provider，已保存阻断草稿，但没有生成真实音频。";
  }

  return message;
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

.page-header__copy {
  display: grid;
  gap: 4px;
}

.page-header__title {
  margin: 0;
  font: var(--font-display-md);
  letter-spacing: var(--ls-display-md);
  color: var(--color-text-primary);
}

.page-header__subtitle {
  margin: 0;
  font: var(--font-body-md);
  color: var(--color-text-secondary);
}

.page-header__actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
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

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}

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
  .page-header__row {
    flex-direction: column;
  }

  .voice-workspace {
    grid-template-columns: minmax(240px, 1fr) minmax(360px, 1fr);
  }

  .voice-rail {
    grid-column: 1 / -1;
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 860px) {
  .page-container {
    padding-inline: var(--space-4);
  }

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
