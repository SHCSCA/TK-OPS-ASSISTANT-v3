<template>
  <div class="voice-studio-page" data-testid="voice-studio-page">
    <header class="voice-toolbar">
      <div class="title-block">
        <span class="module-kicker">M07 配音中心</span>
        <h1>配音中心</h1>
        <p>把脚本段落组织成可追溯的配音版本，等待真实 TTS Provider 接入。</p>
      </div>

      <div class="toolbar-actions">
        <span class="project-pill">
          {{ currentProject?.projectName ?? "请先选择项目" }}
        </span>
        <button
          class="generate-button"
          data-testid="voice-generate-button"
          :disabled="!canGenerate"
          type="button"
          @click="handleGenerate"
        >
          {{ store.status === "generating" ? "生成中" : "生成配音版本" }}
        </button>
      </div>
    </header>

    <section v-if="!currentProject" class="guide-state">
      <strong>请先选择项目</strong>
      <span>配音中心需要读取当前项目的脚本文本后才能创建配音版本。</span>
    </section>

    <main v-else class="voice-workbench">
      <VoiceScriptPanel
        :active-index="store.activeParagraphIndex"
        :error-message="store.error?.message ?? null"
        :paragraphs="store.paragraphs"
        :status="store.status"
        @select="store.activeParagraphIndex = $event"
      />

      <VoicePreviewStage
        :active-paragraph="activeParagraph"
        :generation-message="store.generationResult?.message ?? null"
        :selected-track="store.selectedTrack"
        :status="store.status"
      />

      <aside class="right-rail">
        <VoiceProfileRail
          :profiles="store.profiles"
          :selected-profile-id="store.selectedProfileId"
          @select="store.selectProfile"
        />
        <VoiceParamsPanel
          :config="store.config"
          @update:config="store.config = $event"
        />
        <VoiceVersionPanel
          :selected-track-id="store.selectedTrackId"
          :tracks="store.tracks"
          @delete="store.deleteTrack"
          @select="store.selectTrack"
        />
      </aside>
    </main>
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

const projectStore = useProjectStore();
const store = useVoiceStudioStore();

const currentProject = computed(() => projectStore.currentProject);

const activeParagraph = computed(() => {
  return store.paragraphs[store.activeParagraphIndex] ?? null;
});

const canGenerate = computed(() => {
  return Boolean(
    currentProject.value &&
      store.paragraphs.length > 0 &&
      store.selectedProfileId &&
      store.status !== "loading" &&
      store.status !== "generating"
  );
});

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
  const projectId = currentProject.value?.projectId;
  if (!projectId) return;
  await store.load(projectId);
}

async function handleGenerate(): Promise<void> {
  await store.generate();
}
</script>

<style scoped>
.voice-studio-page {
  display: grid;
  grid-template-rows: auto 1fr;
  min-height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  overflow: hidden;
}

.voice-toolbar {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  padding: 26px 32px 22px;
  border-bottom: 1px solid var(--border-default);
  background:
    linear-gradient(115deg, color-mix(in srgb, var(--brand-primary) 10%, transparent), transparent 48%),
    var(--bg-elevated);
}

.title-block {
  display: grid;
  gap: 8px;
}

.module-kicker {
  color: var(--brand-primary);
  font-size: 13px;
  font-weight: 900;
}

h1 {
  margin: 0;
  color: var(--text-primary);
  font-size: 34px;
  line-height: 1;
}

.title-block p {
  max-width: 680px;
  margin: 0;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.7;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.project-pill {
  max-width: 260px;
  overflow: hidden;
  padding: 8px 11px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.generate-button {
  min-height: 40px;
  border: 0;
  border-radius: 8px;
  background: var(--brand-primary);
  color: #041414;
  cursor: pointer;
  font-size: 14px;
  font-weight: 900;
  padding: 0 18px;
}

.generate-button:disabled {
  cursor: not-allowed;
  opacity: 0.52;
}

.voice-workbench {
  display: grid;
  grid-template-columns: minmax(240px, 320px) minmax(420px, 1fr) minmax(260px, 340px);
  gap: 16px;
  min-height: 0;
  padding: 18px;
  overflow: hidden;
}

.right-rail {
  display: grid;
  align-content: start;
  gap: 12px;
  min-height: 0;
  overflow: auto;
}

.guide-state {
  display: grid;
  place-content: center;
  gap: 8px;
  padding: 48px;
  color: var(--text-secondary);
  text-align: center;
}

.guide-state strong {
  color: var(--text-primary);
  font-size: 22px;
}

@media (max-width: 1120px) {
  .voice-toolbar {
    align-items: start;
    flex-direction: column;
  }

  .toolbar-actions {
    justify-content: flex-start;
  }

  .voice-workbench {
    grid-template-columns: minmax(260px, 0.9fr) minmax(360px, 1.2fr);
    overflow: auto;
  }

  .right-rail {
    grid-column: 1 / -1;
    grid-template-columns: repeat(3, minmax(220px, 1fr));
  }
}

@media (max-width: 820px) {
  .voice-toolbar {
    padding: 22px 18px;
  }

  h1 {
    font-size: 28px;
  }

  .voice-workbench,
  .right-rail {
    grid-template-columns: 1fr;
  }
}
</style>
