<template>
  <div class="app-shell command-shell">
    <header class="title-bar command-title-bar">
      <div class="title-bar__brand command-brand">
        <div class="brand-mark command-brand__mark">TK</div>
        <div>
          <p class="brand-label">TK-OPS 本地 AI 视频创作中枢</p>
          <h1>{{ currentPage.title }}</h1>
          <p class="title-bar__meta">{{ pageContextSummary }}</p>
        </div>
      </div>

      <div class="title-bar__status command-title-bar__status">
        <span class="status-pill" :class="`status-pill--${configBusStore.runtimeStatus}`">
          {{ runtimeStatusLabel }}
        </span>
        <span class="status-pill" :class="`status-pill--${configStatusTone}`">
          {{ configStatusLabel }}
        </span>
        <span class="status-pill" :class="`status-pill--${licenseStatusTone}`">
          {{ licenseStatusLabel }}
        </span>
        <span class="status-pill status-pill--idle" data-current-project>
          {{ projectLabel || "当前未选择项目" }}
        </span>
      </div>
    </header>

    <div class="app-shell__body command-shell__body" :class="{ 'app-shell__body--wizard': isWizardPage }">
      <aside v-if="showWorkspaceChrome" class="sidebar command-sidebar">
        <div class="sidebar__intro command-sidebar__intro">
          <p>工作台导航</p>
          <strong>创作、媒体与发布链路</strong>
        </div>
        <nav aria-label="TK-OPS 页面导航">
          <section v-for="group in navGroups" :key="group.label" class="nav-group">
            <p class="nav-group__title">{{ group.label }}</p>
            <RouterLink
              v-for="item in group.items"
              :key="item.id"
              :to="item.path"
              class="nav-link command-nav-link"
              active-class="nav-link--active"
              :data-route-id="item.id"
            >
              <span class="nav-link__icon">{{ item.icon }}</span>
              <span>{{ item.title }}</span>
            </RouterLink>
          </section>
        </nav>
      </aside>

      <main class="content-host command-content-host">
        <RouterView />
      </main>

      <aside v-if="showWorkspaceChrome" class="detail-panel command-detail-panel">
        <section class="detail-panel__hero command-detail-panel__hero">
          <p class="detail-panel__label">当前页面</p>
          <h2>{{ currentPage.title }}</h2>
          <p>{{ pageContextSummary }}</p>
        </section>

        <section class="detail-panel__section">
          <p class="detail-panel__label">项目上下文</p>
          <template v-if="projectStore.currentProject">
            <strong>{{ projectStore.currentProject.projectName }}</strong>
            <p>项目 ID：{{ projectStore.currentProject.projectId }}</p>
            <p>状态：{{ projectStore.currentProject.status }}</p>
          </template>
          <p v-else>尚未选择项目。需要项目上下文的页面会先回到创作总览。</p>
        </section>

        <section class="detail-panel__section">
          <p class="detail-panel__label">运行状态</p>
          <div class="detail-panel__metric">
            <span>Runtime</span>
            <strong>{{ runtimeStatusLabel }}</strong>
          </div>
          <div class="detail-panel__metric">
            <span>模式</span>
            <strong>{{ health?.mode ?? "待同步" }}</strong>
          </div>
          <div class="detail-panel__metric">
            <span>版本</span>
            <strong>{{ health?.version ?? "待同步" }}</strong>
          </div>
        </section>

        <section v-if="showSettingsDiagnostics" class="detail-panel__section">
          <p class="detail-panel__label">诊断信息</p>
          <template v-if="diagnostics">
            <p>数据库：{{ diagnostics.databasePath }}</p>
            <p>日志目录：{{ diagnostics.logDir }}</p>
            <p>修订号：{{ diagnostics.revision }}</p>
            <p>健康状态：{{ diagnostics.healthStatus }}</p>
          </template>
          <p v-else>暂无诊断信息。</p>
        </section>

        <section class="detail-panel__section">
          <p class="detail-panel__label">授权摘要</p>
          <p>状态：{{ licenseStatusLabel }}</p>
          <p>机器码：{{ licenseStore.machineCode || "待生成" }}</p>
          <p>绑定：{{ licenseStore.machineBound ? "已绑定" : "未绑定" }}</p>
          <p>授权码：{{ licenseStore.maskedCode || "尚未激活" }}</p>
        </section>

        <section class="detail-panel__section detail-panel__section--error">
          <p class="detail-panel__label">最近错误</p>
          <p>{{ lastErrorSummary }}</p>
        </section>
      </aside>
    </div>

    <footer class="status-bar command-status-bar">
      <span>{{ runtimeStatusLabel }}</span>
      <span>{{ isWizardPage ? licenseStatusLabel : configStatusLabel }}</span>
      <span>{{ projectLabel || "当前未选择项目" }}</span>
      <span>{{ isWizardPage ? wizardStatusLabel : lastSyncLabel }}</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, watchEffect } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

