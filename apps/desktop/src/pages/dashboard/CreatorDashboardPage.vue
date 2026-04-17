<template>
  <section class="dashboard-page" :data-dashboard-state="dashboardState">
    <header class="dashboard-hero" data-dashboard-section="hero">
      <div class="dashboard-hero__copy">
        <p class="dashboard-hero__eyebrow">创作总览</p>
        <h1>{{ heroTitle }}</h1>
        <p class="dashboard-hero__summary">{{ heroSummary }}</p>

        <div class="dashboard-hero__badges">
          <span class="status-chip" :data-tone="licenseTone">{{ licenseLabel }}</span>
          <span class="status-chip" :data-tone="runtimeTone">{{ runtimeLabel }}</span>
          <span class="status-chip" :data-tone="configTone">{{ configLabel }}</span>
          <span class="status-chip" :data-tone="projectTone">{{ projectLabel }}</span>
        </div>
      </div>

      <div class="dashboard-hero__panel">
        <article class="dashboard-hero-card">
          <p class="dashboard-hero-card__label">当前项目</p>
          <strong>{{ currentProject?.projectName || "尚未选择" }}</strong>
          <p>{{ currentProjectHint }}</p>
        </article>
        <article class="dashboard-hero-card dashboard-hero-card--muted">
          <p class="dashboard-hero-card__label">下一步</p>
          <strong>{{ nextActionLabel }}</strong>
          <p>{{ nextActionHint }}</p>
        </article>
      </div>
    </header>

    <p v-if="feedbackMessage" class="dashboard-alert" :data-tone="feedbackTone">
      {{ feedbackMessage }}
    </p>

    <section class="dashboard-kpis" data-dashboard-section="summary-strip">
      <article class="dashboard-kpi">
        <p class="dashboard-kpi__label">最近项目</p>
        <strong>{{ dashboardStats.projectCount }}</strong>
        <span>真实项目数量</span>
      </article>
      <article class="dashboard-kpi">
        <p class="dashboard-kpi__label">脚本版本</p>
        <strong>{{ dashboardStats.scriptVersion }}</strong>
        <span>{{ dashboardStats.scriptHint }}</span>
      </article>
      <article class="dashboard-kpi">
        <p class="dashboard-kpi__label">分镜版本</p>
        <strong>{{ dashboardStats.storyboardVersion }}</strong>
        <span>{{ dashboardStats.storyboardHint }}</span>
      </article>
      <article class="dashboard-kpi">
        <p class="dashboard-kpi__label">Runtime 版本</p>
        <strong>{{ dashboardStats.runtimeVersion }}</strong>
        <span>{{ dashboardStats.runtimeHint }}</span>
      </article>
    </section>

    <div class="dashboard-grid">
      <article class="dashboard-card" data-dashboard-section="project-entry">
        <div class="dashboard-card__header">
          <div>
            <p class="detail-panel__label">项目入口</p>
            <h2>创建新项目</h2>
          </div>
          <span class="status-chip" :data-tone="projectTone">{{ projectLabel }}</span>
        </div>

        <p class="dashboard-card__summary">
          新建项目后，脚本、分镜、剪辑和复盘会回到同一条真实链路，不会生成虚假的“已完成”统计。
        </p>

        <label class="dashboard-field">
          <span>项目名称</span>
          <input
            v-model="projectName"
            data-field="project.name"
            :disabled="projectActionDisabled"
            placeholder="例如：TikTok 新品短视频首发"
          />
        </label>

        <label class="dashboard-field">
          <span>项目说明</span>
          <textarea
            v-model="projectDescription"
            data-field="project.description"
            :disabled="projectActionDisabled"
            placeholder="写下目标受众、节奏要求或内容方向。"
          />
        </label>

        <div class="dashboard-card__actions">
          <button
            class="dashboard-button"
            type="button"
            data-action="create-project"
            :disabled="projectActionDisabled || projectName.trim().length === 0"
            @click="handleCreateProject"
          >
            创建并进入主链路
          </button>
          <button
            class="dashboard-button dashboard-button--secondary"
            type="button"
            :disabled="projectActionDisabled"
            @click="handleReload"
          >
            重新读取总览
          </button>
        </div>
      </article>

      <section class="dashboard-card" data-dashboard-section="chain-rail">
        <div class="dashboard-card__header">
          <div>
            <p class="detail-panel__label">链路摘要</p>
            <h2>当前主链路</h2>
          </div>
          <span class="status-chip" :data-tone="chainTone">{{ chainLabel }}</span>
        </div>

        <div class="dashboard-chain">
          <RouterLink
            v-for="step in chainSteps"
            :key="step.path"
            class="dashboard-chain__step"
            :class="{ 'is-active': step.active }"
            :to="step.path"
          >
            <span class="dashboard-chain__index">{{ step.index }}</span>
            <div class="dashboard-chain__body">
              <strong>{{ step.title }}</strong>
              <p>{{ step.summary }}</p>
            </div>
            <span class="status-chip" :data-tone="step.tone">{{ step.status }}</span>
          </RouterLink>
        </div>
      </section>

      <section class="dashboard-card" data-dashboard-section="exception-queue">
        <div class="dashboard-card__header">
          <div>
            <p class="detail-panel__label">待办与异常</p>
            <h2>需要先处理的事情</h2>
          </div>
          <span class="status-chip" :data-tone="issueTone">{{ issueLabel }}</span>
        </div>

        <div v-if="issueItems.length === 0" class="dashboard-empty">
          <strong>当前没有待处理异常</strong>
          <p>所有已加载状态都正常，或者还没有项目进入主链路。</p>
        </div>
        <div v-else class="dashboard-issue-list">
          <article v-for="issue in issueItems" :key="issue.id" class="dashboard-issue">
            <span class="dashboard-issue__icon" :data-tone="issue.tone">{{ issue.icon }}</span>
            <div class="dashboard-issue__body">
              <strong>{{ issue.title }}</strong>
              <p>{{ issue.message }}</p>
              <button
                v-if="issue.action"
                class="dashboard-link-button"
                type="button"
                @click="issue.action()"
              >
                {{ issue.actionLabel }}
              </button>
            </div>
          </article>
        </div>
      </section>
    </div>

    <section class="dashboard-card dashboard-card--full" data-dashboard-section="recent-projects">
      <div class="dashboard-card__header">
        <div>
          <p class="detail-panel__label">最近项目</p>
          <h2>真实项目列表</h2>
        </div>
        <span class="status-chip" :data-tone="recentTone">{{ recentLabel }}</span>
      </div>

      <div v-if="projectStore.recentProjects.length === 0" class="dashboard-empty dashboard-empty--wide">
        <strong>还没有项目</strong>
        <p>先创建一个项目，或者从其他页面切回已存在的真实项目。</p>
      </div>

      <div v-else class="dashboard-table-wrap">
        <table class="dashboard-table">
          <thead>
            <tr>
              <th>项目</th>
              <th>版本</th>
              <th>状态</th>
              <th>最近访问</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="project in projectStore.recentProjects"
              :key="project.id"
              :data-project-card="project.id"
              :data-project-id="project.id"
              :class="{ 'is-current': currentProject?.projectId === project.id }"
            >
              <td>
                <strong>{{ project.name }}</strong>
                <p>{{ project.description || "暂无说明" }}</p>
              </td>
              <td>
                <span>{{ project.currentScriptVersion }} / {{ project.currentStoryboardVersion }}</span>
              </td>
              <td>
                <span class="status-chip" :data-tone="projectToneFor(project.status)">{{ project.status }}</span>
              </td>
              <td>
                <span>{{ formatDate(project.lastAccessedAt) }}</span>
              </td>
              <td>
                <button
                  class="dashboard-link-button"
                  type="button"
                  :disabled="projectActionDisabled"
                  @click="handleSelectProject(project.id)"
                >
                  打开
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { useProjectStore } from "@/stores/project";

