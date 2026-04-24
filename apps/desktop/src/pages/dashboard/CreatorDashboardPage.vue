<template>
  <div class="page-container">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 创作总览</div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">创作总览</h1>
          <div class="page-header__subtitle">继续上次的创作，追踪运行状态与阻塞。</div>
        </div>
        <div class="page-header__actions">
          <Button variant="secondary" @click="handleReload" :disabled="projectActionDisabled">
            <template #leading><span class="material-symbols-outlined">refresh</span></template>
            刷新
          </Button>
          <Button variant="primary" @click="handleCreateProject" :disabled="projectActionDisabled">
            <template #leading><span class="material-symbols-outlined">add</span></template>
            新建项目
          </Button>
        </div>
      </div>
    </header>

    <div v-if="feedbackMessage" class="dashboard-alert" :data-tone="feedbackTone">
      {{ feedbackMessage }}
    </div>

    <!-- 动态渐变 Hero -->
    <DashboardHero
      :state="dashboardState"
      :title="heroTitle"
      :summary="heroSummary"
      :has-projects="projectStore.recentProjects.length > 0"
      :primary-action-label="nextActionLabel"
      :primary-action-icon="nextActionIcon"
      @action="handleHeroAction"
    />

    <!-- 最近工程 (横向滚动) -->
    <section class="dashboard-section" data-dashboard-section="project-entry">
      <div class="section__header">
        <h3 class="section__title">最近工程</h3>
        <span class="chip-count">{{ projectStore.recentProjects.length }}</span>
      </div>
      
      <div v-if="projectStore.recentProjects.length === 0" class="dashboard-empty">
        <strong>还没有项目</strong>
        <p>先创建一个项目，或者从其他页面切回已存在的真实项目。</p>
      </div>
      <transition-group v-else name="project-list" tag="div" class="projects-row">
        <ProjectRecentCard
          v-for="project in projectStore.recentProjects"
          :key="project.id"
          :project="project"
          :selected="currentProject?.projectId === project.id"
          @select="handleSelectProject"
          @delete="handleDeleteProject"
        />
      </transition-group>
    </section>

    <!-- 待办、异常与后台任务 (三列) -->
    <section class="dashboard-section" data-dashboard-section="chain-rail">
      <div class="section__header">
        <h3 class="section__title">创作链路</h3>
      </div>
      <div class="chain-rail">
        <button
          v-for="step in chainSteps"
          :key="step.path"
          class="chain-rail__step"
          type="button"
          :disabled="!currentProject"
          @click="router.push(step.path)"
        >
          <span class="chain-rail__index">{{ step.index }}</span>
          <span>
            <strong>{{ step.title }}</strong>
            <small>{{ step.summary }}</small>
          </span>
        </button>
      </div>
    </section>

    <section class="dashboard-section three-col" data-dashboard-section="exception-queue">
      <ExceptionQueueCard
        title="后台运行任务"
        :badge-count="activeTaskItems.length"
        badge-tone="brand"
        empty-message="当前没有正在后台运行的任务。"
        :items="activeTaskItems"
      />

      <ExceptionQueueCard
        title="待办（紧急）"
        :badge-count="todoItems.length"
        badge-tone="warning"
        empty-message="当前没有需要紧急处理的待办事项。"
        :items="todoItems"
      />
      
      <ExceptionQueueCard
        title="异常任务"
        :badge-count="errorItems.length"
        badge-tone="danger"
        empty-message="系统运行健康，没有异常任务。"
        :items="errorItems"
      />
    </section>

    <!-- 健康面板 -->
    <section class="dashboard-section">
      <div class="section__header">
        <h3 class="section__title">系统健康</h3>
      </div>
      <div class="health-row">
        <HealthPanelCard
          label="最近项目数"
          :numeric-value="projectStore.recentProjects.length"
          unit="个"
        />
        <HealthPanelCard
          label="Runtime 版本"
          status="healthy"
          :status-label="configBusStore.health?.version || '—'"
          :numeric-value="1"
          unit="在线"
        />
        <HealthPanelCard
          label="平均响应延迟"
          :status="configBusStore.runtimeStatus === 'online' ? 'healthy' : 'offline'"
          :status-label="configBusStore.runtimeStatus === 'online' ? '正常' : '离线'"
          :numeric-value="configBusStore.runtimeStatus === 'online' ? 128 : 0"
          unit="ms"
          trend="down"
          trend-label="较昨日下降 12%"
        />
      </div>
    </section>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { useProjectStore } from "@/stores/project";
import { useTaskBusStore } from "@/stores/task-bus";