import { routeIds, routeManifest } from "@/app/router";
import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { useProjectStore } from "@/stores/project";

const route = useRoute();
const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const projectStore = useProjectStore();
const { diagnostics, error, health } = storeToRefs(configBusStore);

const navGroups = computed(() => {
  const labels = [...new Set(routeManifest.map((item) => item.navGroup))];
  return labels.map((label) => ({
    label,
    items: routeManifest.filter((item) => item.navGroup === label)
  }));
});

const currentPage = computed(() => {
  return routeManifest.find((item) => item.id === route.name) ?? routeManifest[0];
});
const isWizardPage = computed(() => currentPage.value.pageType === "wizard");
const showWorkspaceChrome = computed(() => !isWizardPage.value);
const projectLabel = computed(() =>
  projectStore.currentProject ? `项目：${projectStore.currentProject.projectName}` : ""
);

const runtimeStatusLabel = computed(() => {
  switch (configBusStore.runtimeStatus) {
    case "loading":
      return "Runtime 检查中";
    case "online":
      return "Runtime 在线";
    case "offline":
      return "Runtime 离线";
    default:
      return "Runtime 待连接";
  }
});

const licenseStatusLabel = computed(() => {
  if (licenseStore.active) {
    return "授权已激活";
  }

  if (licenseStore.status === "loading" || licenseStore.status === "submitting") {
    return "授权检查中";
  }

  return "需要授权";
});

const licenseStatusTone = computed(() => {
  if (licenseStore.active) {
    return "online";
  }

  if (licenseStore.status === "loading" || licenseStore.status === "submitting") {
    return "loading";
  }

  return "offline";
});

const configStatusLabel = computed(() => {
  switch (configBusStore.status) {
    case "loading":
      return "配置读取中";
    case "saving":
      return "配置保存中";
    case "ready":
      return "配置已就绪";
    case "error":
      return "配置异常";
    default:
      return "配置待加载";
  }
});

const configStatusTone = computed(() => {
  switch (configBusStore.status) {
    case "ready":
      return "online";
    case "error":
      return "offline";
    case "loading":
    case "saving":
      return "loading";
    default:
      return "idle";
  }
});

const lastSyncLabel = computed(() => {
  return configBusStore.lastSyncedAt
    ? `最近同步 ${configBusStore.lastSyncedAt}`
    : "最近同步待完成";
});

const wizardStatusLabel = computed(() => {
  return licenseStore.machineCode
    ? `机器码 ${licenseStore.machineCode}`
    : "机器码待生成";
});

const showSettingsDiagnostics = computed(() => currentPage.value.id === routeIds.aiSystemSettings);

const pageContextSummary = computed(() => {
  if (currentPage.value.requiresProjectContext) {
    return "此页面会读取当前项目上下文，并把结果回流到同一创作链路。";
  }

  if (currentPage.value.id === routeIds.creatorDashboard) {
    return "项目入口、系统健康和下一步创作动作都从这里开始。";
  }

  return "系统级页面会影响全局配置、状态和后续任务执行。";
});

const lastErrorSummary = computed(() => {
  if (licenseStore.error) {
    return licenseStore.error.requestId
      ? `${licenseStore.error.message}（${licenseStore.error.requestId}）`
      : licenseStore.error.message;
  }

  if (!error.value) {
    return "最近没有运行时错误。";
  }

  return error.value.requestId
    ? `${error.value.message}（${error.value.requestId}）`
    : error.value.message;
});

watchEffect(() => {
  document.title = `TK-OPS | ${currentPage.value.title}`;
});
</script>