type Tone = "neutral" | "brand" | "success" | "warning" | "danger" | "info";

type ChainStep = {
  active: boolean;
  index: string;
  path: string;
  status: string;
  summary: string;
  title: string;
  tone: Tone;
};

type IssueItem = {
  action?: () => void;
  actionLabel?: string;
  id: string;
  icon: string;
  message: string;
  title: string;
  tone: Tone;
};

const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const projectStore = useProjectStore();
const route = useRoute();
const router = useRouter();

const projectName = ref("");
const projectDescription = ref("");

const currentProject = computed(() => projectStore.currentProject);
const currentProjectRecord = computed(() =>
  projectStore.recentProjects.find((item) => item.id === currentProject.value?.projectId) ?? null
);
const hasMissingProjectReason = computed(() => {
  const reason = route.query.reason;
  return Array.isArray(reason) ? reason.includes("missing-project") : reason === "missing-project";
});

const dashboardState = computed(() => {
  if (hasMissingProjectReason.value && projectStore.status !== "saving") {
    return "blocked";
  }

  if (
    projectStore.status === "loading" ||
    projectStore.status === "idle" ||
    licenseStore.status === "loading" ||
    licenseStore.status === "idle" ||
    configBusStore.status === "loading" ||
    configBusStore.status === "idle" ||
    configBusStore.runtimeStatus === "loading"
  ) {
    return "loading";
  }

  if (projectStore.status === "saving" || configBusStore.status === "saving") {
    return "disabled";
  }

  if (projectStore.error || licenseStore.error || configBusStore.error) {
    return "error";
  }

  if (!currentProject.value && projectStore.recentProjects.length > 0) {
    return "blocked";
  }

  if (!currentProject.value && projectStore.recentProjects.length === 0) {
    return "empty";
  }

  return "ready";
});

