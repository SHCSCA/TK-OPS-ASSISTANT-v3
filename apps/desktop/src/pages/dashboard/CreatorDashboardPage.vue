<template>
  <section class="dashboard-page">
    <header class="dashboard-header">
      <h1 class="dashboard-header__title">概览数据看板</h1>
      <p class="dashboard-header__subtitle">把脚本、分镜、剪辑与发布收束到同一个项目。</p>
    </header>

    <p v-if="guardMessage" class="settings-page__error">{{ guardMessage }}</p>
    <p v-if="projectStore.error" class="settings-page__error">{{ projectErrorSummary }}</p>

    <DashboardStatCards :project-count="projectStore.recentProjects.length" />

    <div class="dashboard-middle">
      <DashboardProjectEntry
        v-model:name="projectName"
        v-model:description="projectDescription"
        :is-busy="isBusy"
        @create="handleCreateProject"
      />

      <DashboardSystemStatus
        :config-status-label="configStatusLabel"
        :license-label="licenseLabel"
        :runtime-label="runtimeLabel"
      />
    </div>

    <DashboardRecentProjects
      :is-busy="isBusy"
      :label="recentProjectLabel"
      :projects="projectStore.recentProjects"
      @select="handleSelectProject"
    />

    <DashboardChainRail :has-project="projectStore.currentProject !== null" :steps="chainSteps" />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { useProjectStore } from "@/stores/project";

import DashboardChainRail from "./components/DashboardChainRail.vue";
import DashboardProjectEntry from "./components/DashboardProjectEntry.vue";
import DashboardRecentProjects from "./components/DashboardRecentProjects.vue";
import DashboardStatCards from "./components/DashboardStatCards.vue";
import DashboardSystemStatus from "./components/DashboardSystemStatus.vue";

const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const projectStore = useProjectStore();
const route = useRoute();
const router = useRouter();

const projectName = ref("");
const projectDescription = ref("");

const chainSteps = [
  {
    index: "01",
    path: "/scripts/topics",
    title: "脚本与选题",
    summary: "生成脚本、标题和文案版本。"
  },
  {
    index: "02",
    path: "/storyboards/planning",
    title: "分镜规划",
    summary: "把脚本结构转成镜头节奏。"
  },
  {
    index: "03",
    path: "/workspace/editing",
    title: "AI 剪辑工作台",
    summary: "汇总视频、音轨、字幕和时间线。"
  },
  {
    index: "04",
    path: "/renders/export",
    title: "渲染与导出",
    summary: "输出可发布的项目版本。"
  }
];

const isBusy = computed(() => projectStore.status === "loading" || projectStore.status === "saving");
const recentProjectLabel = computed(() =>
  projectStore.recentProjects.length > 0 ? `${projectStore.recentProjects.length} 个真实项目` : "空态"
);
const guardMessage = computed(() =>
  route.query.reason === "missing-project" ? "请先创建或打开项目，再继续进入该页面。" : ""
);
const runtimeLabel = computed(() =>
  configBusStore.runtimeStatus === "online"
    ? "在线"
    : configBusStore.runtimeStatus === "loading"
      ? "检查中"
      : "离线"
);
const licenseLabel = computed(() => (licenseStore.active ? "已激活" : "需要授权"));
const configStatusLabel = computed(() => {
  switch (configBusStore.status) {
    case "ready":
      return "已就绪";
    case "loading":
      return "读取中";
    case "saving":
      return "保存中";
    case "error":
      return "异常";
    default:
      return "待加载";
  }
});
const projectErrorSummary = computed(() => {
  if (!projectStore.error) {
    return "";
  }

  return projectStore.error.requestId
    ? `${projectStore.error.message}（${projectStore.error.requestId}）`
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
