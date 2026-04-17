<template>
  <section class="voice-page" data-testid="voice-studio-page">
    <header class="hero">
      <div class="hero__copy">
        <span class="hero__kicker">M07 配音中心</span>
        <h1>把脚本文本组织成可追溯的配音版本。</h1>
        <p>
          当前只保留真实脚本文本、真实 voice profiles 和真实配音版本记录。
          没有可用 TTS Provider 时，只保存阻断草稿，不会伪造音频成功结果。
        </p>
        <div class="hero__meta">
          <span class="pill pill--brand">{{ currentProjectName }}</span>
          <span class="pill" :data-state="pageStateTone">{{ pageStateLabel }}</span>
          <span class="pill">{{ store.paragraphs.length }} 段脚本</span>
          <span class="pill">{{ store.tracks.length }} 条配音版本</span>
        </div>
      </div>

      <div class="hero__actions">
        <button
          class="action-button action-button--primary"
          data-testid="voice-generate-button"
          :disabled="generateDisabled"
          type="button"
          @click="handleGenerate"
        >
          {{ generateButtonLabel }}
        </button>
        <button
          class="action-button action-button--secondary"
          :disabled="!currentProjectId || store.status === 'loading'"
          type="button"
          @click="reloadVoiceStudio"
        >
          {{ store.status === "loading" ? "刷新中" : "刷新工作台" }}
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
        <span>音色：{{ profileStateLabel }}</span>
        <span>版本：{{ versionStateLabel }}</span>
      </div>
    </section>

    <div v-if="!currentProject" class="guide-panel">
      <strong>请先选择项目</strong>
      <span>配音中心必须读取当前项目的脚本文本和版本记录后，才能进入真实工作台。</span>
    </div>

    <main v-else class="voice-workbench">
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

      <aside class="right-rail">
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
    </main>
  </section>
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

const projectStore = useProjectStore();
const store = useVoiceStudioStore();

const currentProject = computed(() => projectStore.currentProject);
const currentProjectId = computed(() => currentProject.value?.projectId ?? "");
const currentProjectName = computed(() => currentProject.value?.projectName ?? "当前项目未就绪");
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
  if (store.status === "generating") return "生成中";
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
  if (!currentProject.value) return "blocked";
  if (store.status === "loading") return "loading";
  if (store.status === "generating") return "loading";
  if (store.status === "error") return "error";
  if (!hasScript.value) return "empty";
  if (!hasEnabledProfile.value) return "disabled";
  if (store.status === "blocked" || hasBlockedTrack.value) return "blocked";
  return "ready";
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
  if (!currentProject.value) return "配音入口被阻断。";
  if (store.status === "loading") return "正在读取脚本、音色和配音版本。";
  if (store.status === "error") return "配音工作台读取失败。";
  if (!hasScript.value) return "脚本为空，无法生成配音版本。";
  if (!hasEnabledProfile.value) return "当前没有可用音色，生成入口保持锁定。";
  if (store.status === "blocked" || hasBlockedTrack.value) return "已保存阻断草稿，但没有生成真实音频。";
  if (store.status === "generating") return "正在生成配音版本。";
  return "脚本、音色和版本都已接通。";
});

const bannerMessage = computed(() => {
  if (!currentProject.value) {
    return "先选择真实项目，再读取脚本文本和 voice profiles。没有项目上下文时，不创建假音频和假版本。";
  }

  if (store.status === "loading") {
    return "脚本、音色和历史版本正在从 Runtime 拉取，当前只显示加载状态。";
  }

  if (store.status === "error") {
    return store.error?.message ?? "配音工作台读取失败，请稍后重试。";
  }

  if (!hasScript.value) {
    return "脚本文本为空，先在脚本与选题中心写入内容，再继续做配音版本。";
  }

  if (!hasEnabledProfile.value) {
    return "当前选中的音色不可用，生成入口会保持禁用，直到有可用 voice profile。";
  }

  if (store.status === "blocked" || hasBlockedTrack.value) {
    return store.generationResult?.message ?? "没有可用 TTS Provider，当前只保存阻断草稿，不生成真实音频。";
  }

  if (store.status === "generating") {
    return "正在把脚本文本整理成真实配音版本记录。";
  }

  return "脚本文本、voice profiles 和配音版本记录都来自真实 Runtime 返回值。";
});

const panelStateMessage = computed(() => {
  if (!currentProject.value) return "当前项目未就绪，工作台保持阻断。";
  if (store.status === "loading") return "正在读取 Runtime 数据。";
  if (store.status === "error") return store.error?.message ?? "读取失败。";
  if (!hasScript.value) return "脚本文本为空。";
  if (!hasEnabledProfile.value) return "当前没有可用音色，参数面板保持锁定。";
  if (store.status === "blocked" || hasBlockedTrack.value) {
    return store.generationResult?.message ?? "TTS Provider 未接通，当前版本为阻断草稿。";
  }
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

watch(
  () => store.paragraphs.length,
  (count) => {
    if (count === 0) {
      store.activeParagraphIndex = 0;
    } else if (store.activeParagraphIndex >= count) {
      store.activeParagraphIndex = 0;
    }
  }
);

onMounted(() => {
  loadProjectVoice();
});

watch(
  () => currentProject.value?.projectId,
  () => {
    loadProjectVoice();
  }
);

async function loadProjectVoice(): Promise<void> {
  const projectId = currentProjectId.value;
  if (!projectId) return;
  await store.load(projectId);
}

async function reloadVoiceStudio(): Promise<void> {
  if (!currentProjectId.value) return;
  await store.load(currentProjectId.value);
}

async function handleGenerate(): Promise<void> {
  if (generateDisabled.value) return;
  await store.generate();
}
</script>

<style scoped>
.voice-page {
  display: grid;
  gap: 16px;
  min-height: 100%;
  padding: 28px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 8%, transparent), transparent 36%),
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

.pill[data-state="disabled"] {
  border-color: var(--border-default);
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

.state-banner[data-state="disabled"] {
  border-color: color-mix(in srgb, var(--text-tertiary) 32%, transparent);
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
  gap: 8px;
  padding: 20px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
}

.guide-panel strong {
  font-size: 16px;
}

.voice-workbench {
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) minmax(420px, 1.3fr) minmax(280px, 0.8fr);
  gap: 16px;
  min-height: 0;
}

.right-rail {
  display: grid;
  align-content: start;
  gap: 12px;
  min-height: 0;
}

@media (max-width: 1160px) {
  .voice-page {
    padding: 20px;
  }

  .hero {
    flex-direction: column;
  }

  .voice-workbench {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 760px) {
  h1 {
    font-size: 28px;
  }
}
</style>