const licenseLabel = computed(() => {
  if (licenseStore.status === "loading") return "授权检查中";
  if (licenseStore.error) return "授权异常";
  return licenseStore.active ? "授权已通过" : "待授权";
});

const licenseTone = computed<Tone>(() => {
  if (licenseStore.error) return "danger";
  if (licenseStore.active) return "success";
  if (licenseStore.status === "loading") return "info";
  return "warning";
});

const runtimeLabel = computed(() => {
  if (configBusStore.runtimeStatus === "online") {
    return "Runtime 在线";
  }
  if (configBusStore.runtimeStatus === "offline") {
    return "Runtime 离线";
  }
  if (configBusStore.runtimeStatus === "loading") {
    return "Runtime 检查中";
  }
  return "Runtime 待检查";
});

const runtimeTone = computed<Tone>(() => {
  if (configBusStore.runtimeStatus === "online") return "success";
  if (configBusStore.runtimeStatus === "offline" || configBusStore.status === "error") return "danger";
  if (configBusStore.runtimeStatus === "loading") return "info";
  return "neutral";
});

const configLabel = computed(() => {
  if (configBusStore.status === "loading") return "配置读取中";
  if (configBusStore.status === "saving") return "配置保存中";
  if (configBusStore.status === "error") return "配置异常";
  if (configBusStore.settings) return "配置已加载";
  return "配置空态";
});

const configTone = computed<Tone>(() => {
  if (configBusStore.status === "error") return "danger";
  if (configBusStore.status === "saving") return "info";
  if (configBusStore.settings) return "success";
  return "warning";
});

const projectLabel = computed(() => {
  if (dashboardState.value === "error") return "总览异常";
  if (currentProject.value) return "已选项目";
  if (hasMissingProjectReason.value) return "缺少项目";
  return "待选择项目";
});

const projectTone = computed<Tone>(() => {
  if (dashboardState.value === "error") return "danger";
  if (currentProject.value) return "success";
  if (hasMissingProjectReason.value) return "warning";
  return "neutral";
});

const heroTitle = computed(() => {
  if (dashboardState.value === "error") {
    return "总览数据读取异常";
  }

  if (currentProject.value) {
    return `继续创作，${currentProject.value.projectName} 正在主链路中运行`;
  }

  if (dashboardState.value === "blocked") {
    return "当前没有可用的项目上下文";
  }

  return "先创建一个项目，再进入真实创作链路";
});

