<template>
  <section class="workspace-page">
    <header class="workspace-page__header">
      <div>
        <p class="placeholder-page__eyebrow">创作主链入口</p>
        <h1>创作总览</h1>
        <p class="workspace-page__summary">
          项目上下文、Runtime 状态和许可证状态都从这里进入，不再散落到各页面首屏。
        </p>
      </div>
      <div class="placeholder-page__meta">
        <span class="page-chip">
          当前项目 {{ projectStore.currentProject?.projectName ?? "未选择" }}
        </span>
        <span class="page-chip page-chip--muted">
          最近项目 {{ projectStore.recentProjects.length }}
        </span>
      </div>
    </header>

    <p v-if="guardMessage" class="settings-page__error">{{ guardMessage }}</p>
    <p v-if="projectStore.error" class="settings-page__error">{{ projectErrorSummary }}</p>

    <div class="workspace-grid">
      <section class="placeholder-card dashboard-card">
        <h2>创建项目</h2>
        <label class="settings-field">
          <span>项目名称</span>
          <input v-model="projectName" data-field="project.name" :disabled="isBusy" />
        </label>
        <label class="settings-field">
          <span>项目描述</span>
          <textarea
            v-model="projectDescription"
            data-field="project.description"
            :disabled="isBusy"
          />
        </label>
        <button
          class="settings-page__button"
          type="button"
          data-action="create-project"
          :disabled="isBusy || projectName.trim().length === 0"
          @click="handleCreateProject"
        >
          创建并进入主链
        </button>
      </section>

      <section class="placeholder-card dashboard-card">
        <h2>最近项目</h2>
        <div v-if="projectStore.recentProjects.length === 0" class="empty-state">
          还没有项目。创建第一个项目后，脚本和分镜链路才会解锁。
        </div>
        <div v-else class="dashboard-list">
          <article
            v-for="project in projectStore.recentProjects"
            :key="project.id"
            class="dashboard-list__item"
            :data-project-id="project.id"
          >
            <div>
              <h3>{{ project.name }}</h3>
              <p>{{ project.description || "暂无描述" }}</p>
              <p class="dashboard-list__meta">
                脚本 v{{ project.currentScriptVersion }} · 分镜 v{{ project.currentStoryboardVersion }}
              </p>
            </div>
            <button
              class="dashboard-list__action"
              type="button"
              @click="handleSelectProject(project.id)"
            >
              打开
            </button>
          </article>
        </div>
      </section>

      <section class="placeholder-card dashboard-card">
        <h2>系统摘要</h2>
        <div class="dashboard-metric">
          <span>Runtime</span>
          <strong>{{ runtimeLabel }}</strong>
        </div>
        <div class="dashboard-metric">
          <span>许可证</span>
          <strong>{{ licenseLabel }}</strong>
        </div>
        <div class="dashboard-metric">
          <span>默认模型</span>
          <strong>{{ configBusStore.settings?.ai.model ?? "未加载" }}</strong>
        </div>
        <div class="dashboard-metric">
          <span>工作目录</span>
          <strong>{{ configBusStore.settings?.runtime.workspaceRoot ?? "未加载" }}</strong>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { useProjectStore } from "@/stores/project";

const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const projectStore = useProjectStore();
const route = useRoute();
const router = useRouter();

const projectName = ref("");
const projectDescription = ref("");

const isBusy = computed(() => projectStore.status === "loading" || projectStore.status === "saving");
const guardMessage = computed(() =>
  route.query.reason === "missing-project" ? "Project context required" : ""
);
const runtimeLabel = computed(() =>
  configBusStore.runtimeStatus === "online" ? "在线" : "离线"
);
const licenseLabel = computed(() => (licenseStore.active ? "已激活" : "受限模式"));
const projectErrorSummary = computed(() => {
  if (!projectStore.error) {
    return "";
  }

  return projectStore.error.requestId
    ? `${projectStore.error.message} (${projectStore.error.requestId})`
    : projectStore.error.message;
});

onMounted(() => {
  if (projectStore.status === "idle") {
    void projectStore.load();
  }
});

async function handleCreateProject(): Promise<void> {
  const created = await projectStore.createProject({
    name: projectName.value.trim(),
    description: projectDescription.value.trim()
  });
  if (!created) {
    return;
  }

  projectName.value = "";
  projectDescription.value = "";
  await resumeRedirectIfNeeded();
}

async function handleSelectProject(projectId: string): Promise<void> {
  const context = await projectStore.selectProject(projectId);
  if (!context) {
    return;
  }

  await resumeRedirectIfNeeded();
}

async function resumeRedirectIfNeeded(): Promise<void> {
  const redirect = resolveRedirectTarget(route.query.redirect);
  if (redirect) {
    await router.push(redirect);
  }
}

function resolveRedirectTarget(value: unknown): string {
  if (typeof value !== "string" || value.length === 0) {
    return "";
  }

  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
</script>
