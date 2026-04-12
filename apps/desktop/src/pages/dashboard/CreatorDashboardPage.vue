<template>
  <section class="dashboard-page command-dashboard">
    <header class="dashboard-hero command-dashboard__hero">
      <div class="dashboard-hero__content">
        <p class="dashboard-hero__eyebrow">创作总览</p>
        <h1>把脚本、分镜、剪辑与发布收束到同一个项目。</h1>
        <p>
          从这里创建项目、恢复最近工作，并检查 Runtime、许可证与 AI 默认配置是否已经就绪。
          当前页只展示真实状态；没有数据时会使用明确空态，不制造假业务数字。
        </p>
        <div class="dashboard-hero__actions">
          <a class="settings-page__button" href="#create-project">创建新项目</a>
          <RouterLink class="settings-page__button settings-page__button--secondary" to="/settings/ai-system">
            检查 AI 与系统设置
          </RouterLink>
        </div>
      </div>

      <aside class="command-signal" aria-label="当前项目状态">
        <span class="command-signal__ring"></span>
        <p>当前项目</p>
        <strong>{{ currentProjectName }}</strong>
        <small>{{ currentProjectStatus }}</small>
      </aside>
    </header>

    <p v-if="guardMessage" class="settings-page__error">{{ guardMessage }}</p>
    <p v-if="projectStore.error" class="settings-page__error">{{ projectErrorSummary }}</p>

    <div class="dashboard-command-grid command-dashboard__grid">
      <section id="create-project" class="command-panel command-panel--primary project-entry-card">
        <div>
          <p class="detail-panel__label">项目入口</p>
          <h2>创建新的创作项目</h2>
          <p class="workspace-page__summary">
            项目会成为脚本、分镜、时间线、配音、字幕和渲染任务的统一上下文。
          </p>
        </div>

        <label class="settings-field">
          <span>项目名称</span>
          <input
            v-model="projectName"
            data-field="project.name"
            :disabled="isBusy"
            placeholder="例如：TikTok 新品短视频首发"
          />
        </label>
        <label class="settings-field">
          <span>项目描述</span>
          <textarea
            v-model="projectDescription"
            data-field="project.description"
            :disabled="isBusy"
            placeholder="写下目标受众、创作方向或需要 AI 优先理解的背景。"
          />
        </label>
        <button
          class="settings-page__button"
          type="button"
          data-action="create-project"
          :disabled="isBusy || projectName.trim().length === 0"
          @click="handleCreateProject"
        >
          创建并进入主链路
        </button>
      </section>

      <section class="command-panel recent-project-card">
        <div class="command-panel__title-row">
          <div>
            <p class="detail-panel__label">最近项目</p>
            <h2>继续已有创作</h2>
          </div>
          <span class="page-chip page-chip--muted">{{ recentProjectLabel }}</span>
        </div>

        <div v-if="projectStore.recentProjects.length === 0" class="empty-state empty-state--guide">
          <strong>还没有项目。</strong>
          <p>创建第一个项目后，脚本、分镜和媒体链路会按项目上下文解锁。</p>
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
              <p class="dashboard-list__meta">{{ formatProjectMeta(project) }}</p>
            </div>
            <button
              class="dashboard-list__action"
              type="button"
              :disabled="isBusy"
              @click="handleSelectProject(project.id)"
            >
              打开
            </button>
          </article>
        </div>
      </section>

      <section class="command-panel command-panel--wide chain-card">
        <div class="command-panel__title-row">
          <div>
            <p class="detail-panel__label">创作链路</p>
            <h2>{{ projectStore.currentProject ? "下一步动作" : "等待项目上下文" }}</h2>
          </div>
          <span class="page-chip page-chip--muted">Project -> Script -> Storyboard -> Timeline</span>
        </div>

        <div class="chain-rail chain-rail--command">
          <RouterLink
            v-for="step in chainSteps"
            :key="step.path"
            class="chain-step"
            :to="step.path"
          >
            <span>{{ step.index }}</span>
            <strong>{{ step.title }}</strong>
            <p>{{ step.summary }}</p>
          </RouterLink>
        </div>
      </section>

      <section class="command-panel system-card">
        <p class="detail-panel__label">运行与授权</p>
        <div class="dashboard-metric">
          <span>Runtime</span>
          <strong>{{ runtimeLabel }}</strong>
        </div>
        <div class="dashboard-metric">
          <span>许可证</span>
          <strong>{{ licenseLabel }}</strong>
        </div>
        <div class="dashboard-metric">
          <span>配置状态</span>
          <strong>{{ configStatusLabel }}</strong>
        </div>
      </section>

      <section class="command-panel system-card">
        <p class="detail-panel__label">AI 默认项</p>
        <div class="dashboard-metric">
          <span>Provider</span>
          <strong>{{ configBusStore.settings?.ai.provider ?? "待加载" }}</strong>
        </div>
        <div class="dashboard-metric">
          <span>模型</span>
          <strong>{{ configBusStore.settings?.ai.model ?? "待加载" }}</strong>
        </div>
        <div class="dashboard-metric">
          <span>工作目录</span>
          <strong>{{ configBusStore.settings?.runtime.workspaceRoot ?? "待加载" }}</strong>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { useProjectStore } from "@/stores/project";
import type { ProjectSummary } from "@/types/runtime";

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
const currentProjectName = computed(() => projectStore.currentProject?.projectName ?? "等待项目");
const currentProjectStatus = computed(() => projectStore.currentProject?.status ?? "请先创建或打开项目");
const recentProjectLabel = computed(() =>
  projectStore.recentProjects.length > 0 ? `${projectStore.recentProjects.length} 个真实项目` : "空态"
);
const guardMessage = computed(() =>
  route.query.reason === "missing-project" ? "请先创建或打开项目，再继续进入该页面。" : ""
);
const runtimeLabel = computed(() =>
  configBusStore.runtimeStatus === "online" ? "在线" : configBusStore.runtimeStatus === "loading" ? "检查中" : "离线"
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

function formatProjectMeta(project: ProjectSummary): string {
  return `脚本 v${project.currentScriptVersion} / 分镜 v${project.currentStoryboardVersion} / ${project.status}`;
}
</script>