const heroSummary = computed(() => {
  if (dashboardState.value === "error") {
    return "当前总览数据读取失败，请先处理上方错误提示，再继续创建或切换项目。";
  }

  if (currentProject.value) {
    return "这里只展示真实项目和真实状态。脚本、分镜、AI 剪辑与复盘都会从同一个项目上下文继续向前推进。";
  }

  if (dashboardState.value === "blocked") {
    return "系统已经读到运行环境，但当前没有选中的项目。先创建一个项目，或者回到最近项目列表打开已有项目。";
  }

  return "创建首个项目后，脚本、分镜、AI 剪辑、发布和复盘都会回到同一条链路。";
});

const currentProjectHint = computed(() => {
  if (dashboardState.value === "error") {
    return "总览数据读取异常，暂时无法显示当前项目。";
  }

  if (!currentProject.value) {
    return "还没有可继续的项目，先创建一个。";
  }

  if (!currentProjectRecord.value) {
    return "当前项目上下文已就绪，版本信息正在等待最近项目列表回填。";
  }

  return `脚本版本 ${currentProjectRecord.value.currentScriptVersion}，分镜版本 ${currentProjectRecord.value.currentStoryboardVersion}，最近访问会保留真实时间戳。`;
});

const nextActionLabel = computed(() => {
  if (dashboardState.value === "error") {
    return "等待错误修复";
  }

  if (!currentProject.value) {
    return "创建第一个项目";
  }

  if (currentProject.value.status === "active") {
    if (!currentProjectRecord.value) {
      return "等待版本信息回填";
    }

    if (dashboardStats.value.scriptVersion === "0") {
      return "先从脚本与选题开始";
    }
    if (dashboardStats.value.storyboardVersion === "0") {
      return "继续分镜规划";
    }
    return "进入 AI 剪辑工作台";
  }

  return "回到总览恢复上下文";
});

const nextActionHint = computed(() => {
  if (dashboardState.value === "error") {
    return "先处理总览、授权或 Runtime 错误，再继续主链路。";
  }

  if (!currentProject.value) {
    return "先用一个真实项目承接后续链路。";
  }

  if (!currentProjectRecord.value) {
    return "最近项目列表还没回填到当前项目，先稍等版本信息同步完成。";
  }

  if (dashboardStats.value.scriptVersion === "0") {
    return "脚本还没有版本，先生成或导入脚本。";
  }

  if (dashboardStats.value.storyboardVersion === "0") {
    return "分镜尚未成形，继续把脚本拆成镜头。";
  }

  return "前置链路已经具备，继续到剪辑工作台。";
});

const dashboardStats = computed(() => {
  const project = currentProjectRecord.value;
  const scriptVersion = project ? String(project.currentScriptVersion) : "—";
  const storyboardVersion = project ? String(project.currentStoryboardVersion) : "—";
  return {
    projectCount: String(projectStore.recentProjects.length),
    runtimeHint: configBusStore.health ? `${configBusStore.health.mode} · ${configBusStore.health.service}` : "等待健康检查",
    runtimeVersion: configBusStore.health?.version || "—",
    scriptHint: project ? `当前项目 ${project.projectName}` : "暂无当前项目",
    scriptVersion,
    storyboardHint: project ? `当前项目 ${project.projectName}` : "暂无当前项目",
    storyboardVersion
  };
});

