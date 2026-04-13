<template>
  <div class="app-shell command-shell">
    <ShellTitleBar
      :config-label="configStatusLabel"
      :config-tone="configStatusTone"
      :license-label="licenseStatusLabel"
      :license-tone="licenseStatusTone"
      :project-label="projectLabel || '当前未选择项目'"
      :runtime-label="runtimeStatusLabel"
      :runtime-tone="runtimeStatusTone"
      :summary="pageContextSummary"
      :title="currentPage.title"
    />

    <div class="app-shell__body command-shell__body" :class="{ 'app-shell__body--wizard': isWizardPage }">
      <ShellSidebar v-if="showWorkspaceChrome" :nav-groups="navGroups" />

      <main class="content-host command-content-host">
        <RouterView />
      </main>

      <ShellDetailPanel
        v-if="showWorkspaceChrome"
        :diagnostics="diagnostics"
        :last-error-summary="lastErrorSummary"
        :license-label="licenseStatusLabel"
        :machine-bound="licenseStore.machineBound"
        :machine-code="licenseStore.machineCode || '待生成'"
        :masked-code="licenseStore.maskedCode || '尚未激活'"
        :page-summary="pageContextSummary"
        :page-title="currentPage.title"
        :project-id="projectStore.currentProject?.projectId ?? ''"
        :project-name="projectStore.currentProject?.projectName ?? ''"
        :project-status="projectStore.currentProject?.status ?? ''"
        :runtime-label="runtimeStatusLabel"
        :runtime-mode="health?.mode ?? '待同步'"
        :runtime-version="health?.version ?? '待同步'"
        :show-diagnostics="showSettingsDiagnostics"
      />
    </div>

    <ShellStatusBar
      :project-label="projectLabel || '当前未选择项目'"
      :runtime-label="runtimeStatusLabel"
      :secondary-label="isWizardPage ? licenseStatusLabel : configStatusLabel"
      :sync-label="isWizardPage ? wizardStatusLabel : lastSyncLabel"
    />
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, watchEffect } from "vue";
import { RouterView, useRoute } from "vue-router";

import { routeIds, routeManifest } from "@/app/router";
import ShellDetailPanel from "@/layouts/shell/ShellDetailPanel.vue";
import ShellSidebar from "@/layouts/shell/ShellSidebar.vue";
import ShellStatusBar from "@/layouts/shell/ShellStatusBar.vue";
import ShellTitleBar from "@/layouts/shell/ShellTitleBar.vue";
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

const runtimeStatusTone = computed(() => {
  switch (configBusStore.runtimeStatus) {
    case "online":
      return "online";
    case "offline":
      return "offline";
    case "loading":
      return "loading";
    default:
      return "idle";
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
  return licenseStore.machineCode ? `机器码 ${licenseStore.machineCode}` : "机器码待生成";
});

const showSettingsDiagnostics = computed(() => currentPage.value.id === routeIds.aiSystemSettings);

const pageContextSummary = computed(() => {
  if (currentPage.value.requiresProjectContext) {
    return "此页面会读取当前项目上下文，并把结果回流到同一条创作链路。";
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