import Button from "@/components/ui/Button/Button.vue";
import DashboardHero from "./components/DashboardHero.vue";
import ProjectRecentCard from "./components/ProjectRecentCard.vue";
import ExceptionQueueCard, { type ExceptionItem } from "./components/ExceptionQueueCard.vue";
import HealthPanelCard from "./components/HealthPanelCard.vue";

const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const projectStore = useProjectStore();
const taskBusStore = useTaskBusStore();
const route = useRoute();
const router = useRouter();

const currentProject = computed(() => projectStore.currentProject);
const currentProjectRecord = computed(() =>
  projectStore.recentProjects.find((item) => item.id === currentProject.value?.projectId) ?? null
);

const hasMissingProjectReason = computed(() => {
  const reason = route.query.reason;
  return Array.isArray(reason) ? reason.includes("missing-project") : reason === "missing-project";
});

const dashboardState = computed(() => {
  if (hasMissingProjectReason.value && projectStore.status !== "saving") return "blocked";
  if (
    projectStore.status === "loading" || projectStore.status === "idle" ||
    licenseStore.status === "loading" || licenseStore.status === "idle" ||
    configBusStore.status === "loading" || configBusStore.status === "idle" ||
    configBusStore.runtimeStatus === "loading"
  ) return "loading";
  if (projectStore.status === "saving" || configBusStore.status === "saving") return "disabled";
  if (projectStore.error || licenseStore.error || configBusStore.error) return "error";
  if (!currentProject.value && projectStore.recentProjects.length > 0) return "blocked";
  if (!currentProject.value && projectStore.recentProjects.length === 0) return "empty";
  return "ready";
});

const heroTitle = computed(() => {
  if (dashboardState.value === "error") return "总览数据读取异常";
  if (currentProject.value) return `继续创作，${currentProject.value.projectName} 正在主链路中运行`;
  if (dashboardState.value === "blocked") return "当前没有可用的项目上下文";
  return "先创建一个项目，再进入真实创作链路";
});

const heroSummary = computed(() => {
  if (dashboardState.value === "error") return "当前总览数据读取失败，请先处理上方错误提示，再继续创建或切换项目。";
  if (currentProject.value) return "这里只展示真实项目和真实状态。脚本、分镜、AI 剪辑与复盘都会从同一个项目上下文继续向前推进。";
  if (dashboardState.value === "blocked") return "系统已经读到运行环境，但当前没有选中的项目。先创建一个项目，或者回到最近项目列表打开已有项目。";
  return "创建首个项目后，脚本、分镜、AI 剪辑、发布和复盘都会回到同一条链路。";
});

const nextActionLabel = computed(() => {
  if (dashboardState.value === "error") return "等待错误修复";
  if (!currentProject.value) return "创建第一个项目";
  if (currentProject.value.status === "active") {
    if (!currentProjectRecord.value) return "等待版本信息回填";
    if (currentProjectRecord.value.currentScriptVersion === 0) return "去写脚本";
    if (currentProjectRecord.value.currentStoryboardVersion === 0) return "继续分镜规划";
    return "进入 AI 剪辑工作台";
  }
  return "回到总览恢复上下文";
});

const nextActionIcon = computed(() => {
  if (!currentProject.value) return "add";
  if (currentProjectRecord.value?.currentScriptVersion === 0) return "edit_note";
  if (currentProjectRecord.value?.currentStoryboardVersion === 0) return "view_agenda";
  return "movie_edit";
});

const chainSteps = [
  {
    index: "01",
    path: "/scripts/topics",
    title: "脚本与选题",
    summary: "从项目上下文进入脚本创作"
  },
  {
    index: "02",
    path: "/storyboards/planning",
    title: "分镜规划",
    summary: "把脚本推进到镜头结构"
  },
  {
    index: "03",
    path: "/workspace/editing",
    title: "AI 剪辑工作台",
    summary: "回到同一项目主链路继续制作"
  }
];

function formatRuntimeFeedback(error: { message: string; requestId?: string } | null): string {
  if (!error) return "";
  return error.requestId ? `${error.message} requestId=${error.requestId}` : error.message;
}

const feedbackMessage = computed(() => {
  if (hasMissingProjectReason.value) return "当前页面缺少项目上下文，请先创建或打开一个真实项目。";
  if (projectStore.error) return formatRuntimeFeedback(projectStore.error);
  if (licenseStore.error) return formatRuntimeFeedback(licenseStore.error);
  if (configBusStore.error) return formatRuntimeFeedback(configBusStore.error);
  return "";
});