const chainSteps = computed<ChainStep[]>(() => {
  const scriptDone = Boolean(currentProjectRecord.value && currentProjectRecord.value.currentScriptVersion > 0);
  const storyboardDone = Boolean(
    currentProjectRecord.value && currentProjectRecord.value.currentStoryboardVersion > 0
  );
  const hasProject = Boolean(currentProject.value);

  return [
    {
      active: !hasProject || !scriptDone,
      index: "01",
      path: "/scripts/topics",
      status: hasProject ? (scriptDone ? "完成" : "待开始") : "阻断",
      summary: hasProject
        ? scriptDone
          ? `脚本已存在第 ${currentProjectRecord.value?.currentScriptVersion} 版。`
          : "先生成脚本与选题，再继续向后推进。"
        : "没有项目上下文时，这一步不能进入。",
      title: "脚本与选题",
      tone: hasProject ? (scriptDone ? "success" : "warning") : "danger"
    },
    {
      active: hasProject && scriptDone && !storyboardDone,
      index: "02",
      path: "/storyboards/planning",
      status: storyboardDone ? "完成" : hasProject && scriptDone ? "进行中" : "待前置",
      summary: hasProject
        ? storyboardDone
          ? `分镜已存在第 ${currentProjectRecord.value?.currentStoryboardVersion} 版。`
          : "把脚本拆成镜头，建立分镜版本。"
        : "先完成项目和脚本，再进入分镜规划。",
      title: "分镜规划",
      tone: hasProject && scriptDone ? (storyboardDone ? "success" : "brand") : "neutral"
    },
    {
      active: hasProject && storyboardDone,
      index: "03",
      path: "/workspace/editing",
      status: storyboardDone ? "可进入" : "待前置",
      summary: hasProject
        ? storyboardDone
          ? "前置版本齐备，可以进入 AI 剪辑工作台。"
          : "等分镜版本落定后再进入剪辑。"
        : "先有项目上下文，再进入剪辑工作台。",
      title: "AI 剪辑",
      tone: hasProject && storyboardDone ? "success" : "neutral"
    },
    {
      active: hasProject,
      index: "04",
      path: "/review/optimization",
      status: hasProject ? "待复盘" : "待创建",
      summary: hasProject
        ? "复盘只消费真实统计和建议，不会补假的结果。"
        : "先建立项目，复盘才有真实来源。",
      title: "复盘与优化",
      tone: hasProject ? "info" : "neutral"
    }
  ];
});

const chainLabel = computed(() => {
  if (!currentProject.value) {
    return "等待项目";
  }
  if (!currentProjectRecord.value) {
    return "等待版本";
  }
  if (dashboardStats.value.scriptVersion === "0") {
    return "脚本待开始";
  }
  if (dashboardStats.value.storyboardVersion === "0") {
    return "分镜待开始";
  }
  return "主链已接通";
});

const chainTone = computed<Tone>(() => {
  if (dashboardState.value === "error") return "danger";
  if (!currentProject.value) return "warning";
  if (!currentProjectRecord.value) return "info";
  if (dashboardStats.value.scriptVersion === "0" || dashboardStats.value.storyboardVersion === "0") {
    return "info";
  }
  return "success";
});

