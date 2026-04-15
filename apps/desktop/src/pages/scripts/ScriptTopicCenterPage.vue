<template>
  <ProjectContextGuard>
    <section class="workspace-page">
      <header class="workspace-page__header">
        <div>
          <p class="placeholder-page__eyebrow">创作主链 / 脚本</p>
          <h1>脚本与选题中心</h1>
          <p class="workspace-page__summary">
            当前项目下的脚本文档、AI 生成、改写和版本记录都从这里进入同一条创作链路。
          </p>
        </div>
        <div class="placeholder-page__meta">
          <span class="page-chip">
            {{ projectStore.currentProject?.projectName ?? "未选择项目" }}
          </span>
          <span class="page-chip page-chip--muted">
            {{ revisionLabel }}
          </span>
        </div>
      </header>

      <p v-if="scriptStore.error" class="settings-page__error">{{ errorSummary }}</p>

      <div class="workspace-grid">
        <section class="command-panel editor-card editor-card--wide">
          <div class="editor-card__header">
            <h2>脚本正文</h2>
            <button
              class="settings-page__button"
              type="button"
              data-action="save-script"
              :disabled="isDisabled"
              @click="handleSave"
            >
              保存脚本
            </button>
          </div>
          <textarea
            v-model="content"
            class="editor-textarea"
            data-field="script.content"
            :disabled="isDisabled"
          />
        </section>

        <section class="command-panel dashboard-card">
          <h2>AI 生成</h2>
          <label class="settings-field">
            <span>主题</span>
            <input v-model="topic" data-field="script.topic" :disabled="isDisabled" />
          </label>
          <button
            class="settings-page__button"
            type="button"
            data-action="generate-script"
            :disabled="isDisabled || topic.trim().length === 0"
            @click="handleGenerate"
          >
            生成脚本
          </button>

          <label class="settings-field">
            <span>改写要求</span>
            <textarea
              v-model="instructions"
              class="editor-textarea editor-textarea--compact"
              data-field="script.instructions"
              :disabled="isDisabled"
            />
          </label>
          <button
            class="dashboard-list__action"
            type="button"
            data-action="rewrite-script"
            :disabled="isDisabled || instructions.trim().length === 0"
            @click="handleRewrite"
          >
            改写当前版本
          </button>
        </section>

        <section class="command-panel dashboard-card">
          <h2>版本记录</h2>
          <div v-if="versions.length === 0" class="empty-state">当前项目还没有脚本版本。</div>
          <div v-else class="dashboard-list">
            <article v-for="version in versions" :key="version.revision" class="dashboard-list__item">
              <div>
                <h3>修订 {{ version.revision }}</h3>
                <p>{{ version.source }} · {{ version.model ?? "手动" }}</p>
                <p class="dashboard-list__meta">{{ version.createdAt }}</p>
              </div>
            </article>
          </div>
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
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { useProjectStore } from "@/stores/project";
import { useScriptStudioStore } from "@/stores/script-studio";

const projectStore = useProjectStore();
const scriptStore = useScriptStudioStore();
const { document } = storeToRefs(scriptStore);

const content = ref("");
const topic = ref("");
const instructions = ref("");

const isDisabled = computed(
  () => scriptStore.status === "loading" || scriptStore.status === "saving" || scriptStore.status === "generating"
);
const revisionLabel = computed(() =>
  document.value?.currentVersion ? `修订 ${document.value.currentVersion.revision}` : "修订 -"
);
const versions = computed(() => document.value?.versions ?? []);
const recentJobs = computed(() => document.value?.recentJobs ?? []);
const errorSummary = computed(() => {
  if (!scriptStore.error) {
    return "";
  }

  return scriptStore.error.requestId
    ? `${scriptStore.error.message}（${scriptStore.error.requestId}）`
    : scriptStore.error.message;
});

watch(
  document,
  (value) => {
    content.value = value?.currentVersion?.content ?? "";
  },
  { immediate: true }
);

onMounted(() => {
  if (projectStore.currentProject) {
    void scriptStore.load(projectStore.currentProject.projectId);
  }
});

async function handleSave(): Promise<void> {
  await scriptStore.save(content.value);
}

async function handleGenerate(): Promise<void> {
  await scriptStore.generate(topic.value.trim());
}

async function handleRewrite(): Promise<void> {
  await scriptStore.rewrite(instructions.value.trim());
}
</script>
