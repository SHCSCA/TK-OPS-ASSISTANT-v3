<template>
  <div class="app-shell command-shell" :data-theme="currentTheme">
    <!-- 1. 冻结的顶部标题栏 -->
    <div class="app-shell__header">
      <ShellTitleBar
        :is-collapsed="isSidebarCollapsed"
        @toggle-sidebar="toggleSidebar"
        @toggle-theme="toggleTheme"
        @toggle-detail="toggleDetailPanel"
      />
    </div>

    <!-- 2. 主体区域 -->
    <div class="app-shell__main">
      <div class="command-shell__body" :class="{ 'app-shell__body--wizard': isWizardPage }">
        <!-- 侧边栏 -->
        <ShellSidebar
          v-if="showWorkspaceChrome"
          :nav-groups="navGroups"
          :is-collapsed="isSidebarCollapsed"
          :has-project="!!projectStore.currentProject"
        />

        <!-- 独立滚动的创作主区 -->
        <main class="content-host command-content-host">
          <RouterView v-slot="{ Component }">
            <transition name="page-fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </RouterView>
        </main>

        <!-- 详情面板（抽屉式或浮动面板） -->
        <div v-if="showWorkspaceChrome" class="detail-panel-container" :class="{ 'is-open': isDetailPanelOpen }">
          <ShellDetailPanel
            :mode="(route.meta.detailPanelMode as any)"
            :config-status-label="configStatusLabel"
            :license-label="licenseStatusLabel"
            :masked-code="licenseStore.maskedCode || '尚未激活'"
            :project-name="projectStore.currentProject?.projectName ?? ''"
            :project-status="projectStore.currentProject?.status ?? ''"
            :runtime-label="runtimeStatusLabel"
            :runtime-version="health?.version ?? '待同步'"
          />
        </div>
      </div>
    </div>

    <!-- 3. 冻结的底部状态栏 -->
    <div class="app-shell__footer">
      <ShellStatusBar
        :mode="(route.meta.statusBarMode as string) || 'overview'"
        :runtime-label="runtimeStatusLabel"
        :runtime-tone="runtimeStatusTone"
        :runtime-status="configBusStore.runtimeStatus"
        :ai-provider-label="aiProviderLabel"
        :sync-label="lastSyncLabel"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref, watchEffect, onMounted } from "vue";
import { RouterView, useRoute } from "vue-router";

import { routeManifest } from "@/app/router";
import ShellDetailPanel from "@/layouts/shell/ShellDetailPanel.vue";
import ShellSidebar from "@/layouts/shell/ShellSidebar.vue";
import ShellStatusBar from "@/layouts/shell/ShellStatusBar.vue";
import ShellTitleBar from "@/layouts/shell/ShellTitleBar.vue";
import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { useProjectStore } from "@/stores/project";
import { useShellUiStore } from "@/stores/shell-ui";

const route = useRoute();
const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const projectStore = useProjectStore();
const shellUiStore = useShellUiStore();
const { health } = storeToRefs(configBusStore);
const { isDetailPanelOpen } = storeToRefs(shellUiStore);

// --- 状态控制 ---
const isSidebarCollapsed = ref(false);
const currentTheme = ref<'light' | 'dark'>('light');

function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
}

function toggleDetailPanel() {
  shellUiStore.toggleDetailPanel();
}

function toggleTheme() {
  currentTheme.value = currentTheme.value === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', currentTheme.value);
}

onMounted(() => {
  const savedTheme = localStorage.getItem('tkops-theme') as 'light' | 'dark';
  if (savedTheme) {
    currentTheme.value = savedTheme;
  }
  document.documentElement.setAttribute('data-theme', currentTheme.value);
});

watchEffect(() => {
  localStorage.setItem('tkops-theme', currentTheme.value);
});

const navGroups = computed(() => {
  const labels = [...new Set(routeManifest.map((item) => item.navGroup))].filter(l => l !== 'HIDDEN');
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
    case "loading": return "Runtime 检查中";
    case "online": return "Runtime 在线";
    case "offline": return "Runtime 离线";
    default: return "Runtime 待连接";
  }
});

const runtimeStatusTone = computed(() => {
  switch (configBusStore.runtimeStatus) {
    case "online": return "online";
    case "offline": return "offline";
    case "loading": return "loading";
    default: return "idle";
  }
});

const aiProviderLabel = computed(() => {
  const provider = (configBusStore.settings as any)?.ai?.provider?.trim();
  return provider ? `AI ${provider}` : 'AI 未配置';
});

const licenseStatusLabel = computed(() => {
  if (licenseStore.active) return "授权已激活";
  if (licenseStore.status === "loading" || licenseStore.status === "submitting") return "授权检查中";
  return "需要授权";
});

const configStatusLabel = computed(() => {
  switch (configBusStore.status) {
    case "loading": return "配置读取中";
    case "saving": return "配置保存中";
    case "ready": return "配置已就绪";
    case "error": return "配置异常";
    default: return "配置待加载";
  }
});

const lastSyncLabel = computed(() => {
  return configBusStore.lastSyncedAt
    ? `最近同步 ${formatShanghaiDateTime(configBusStore.lastSyncedAt)}`
    : "最近同步待完成";
});

watchEffect(() => {
  document.title = `TK-OPS | ${currentPage.value.title}`;
});

function formatShanghaiDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")}`;
}
</script>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.app-shell__header {
  flex-shrink: 0;
  height: var(--titlebar-height);
  z-index: 1000;
}

.app-shell__main {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.app-shell__footer {
  flex-shrink: 0;
  height: var(--statusbar-height);
  z-index: 1000;
}

.command-shell__body {
  display: flex;
  flex: 1;
  min-width: 0;
  padding: var(--space-3);
  gap: var(--space-3);
  overflow: hidden;
  position: relative;
}

.detail-panel-container {
  position: absolute;
  right: var(--space-3);
  top: var(--space-3);
  bottom: var(--space-3);
  z-index: 100;
  box-shadow: var(--shadow-lg), 0 0 40px rgba(0, 0, 0, 0.5);
  border-radius: var(--radius-xl);
  transform: translateX(calc(100% + var(--space-3) + 20px));
  transition: transform var(--motion-base), opacity var(--motion-base);
  opacity: 0;
  pointer-events: none;
}

.detail-panel-container.is-open {
  transform: translateX(0);
  opacity: 1;
  pointer-events: auto;
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1), transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