const issueItems = computed<IssueItem[]>(() => {
  const items: IssueItem[] = [];
  if (dashboardState.value === "loading") {
    return items;
  }

  const project = currentProject.value;

  if (route.query.reason === "missing-project" || (!project && projectStore.recentProjects.length > 0)) {
    items.push({
      action: () => {
        void router.push("/dashboard");
      },
      actionLabel: "返回总览",
      id: "missing-project",
      icon: "project_off",
      message: "当前没有选中的项目，先打开一个真实项目，主链路才会继续。",
      title: "缺少项目上下文",
      tone: "warning"
    });
  }

  if (!project && projectStore.recentProjects.length === 0) {
    items.push({
      id: "no-project",
      icon: "add_circle",
      message: "当前没有任何项目，先在左侧创建一个真实项目。",
      title: "尚未创建项目",
      tone: "brand"
    });
  }

  if (!licenseStore.active) {
    items.push({
      action: () => {
        void router.push("/setup/license");
      },
      actionLabel: "去授权页",
      id: "license-required",
      icon: "vpn_key_off",
      message: "许可证未激活，主工作流保持阻断。",
      title: "需要先完成授权",
      tone: "warning"
    });
  }

  if (configBusStore.runtimeStatus === "offline") {
    items.push({
      id: "runtime-offline",
      icon: "cloud_off",
      message: "Runtime 离线，先恢复健康检查再继续。",
      title: "Runtime 离线",
      tone: "danger"
    });
  }

  if (configBusStore.error) {
    items.push({
      id: "config-error",
      icon: "error",
      message: configBusStore.error.requestId
        ? `${configBusStore.error.message}（${configBusStore.error.requestId}）`
        : configBusStore.error.message,
      title: "配置读取异常",
      tone: "danger"
    });
  }

  if (projectStore.error) {
    items.push({
      id: "project-error",
      icon: "report",
      message: projectStore.error.requestId
        ? `${projectStore.error.message}（${projectStore.error.requestId}）`
        : projectStore.error.message,
      title: "总览读取异常",
      tone: "danger"
    });
  }

  if (project && currentProject.value) {
    if (!currentProjectRecord.value) {
      items.push({
        id: "project-sync",
        icon: "sync",
        message: "当前项目已就绪，但最近项目列表还在回填版本信息。",
        title: "版本信息同步中",
        tone: "info"
      });
    } else if (currentProjectRecord.value.currentScriptVersion === 0) {
      items.push({
        action: () => {
          void router.push("/scripts/topics");
        },
        actionLabel: "去脚本页",
        id: "script-next",
        icon: "description",
        message: "脚本还没有版本，先补齐脚本与选题。",
        title: "脚本待补齐",
        tone: "brand"
      });
    } else if (currentProjectRecord.value.currentStoryboardVersion === 0) {
      items.push({
        action: () => {
          void router.push("/storyboards/planning");
        },
        actionLabel: "去分镜页",
        id: "storyboard-next",
        icon: "view_timeline",
        message: "脚本已有版本，下一步是分镜规划。",
        title: "分镜待推进",
        tone: "info"
      });
    } else {
      items.push({
        action: () => {
          void router.push("/workspace/editing");
        },
        actionLabel: "去剪辑工作台",
        id: "editing-next",
        icon: "movie_edit",
        message: "前置版本已齐备，可以继续进入 AI 剪辑工作台。",
        title: "可以继续剪辑",
        tone: "success"
      });
    }
  }

  return items;
});

const issueLabel = computed(() => {
  if (issueItems.value.length === 0) return "状态正常";
  if (issueItems.value.some((item) => item.tone === "danger")) return "存在异常";
  if (issueItems.value.some((item) => item.tone === "warning")) return "需要处理";
  if (issueItems.value.some((item) => item.tone === "info")) return "同步中";
  return "需要处理";
});

const issueTone = computed<Tone>(() => {
  if (issueItems.value.length === 0) return "success";
  if (issueItems.value.some((item) => item.tone === "danger")) return "danger";
  if (issueItems.value.some((item) => item.tone === "warning")) return "warning";
  if (issueItems.value.some((item) => item.tone === "info")) return "info";
  return "brand";
});

const recentLabel = computed(() =>
  projectStore.recentProjects.length > 0 ? `${projectStore.recentProjects.length} 个真实项目` : "空态"
);
const recentTone = computed<Tone>(() => (projectStore.recentProjects.length > 0 ? "success" : "neutral"));

const feedbackMessage = computed(() => {
  if (hasMissingProjectReason.value) {
    return "当前页面缺少项目上下文，请先创建或打开一个真实项目。";
  }

  if (projectStore.error) {
    return projectStore.error.requestId
      ? `${projectStore.error.message}（${projectStore.error.requestId}）`
      : projectStore.error.message;
  }

  if (licenseStore.error) {
    return licenseStore.error.requestId
      ? `${licenseStore.error.message}（${licenseStore.error.requestId}）`
      : licenseStore.error.message;
  }

  if (configBusStore.error) {
    return configBusStore.error.requestId
      ? `${configBusStore.error.message}（${configBusStore.error.requestId}）`
      : configBusStore.error.message;
  }

  return "";
});

const feedbackTone = computed<Tone>(() => {
  if (projectStore.error || licenseStore.error || configBusStore.error) return "danger";
  if (route.query.reason === "missing-project") return "warning";
  return "neutral";
});

const projectActionDisabled = computed(
  () =>
    dashboardState.value === "error" ||
    projectStore.status === "saving" ||
    configBusStore.status === "saving" ||
    licenseStore.status === "submitting"
);