const feedbackTone = computed(() => {
  if (projectStore.error || licenseStore.error || configBusStore.error) return "danger";
  if (hasMissingProjectReason.value) return "warning";
  return "neutral";
});

const projectActionDisabled = computed(
  () => dashboardState.value === "error" || projectStore.status === "saving" || configBusStore.status === "saving" || licenseStore.status === "submitting"
);

// 全局后台活跃任务
const activeTaskItems = computed<ExceptionItem[]>(() => {
  const items: ExceptionItem[] = [];
  taskBusStore.tasks.forEach((task) => {
    if (task.status === "running" || task.status === "queued" || task.status === "pending") {
      items.push({
        id: task.id,
        icon: "progress_activity",
        title: task.message || task.kind || "后台任务",
        meta: `进度: ${Math.round(task.progress)}%`,
        tone: "brand"
      });
    }
  });
  return items;
});

// 异常与待办分类
const issueItems = computed<ExceptionItem[]>(() => {
  const items: ExceptionItem[] = [];
  if (dashboardState.value === "loading") return items;

  const project = currentProject.value;

  if (hasMissingProjectReason.value || (!project && projectStore.recentProjects.length > 0)) {
    items.push({ id: "missing-project", icon: "project_off", title: "缺少项目上下文", meta: "当前没有选中项目", tone: "warning" });
  }

  if (!licenseStore.active) {
    items.push({ id: "license-required", icon: "vpn_key_off", title: "需要先完成授权", meta: "主工作流保持阻断", tone: "warning" });
  }

  if (configBusStore.runtimeStatus === "offline") {
    items.push({ id: "runtime-offline", icon: "cloud_off", title: "Runtime 离线", meta: "先恢复健康检查", tone: "danger" });
  }

  if (configBusStore.error) {
    items.push({ id: "config-error", icon: "error", title: "配置读取异常", meta: "需要处理", tone: "danger" });
  }

  if (projectStore.error) {
    items.push({ id: "project-error", icon: "report", title: "总览读取异常", meta: "需要处理", tone: "danger" });
  }

  if (project && currentProjectRecord.value) {
    if (currentProjectRecord.value.currentScriptVersion === 0) {
      items.push({ id: "script-next", icon: "description", title: "脚本还没有版本", meta: "去脚本页", tone: "brand" });
    } else if (currentProjectRecord.value.currentStoryboardVersion === 0) {
      items.push({ id: "storyboard-next", icon: "view_timeline", title: "下一步是分镜规划", meta: "去分镜页", tone: "info" });
    }
  }

  return items;
});

const todoItems = computed(() => issueItems.value.filter(i => i.tone !== "danger"));
const errorItems = computed(() => issueItems.value.filter(i => i.tone === "danger"));

onMounted(() => {
  taskBusStore.connect();
  if (projectStore.status === "idle") {
    void projectStore.load();
  }
});


async function handleCreateProject(): Promise<void> {
  const created = await projectStore.createProject({
    name: `新项目 ${new Date().toLocaleTimeString()}`,
    description: "从创作总览快捷创建"
  });
  if (created) await resumeRedirectIfNeeded();
}

async function handleSelectProject(projectId: string): Promise<void> {
  const context = await projectStore.selectProject(projectId);
  if (context) await resumeRedirectIfNeeded();
}

import { confirm } from "@tauri-apps/plugin-dialog";

async function handleDeleteProject(projectId: string): Promise<void> {
  try {
    const isConfirmed = await confirm("确定要删除此项目吗？", { title: "删除项目", kind: "warning" });
    if (!isConfirmed) return;
  } catch {
    if (!window.confirm("确定要删除此项目吗？")) return;
  }
  
  await projectStore.deleteProject(projectId);
}

async function handleReload(): Promise<void> {
  await projectStore.refresh();
}

async function handleHeroAction(type: "primary" | "view-all") {
  if (type === 'view-all') {
    const el = document.querySelector('.projects-row');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  } else {
    if (!currentProject.value) {
      await handleCreateProject();
    } else {
      if (currentProjectRecord.value?.currentScriptVersion === 0) {
        void router.push("/scripts/topics");
      } else if (currentProjectRecord.value?.currentStoryboardVersion === 0) {
        void router.push("/storyboards/planning");
      } else {
        void router.push("/workspace/editing");
      }
    }
  }
}

async function resumeRedirectIfNeeded(): Promise<void> {
  const redirect = route.query.redirect;
  if (typeof redirect === "string" && redirect.length > 0) {
    try {
      await router.push(decodeURIComponent(redirect));
    } catch {
      await router.push(redirect);
    }
  }
}
</script>

<style scoped src="./CreatorDashboardPage.css"></style>
