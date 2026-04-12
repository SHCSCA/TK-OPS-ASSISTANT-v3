<template>
  <section class="workspace-page">
    <header class="workspace-page__header">
      <div>
        <p class="placeholder-page__eyebrow">创作主链 / 分镜</p>
        <h1>分镜规划中心</h1>
        <p class="workspace-page__summary">
          分镜版本固定挂在当前项目下，并显式标注所依据的脚本版本。
        </p>
      </div>
      <div class="placeholder-page__meta">
        <span class="page-chip">
          {{ projectStore.currentProject?.projectName ?? "未选择项目" }}
        </span>
        <span class="page-chip page-chip--muted">
          脚本引用 v{{ storyboardStore.document?.basedOnScriptRevision ?? "-" }}
        </span>
      </div>
    </header>

    <p v-if="storyboardStore.error" class="settings-page__error">{{ errorSummary }}</p>

    <div class="workspace-grid">
      <section class="command-panel editor-card editor-card--wide">
        <div class="editor-card__header">
          <h2>分镜卡片</h2>
          <div class="editor-card__actions">
            <button
              class="dashboard-list__action"
              type="button"
              data-action="generate-storyboard"
              :disabled="isDisabled"
              @click="handleGenerate"
            >
              生成分镜
            </button>
            <button
              class="settings-page__button"
              type="button"
              data-action="save-storyboard"
              :disabled="isDisabled || scenes.length === 0"
              @click="handleSave"
            >
              保存分镜
            </button>
          </div>
        </div>

        <div v-if="scenes.length === 0" class="empty-state">当前项目还没有分镜版本。</div>
        <div v-else class="scene-grid">
          <article v-for="scene in scenes" :key="scene.sceneId" class="scene-card">
            <label class="settings-field">
              <span>标题</span>
              <input v-model="scene.title" />
            </label>
            <label class="settings-field">
              <span>摘要</span>
              <textarea v-model="scene.summary" class="editor-textarea editor-textarea--compact" />
            </label>
            <label class="settings-field">
              <span>视觉提示</span>
              <textarea
                v-model="scene.visualPrompt"
                class="editor-textarea editor-textarea--compact"
              />
            </label>
          </article>
        </div>
      </section>

      <section class="command-panel dashboard-card">
        <h2>当前版本</h2>
        <div v-if="storyboardStore.document?.currentVersion">
          <p>
            修订 {{ storyboardStore.document.currentVersion.revision }} ·
            {{ storyboardStore.document.currentVersion.source }}
          </p>
          <p>
            {{ storyboardStore.document.currentVersion.provider ?? "手动" }} ·
            {{ storyboardStore.document.currentVersion.model ?? "-" }}
          </p>
        </div>
        <p v-else>还没有分镜版本。</p>
      </section>

      <section class="command-panel dashboard-card">
        <h2>最近 AI 作业</h2>
        <div v-if="recentJobs.length === 0" class="empty-state">还没有 AI 作业记录。</div>
        <div v-else class="dashboard-list">
          <article v-for="job in recentJobs" :key="job.id" class="dashboard-list__item">
            <div>
              <h3>{{ job.capabilityId }}</h3>
              <p>{{ job.provider }} · {{ job.model }}</p>
              <p class="dashboard-list__meta">{{ job.status }} · {{ job.createdAt }}</p>
            </div>
          </article>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { useProjectStore } from "@/stores/project";
import { useStoryboardStore } from "@/stores/storyboard";
import type { StoryboardScene } from "@/types/runtime";

const projectStore = useProjectStore();
const storyboardStore = useStoryboardStore();

const scenes = ref<StoryboardScene[]>([]);

const isDisabled = computed(
  () =>
    storyboardStore.status === "loading" ||
    storyboardStore.status === "saving" ||
    storyboardStore.status === "generating"
);
const recentJobs = computed(() => storyboardStore.document?.recentJobs ?? []);
const errorSummary = computed(() => {
  if (!storyboardStore.error) {
    return "";
  }

  return storyboardStore.error.requestId
    ? `${storyboardStore.error.message}（${storyboardStore.error.requestId}）`
    : storyboardStore.error.message;
});

watch(
  () => storyboardStore.document?.currentVersion?.scenes,
  (value) => {
    scenes.value = (value ?? []).map((scene) => ({ ...scene }));
  },
  { immediate: true }
);

onMounted(() => {
  if (projectStore.currentProject) {
    void storyboardStore.load(projectStore.currentProject.projectId);
  }
});

async function handleGenerate(): Promise<void> {
  await storyboardStore.generate();
}

async function handleSave(): Promise<void> {
  const basedOnScriptRevision =
    storyboardStore.document?.currentVersion?.basedOnScriptRevision ??
    storyboardStore.document?.basedOnScriptRevision ??
    1;
  await storyboardStore.save(basedOnScriptRevision, scenes.value);
}
</script>