onMounted(() => {
  if (projectStore.status === "idle") {
    void projectStore.load();
  }
});

async function handleCreateProject(): Promise<void> {
  const name = projectName.value.trim();
  if (!name) {
    return;
  }

  const created = await projectStore.createProject({
    name,
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

async function handleReload(): Promise<void> {
  await projectStore.refresh();
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

function formatDate(value: string): string {
  if (!value) {
    return "暂无";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function projectToneFor(status: string): Tone {
  if (status === "active") return "success";
  if (status === "blocked") return "warning";
  if (status === "error") return "danger";
  return "neutral";
}
</script>

<style scoped>
.dashboard-page {
  display: grid;
  gap: var(--space-5);
}

.dashboard-hero,
.dashboard-card {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
}

.dashboard-hero {
  display: grid;
  gap: var(--space-5);
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  padding: var(--space-8);
  background:
    linear-gradient(150deg, rgba(0, 188, 212, 0.10), transparent 40%),
    linear-gradient(320deg, rgba(112, 0, 255, 0.08), transparent 36%),
    var(--color-bg-surface);
}

.dashboard-hero__copy h1,
.dashboard-hero__copy p,
.dashboard-hero-card p,
.dashboard-alert {
  margin: 0;
}

.dashboard-hero__eyebrow {
  color: var(--color-brand-primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}

.dashboard-hero__copy h1 {
  margin-top: var(--space-3);
  font-size: 32px;
  line-height: 1.18;
  letter-spacing: -0.4px;
}

.dashboard-hero__summary {
  margin-top: var(--space-4);
  max-width: 760px;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.dashboard-hero__badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-5);
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.status-chip[data-tone="success"] {
  background: rgba(34, 211, 154, 0.12);
  border-color: rgba(34, 211, 154, 0.18);
  color: var(--color-success);
}

.status-chip[data-tone="warning"] {
  background: rgba(245, 183, 64, 0.12);
  border-color: rgba(245, 183, 64, 0.18);
  color: var(--color-warning);
}

.status-chip[data-tone="danger"] {
  background: rgba(255, 90, 99, 0.12);
  border-color: rgba(255, 90, 99, 0.18);
  color: var(--color-danger);
}

.status-chip[data-tone="info"],
.status-chip[data-tone="brand"] {
  background: var(--color-bg-active);
  border-color: var(--color-border-subtle);
  color: var(--color-brand-primary);
}

.status-chip[data-tone="neutral"] {
  background: var(--color-bg-muted);
  border-color: var(--color-border-subtle);
  color: var(--color-text-secondary);
}

.dashboard-hero__panel {
  display: grid;
  gap: var(--space-3);
}

.dashboard-hero-card {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  background: var(--color-bg-canvas);
  border: 1px solid var(--color-border-subtle);
}

.dashboard-hero-card--muted {
  background: linear-gradient(180deg, rgba(0, 188, 212, 0.05), rgba(112, 0, 255, 0.04));
}

.dashboard-hero-card__label,
.dashboard-card__summary,
.dashboard-card__hint,
.dashboard-issue__body p,
.dashboard-empty p,
.dashboard-kpi span {
  color: var(--color-text-secondary);
}

.dashboard-hero-card strong {
  font-size: 18px;
  line-height: 1.35;
  word-break: break-word;
}

.dashboard-alert {
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-muted);
  line-height: 1.6;
}

.dashboard-alert[data-tone="danger"] {
  border-color: rgba(255, 90, 99, 0.20);
  background: rgba(255, 90, 99, 0.08);
  color: var(--color-danger);
}

.dashboard-alert[data-tone="warning"] {
  border-color: rgba(245, 183, 64, 0.18);
  background: rgba(245, 183, 64, 0.08);
  color: var(--color-warning);
}

.dashboard-kpis {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.dashboard-kpi {
  display: grid;
  gap: 4px;
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-surface);
}

.dashboard-kpi__label {
  color: var(--color-text-tertiary);
  font-size: 12px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.dashboard-kpi strong {
  font-size: 24px;
  line-height: 1.15;
}

.dashboard-grid {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.2fr) minmax(0, 0.85fr);
  align-items: start;
}

.dashboard-card {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
}

.dashboard-card--full {
  grid-column: 1 / -1;
}

.dashboard-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.dashboard-card__header h2 {
  margin-top: 4px;
  font-size: 18px;
  line-height: 1.3;
}

.dashboard-field {
  display: grid;
  gap: 8px;
}

.dashboard-field > span {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.dashboard-field input,
.dashboard-field textarea {
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-canvas);
  color: var(--color-text-primary);
  padding: 12px 14px;
  font-family: inherit;
}

.dashboard-field textarea {
  min-height: 100px;
  resize: vertical;
  line-height: 1.6;
}

.dashboard-field input:disabled,
.dashboard-field textarea:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.dashboard-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.dashboard-button,
.dashboard-link-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 36px;
  padding: 0 var(--space-4);
  border: 0;
  border-radius: var(--radius-md);
  background: var(--color-brand-primary);
  color: var(--color-text-on-brand);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.dashboard-button--secondary,
.dashboard-link-button {
  background: transparent;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-default);
}

.dashboard-button:disabled,
.dashboard-link-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dashboard-chain {
  display: grid;
  gap: var(--space-3);
}

.dashboard-chain__step {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--space-3);
  align-items: start;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
  color: inherit;
  text-decoration: none;
}

.dashboard-chain__step.is-active {
  border-color: rgba(0, 188, 212, 0.25);
  box-shadow: 0 0 0 1px rgba(0, 188, 212, 0.08);
}

.dashboard-chain__index {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.dashboard-chain__body strong,
.dashboard-chain__body p,
.dashboard-issue__body strong,
.dashboard-issue__body p,
.dashboard-empty strong,
.dashboard-table strong,
.dashboard-table p {
  margin: 0;
}

.dashboard-chain__body p {
  margin-top: 4px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.dashboard-issue-list {
  display: grid;
  gap: var(--space-3);
}

.dashboard-issue {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-3);
  padding: 12px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
}

.dashboard-issue__icon {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  font-size: 18px;
}

.dashboard-issue__icon[data-tone="brand"] {
  color: var(--color-brand-primary);
}

.dashboard-issue__icon[data-tone="success"] {
  color: var(--color-success);
}

.dashboard-issue__icon[data-tone="warning"] {
  color: var(--color-warning);
}

.dashboard-issue__icon[data-tone="danger"] {
  color: var(--color-danger);
}

.dashboard-issue__body {
  display: grid;
  gap: 6px;
}

.dashboard-empty {
  display: grid;
  gap: 8px;
  padding: var(--space-5);
  border-radius: var(--radius-md);
  border: 1px dashed var(--color-border-default);
  background: var(--color-bg-canvas);
  text-align: center;
}

.dashboard-empty--wide {
  min-height: 150px;
  align-content: center;
}

.dashboard-table-wrap {
  overflow-x: auto;
}

.dashboard-table {
  width: 100%;
  border-collapse: collapse;
}

.dashboard-table th,
.dashboard-table td {
  padding: 12px 10px;
  border-bottom: 1px solid var(--color-border-subtle);
  text-align: left;
  vertical-align: top;
}

.dashboard-table th {
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-weight: 600;
}

.dashboard-table tr.is-current {
  background: rgba(0, 188, 212, 0.05);
}

.dashboard-table td p {
  color: var(--color-text-secondary);
  margin-top: 4px;
  line-height: 1.55;
}

.dashboard-card--full {
  padding-bottom: var(--space-6);
}

@media (max-width: 1180px) {
  .dashboard-hero,
  .dashboard-kpis,
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .dashboard-hero {
    padding: var(--space-5);
  }

  .dashboard-card,
  .dashboard-kpi {
    padding: var(--space-4);
  }

  .dashboard-chain__step {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .dashboard-chain__step > .status-chip {
    grid-column: 1 / -1;
  }
}
</style>
