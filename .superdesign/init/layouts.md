# Superdesign 全局布局上下文

> 2026-07-19 原型覆盖：当前壳层为 `AppSidebar + TopBar + Content Host + Optional Detail Panel + Status Bar`。账号管理与 AI 系统设置继续复用同一壳层；账号向导和批次向导使用居中桌面 Dialog；紧凑 PC 窗口保持 76px 图标侧栏与覆盖式右侧抽屉，不切换移动导航。

以下文件共同构成 TK-OPS 的启动门禁和稳定桌面壳。为保证忠实复现，保留完整真实源码；设计命令对超过 1000 行的 `AppShell.vue` 必须再按已阅读的模板与相关样式区间传入。

## App.vue

- File: `apps/desktop/src/App.vue`
- Description: 应用根组件，装配 BootstrapGate 与 AppShell。

```vue
<template>
  <BootstrapGate />
</template>

<script setup lang="ts">
import BootstrapGate from "@/bootstrap/BootstrapGate.vue";
</script>

```

## BootstrapGate.vue

- File: `apps/desktop/src/bootstrap/BootstrapGate.vue`
- Description: 首启、授权、Runtime 与目录初始化门禁，决定进入工作壳或显示恢复界面。

```vue
<template>
  <AppShell v-if="bootstrapStore.phase === 'ready'" />
  <BootstrapLoadingScreen v-else-if="bootstrapStore.phase === 'boot_loading'" />
  <BootstrapErrorScreen
    v-else-if="bootstrapStore.phase === 'boot_error'"
    :error-summary="errorSummary"
    @retry="handleRetry"
  />
  <BootstrapLicenseScreen v-else-if="bootstrapStore.phase === 'license_required'" />
  <BootstrapInitializationScreen v-else />
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { routeIds } from "@/app/router";
import AppShell from "@/layouts/AppShell.vue";
import { useBootstrapStore } from "@/stores/bootstrap";
import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";

import BootstrapErrorScreen from "./BootstrapErrorScreen.vue";
import BootstrapInitializationScreen from "./BootstrapInitializationScreen.vue";
import BootstrapLicenseScreen from "./BootstrapLicenseScreen.vue";
import BootstrapLoadingScreen from "./BootstrapLoadingScreen.vue";

const bootstrapStore = useBootstrapStore();
const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const route = useRoute();
const router = useRouter();

const errorSummary = computed(() => {
  if (configBusStore.error) {
    return configBusStore.error.requestId
      ? `${configBusStore.error.message} (${configBusStore.error.requestId})`
      : configBusStore.error.message;
  }

  if (licenseStore.error) {
    return licenseStore.error.requestId
      ? `${licenseStore.error.message} (${licenseStore.error.requestId})`
      : licenseStore.error.message;
  }

  return "启动检查失败。";
});

onMounted(() => {
  void bootstrapStore.load();
});

watch(
  () => bootstrapStore.phase,
  async (phase) => {
    if (phase !== "ready") {
      return;
    }

    if (route.name === routeIds.setupLicenseWizard && !route.query.preview) {
      await router.replace(resolveRedirectTarget(route.query.redirect));
    }
  }
);

async function handleRetry(): Promise<void> {
  await bootstrapStore.retry();
}

function resolveRedirectTarget(value: unknown): string {
  if (typeof value !== "string" || value.length === 0) {
    return "/dashboard";
  }

  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
</script>


```

## AppShell.vue

- File: `apps/desktop/src/layouts/AppShell.vue`
- Description: 全局桌面壳，装配 Title Bar、Sidebar、Content Host、Detail Panel、Status Bar 与 Toast。

```vue
<template>
  <div
    class="app-shell command-shell"
    :data-detail-mode="detailPanelMode"
    :data-detail-open="String(isDetailPanelOpen)"
    :data-detail-presentation="detailPresentation"
    :data-has-running-task="String(hasRunningTask)"
    :data-page-type="currentPage.pageType"
    :data-reduced-motion="String(reducedMotion)"
    :data-sidebar-collapsed="String(sidebarCollapsed)"
    :data-sidebar-effective-collapsed="String(effectiveSidebarCollapsed)"
    :data-theme="theme"
  >
    <header class="app-shell__title-bar">
      <ShellTitleBar
        :ai-provider-label="aiProviderLabel"
        :detail-open="isDetailPanelOpen"
        :is-collapsed="effectiveSidebarCollapsed"
        :license-label="licenseStatusLabel"
        :page-title="currentPage.title"
        :project-label="projectLabel"
        :reduced-motion="reducedMotion"
        :runtime-label="runtimeStatusLabel"
        :runtime-tone="runtimeStatusTone"
        :show-detail-toggle="showDetailToggle"
        :show-sidebar-toggle="showWorkspaceChrome"
        :theme="theme"
        @toggle-detail="handleToggleDetailPanel"
        @toggle-motion="shellUiStore.toggleReducedMotion()"
        @toggle-sidebar="handleToggleSidebar"
        @toggle-theme="shellUiStore.toggleTheme()"
      />
      <span class="app-shell__product-position">本地 AI 视频创作中枢</span>
    </header>

    <div class="app-shell__workspace" :class="{ 'app-shell__workspace--wizard': isWizardPage }">
      <aside
        v-if="showWorkspaceChrome"
        class="app-shell__sidebar"
        :class="{ 'is-collapsed': effectiveSidebarCollapsed }"
      >
        <ShellSidebar
          :has-project="Boolean(projectStore.currentProject)"
          :is-collapsed="effectiveSidebarCollapsed"
          :nav-groups="navGroups"
          :project-label="projectLabel"
        />
      </aside>

      <!-- 窄屏下 Sidebar 展开时的背景遮罩 -->
      <transition name="backdrop-fade">
        <div
          v-if="showWorkspaceChrome && !effectiveSidebarCollapsed"
          class="app-shell__sidebar-backdrop"
          @click="handleToggleSidebar"
        />
      </transition>

      <main class="app-shell__content content-host command-content-host">
        <RouterView v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </transition>
        </RouterView>
      </main>

      <aside
        v-if="showWorkspaceChrome"
        class="app-shell__detail detail-panel-container"
        :class="{ 'is-open': isDetailPanelOpen }"
      >
        <button
          v-if="detailPresentation === 'rail'"
          class="app-shell__detail-rail"
          :aria-label="`展开${detailContext.title}`"
          :title="`展开${detailContext.title}`"
          @click="handleToggleDetailPanel"
        >
          <span class="material-symbols-outlined">{{ detailContext.icon || "right_panel_open" }}</span>
        </button>
        <ShellDetailPanel
          v-show="detailPresentation !== 'rail'"
          :context="detailContext"
          :open="isDetailPanelOpen"
          @close="shellUiStore.closeDetailPanel()"
        />
      </aside>
    </div>

    <footer class="app-shell__status">
      <ShellStatusBar
        :ai-provider-label="aiProviderLabel"
        :detail-open="isDetailPanelOpen"
        :mode="statusBarMode"
        :page-title="currentPage.title"
        :page-type="currentPage.pageType"
        :project-label="projectLabel"
        :runtime-label="runtimeStatusLabel"
        :runtime-status="configBusStore.runtimeStatus"
        :runtime-tone="runtimeStatusTone"
        :sync-label="lastSyncLabel"
      />
    </footer>

    <ToastContainer />
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, onMounted, ref, watch, watchEffect } from "vue";
import { RouterView, useRoute } from "vue-router";


import { routeManifest } from "@/app/router";
import type { RouteNavGroup } from "@/types/router";
import type { AssetDto, AssetReferenceDto } from "@/types/runtime";
import ToastContainer from "@/components/ui/Toast/ToastContainer.vue";
import ShellDetailPanel from "@/layouts/shell/ShellDetailPanel.vue";
import ShellSidebar from "@/layouts/shell/ShellSidebar.vue";
import ShellStatusBar from "@/layouts/shell/ShellStatusBar.vue";
import ShellTitleBar from "@/layouts/shell/ShellTitleBar.vue";
import { useAssetLibraryStore } from "@/stores/asset-library";
import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { useProjectStore } from "@/stores/project";
import { useTaskBusStore } from "@/stores/task-bus";
import {
  createRouteDetailContext,
  type DetailContext,
  type DetailContextField,
  type DetailContextItem,
  type DetailContextMode,
  useShellUiStore
} from "@/stores/shell-ui";

const route = useRoute();
const assetLibraryStore = useAssetLibraryStore();
const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const projectStore = useProjectStore();
const shellUiStore = useShellUiStore();
const taskBusStore = useTaskBusStore();

const { detailContext, isDetailPanelOpen, reducedMotion, sidebarCollapsed, theme } = storeToRefs(shellUiStore);
const { health } = storeToRefs(configBusStore);
const isConstrainedShell = ref(false);
const isCompactDetailShell = ref(false);
const compactSidebarOpen = ref(false);
let constrainedShellQuery: MediaQueryList | null = null;
let compactDetailShellQuery: MediaQueryList | null = null;
const NAV_GROUP_ORDER: RouteNavGroup[] = ["启动与总览", "创作前置", "创作与媒体", "执行与治理", "系统与 AI"];

onMounted(() => {
  taskBusStore.connect();

  if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
    constrainedShellQuery = window.matchMedia("(max-width: 1859px)");
    compactDetailShellQuery = window.matchMedia("(max-width: 960px)");
    syncShellConstraint(constrainedShellQuery);
    syncCompactDetailShell(compactDetailShellQuery);
    constrainedShellQuery.addEventListener("change", syncShellConstraint);
    compactDetailShellQuery.addEventListener("change", syncCompactDetailShell);
  }
});

onBeforeUnmount(() => {
  constrainedShellQuery?.removeEventListener("change", syncShellConstraint);
  compactDetailShellQuery?.removeEventListener("change", syncCompactDetailShell);
  constrainedShellQuery = null;
  compactDetailShellQuery = null;
});

const currentPage = computed(() => routeManifest.find((item) => item.id === route.name) ?? routeManifest[0]);
const isWizardPage = computed(() => currentPage.value.pageType === "wizard");
const showWorkspaceChrome = computed(() => !isWizardPage.value);
const detailPanelMode = computed<DetailContextMode>(() => sanitizeMode(route.meta.detailPanelMode));
const statusBarMode = computed(() => (typeof route.meta.statusBarMode === "string" ? route.meta.statusBarMode : "overview"));
const selectedAsset = computed<AssetDto | null>(
  () => assetLibraryStore.assets.find((asset) => asset.id === assetLibraryStore.selectedId) ?? null
);

const navGroups = computed(() => {
  return NAV_GROUP_ORDER.map((label) => ({
    label,
    items: routeManifest.filter((item) => item.navGroup === label)
  })).filter((group) => group.items.length > 0);
});

const projectLabel = computed(() => projectStore.currentProject?.projectName ?? "未选择项目");
const pageTypeLabel = computed(() => {
  switch (currentPage.value.pageType) {
    case "wizard":
      return "首启链路";
    case "dashboard":
      return "创作总览";
    case "workspace":
      return "工作台";
    case "editor":
      return "编辑流";
    case "queue":
      return "任务队列";
    case "management":
      return "管理页";
    case "settings":
      return "系统设置";
    default:
      return "共享页面";
  }
});

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

const aiProviderLabel = computed(() => {
  const provider = configBusStore.settings?.ai?.provider?.trim();
  return provider ? `AI ${provider}` : "AI 未配置";
});

const licenseStatusLabel = computed(() => {
  if (licenseStore.active) {
    return "许可证已激活";
  }
  if (licenseStore.status === "loading" || licenseStore.status === "submitting") {
    return "许可证检查中";
  }
  return "需要授权";
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

const lastSyncLabel = computed(() => {
  if (!configBusStore.lastSyncedAt) {
    return "最近同步待完成";
  }

  return `最近同步 ${formatShanghaiDate(configBusStore.lastSyncedAt)}`;
});

const hasRunningTask = computed(() => ["tasks", "rendering", "publishing"].includes(statusBarMode.value));
const showDetailToggle = computed(() => showWorkspaceChrome.value && detailPanelMode.value !== "hidden");
const detailPresentation = computed<"hidden" | "docked" | "rail" | "focus">(() => {
  if (!showDetailToggle.value) {
    return "hidden";
  }
  if (!isCompactDetailShell.value) {
    return "docked";
  }
  return isDetailPanelOpen.value ? "focus" : "rail";
});
const shouldProtectWorkspace = computed(
  () => showWorkspaceChrome.value && isDetailPanelOpen.value && isConstrainedShell.value
);
const effectiveSidebarCollapsed = computed(() => {
  if (shouldProtectWorkspace.value) return true;
  if (isCompactDetailShell.value) return !compactSidebarOpen.value;
  return sidebarCollapsed.value;
});

watch(
  [theme, reducedMotion],
  ([nextTheme, nextReducedMotion]) => {
    document.documentElement.dataset.theme = nextTheme;
    document.documentElement.setAttribute("data-reduced-motion", String(nextReducedMotion));
    document.documentElement.style.colorScheme = nextTheme;
  },
  { immediate: true }
);

watchEffect(() => {
  document.title = `TK-OPS | ${currentPage.value.title}`;
});

watch(
  [
    currentPage,
    detailPanelMode,
    projectLabel,
    runtimeStatusLabel,
    aiProviderLabel,
    licenseStatusLabel,
    configStatusLabel,
    selectedAsset,
    isCompactDetailShell,
    () => assetLibraryStore.references,
    () => route.fullPath,
    () => health.value?.version
  ],
  () => {
    syncDetailContext();
  },
  { immediate: true, deep: true }
);

function handleToggleDetailPanel() {
  if (detailPanelMode.value === "hidden") {
    return;
  }

  shellUiStore.toggleDetailPanel();
}

function handleToggleSidebar() {
  if (isCompactDetailShell.value) {
    if (shouldProtectWorkspace.value) {
      shellUiStore.closeDetailPanel();
    }
    compactSidebarOpen.value = !compactSidebarOpen.value;
    return;
  }

  if (shouldProtectWorkspace.value) {
    shellUiStore.closeDetailPanel();
    if (sidebarCollapsed.value) {
      shellUiStore.toggleSidebar();
    }
    return;
  }

  shellUiStore.toggleSidebar();
}

function syncShellConstraint(source?: MediaQueryList | MediaQueryListEvent) {
  isConstrainedShell.value = Boolean(source?.matches ?? constrainedShellQuery?.matches);
}

function syncCompactDetailShell(source?: MediaQueryList | MediaQueryListEvent) {
  isCompactDetailShell.value = Boolean(source?.matches ?? compactDetailShellQuery?.matches);
  if (!isCompactDetailShell.value) {
    compactSidebarOpen.value = false;
  }
}

watch(
  () => route.fullPath,
  () => {
    compactSidebarOpen.value = false;
  }
);

function syncDetailContext() {
  if (!showWorkspaceChrome.value || detailPanelMode.value === "hidden") {
    shellUiStore.clearDetailContext("hidden");
    shellUiStore.closeDetailPanel();
    return;
  }

  switch (detailPanelMode.value) {
    case "asset":
      shellUiStore.setDetailContext(buildAssetDetailContext());
      if (selectedAsset.value && !isCompactDetailShell.value) {
        shellUiStore.openDetailPanel();
      }
      return;
    case "binding":
      shellUiStore.setDetailContext(buildBindingDetailContext());
      return;
    case "logs":
      shellUiStore.setDetailContext(buildLogDetailContext());
      return;
    case "settings":
      shellUiStore.setDetailContext(buildSettingsDetailContext());
      return;
    case "contextual":
    default:
      shellUiStore.setDetailContext(buildContextualDetailContext());
  }
}

function buildContextualDetailContext(): DetailContext {
  return createRouteDetailContext("contextual", {
    icon: currentPage.value.icon,
    eyebrow: pageTypeLabel.value,
    title: `${currentPage.value.title} 上下文`,
    description: projectStore.currentProject
      ? "共享层已经接管当前页面的壳层状态、项目上下文和运行时反馈。"
      : "当前页面仍可渲染，但需要在创作总览选择项目后才能接入完整工作流。",
    badge: {
      label: runtimeStatusLabel.value,
      tone: mapRuntimeTone(runtimeStatusTone.value)
    },
    metrics: [
      {
        id: "page-type",
        label: "页面类型",
        value: pageTypeLabel.value
      },
      {
        id: "project",
        label: "项目上下文",
        value: projectLabel.value
      },
      {
        id: "provider",
        label: "AI Provider",
        value: aiProviderLabel.value
      }
    ],
    sections: [
      {
        id: "work-context",
        title: "工作上下文",
        fields: [
          createField("route", "当前页面", currentPage.value.title),
          createField("project", "项目", projectLabel.value),
          createField("runtime", "Runtime", runtimeStatusLabel.value),
          createField("license", "授权", licenseStatusLabel.value)
        ]
      },
      {
        id: "panel-contract",
        title: "共享层约定",
        description: "页面代理接入时继续沿用 route meta 的 detailPanelMode、statusBarMode 和 pageType。",
        items: [
          createItem("detail-mode", `detailPanelMode: ${detailPanelMode.value}`),
          createItem("status-mode", `statusBarMode: ${statusBarMode.value}`),
          createItem("page-type", `pageType: ${currentPage.value.pageType}`)
        ]
      }
    ]
  });
}

function buildAssetDetailContext(): DetailContext {
  if (!selectedAsset.value) {
    return createRouteDetailContext("asset", {
      icon: "inventory_2",
      eyebrow: "全局上下文",
      title: "资产详情",
      description: "在资产中心或工作台选中真实资产后，右侧会聚合文件元数据、标签和引用范围。",
      badge: {
        label: "等待资产选择",
        tone: "neutral"
      },
      sections: [
        {
          id: "asset-empty",
          title: "选择提示",
          emptyLabel: "当前没有可展示的资产。请选择一个真实资产后再查看详情。"
        }
      ]
    });
  }

  const asset = selectedAsset.value;
  const assetTags = assetLibraryStore.parseTags(asset);
  const references = assetLibraryStore.references;
  const metadataFields: DetailContextField[] = [
    createField("type", "类型", formatAssetType(asset.type)),
    createField("source", "来源", asset.source || "未记录"),
    createField("size", "大小", formatBytes(asset.fileSizeBytes)),
    createField("path", "路径", asset.filePath || "未记录路径", { mono: true, multiline: true }),
    createField("created", "创建时间", formatShanghaiDateTime(asset.createdAt)),
    createField("updated", "更新时间", formatShanghaiDateTime(asset.updatedAt))
  ];

  return {
    key: `asset:${asset.id}`,
    mode: "asset",
    source: "asset-library",
    icon: "inventory_2",
    eyebrow: "全局上下文",
    title: "资产详情",
    description: asset.name,
    badge: {
      label: formatAssetType(asset.type),
      tone: "brand"
    },
    metrics: [
      {
        id: "asset-name",
        label: "资产名称",
        value: asset.name
      },
      {
        id: "asset-tags",
        label: "标签数量",
        value: `${assetTags.length}`
      },
      {
        id: "asset-references",
        label: "引用数量",
        value: `${references.length}`
      }
    ],
    sections: [
      {
        id: "asset-meta",
        title: "属性与元数据",
        fields: metadataFields
      },
      {
        id: "asset-tags",
        title: "真实标签",
        emptyLabel: "当前资产没有可展示的标签。",
        items: assetTags.map((tag, index) => ({
          id: `tag-${index}`,
          title: tag,
          tone: "brand",
          icon: "sell"
        }))
      },
      {
        id: "asset-references",
        title: "引用影响范围",
        emptyLabel: "当前资产暂未被项目链路引用，可以安全整理或删除。",
        items: references.map((reference) => mapReferenceItem(reference))
      }
    ],
    actions: [
      {
        id: "asset-delete",
        label: "检查引用并删除",
        icon: "delete",
        tone: "danger",
        disabled: references.length > 0
      }
    ]
  };
}

function buildLogDetailContext(): DetailContext {
  const items: DetailContextItem[] = [];
  items.push(
    createItem("runtime", runtimeStatusLabel.value, {
      description: "日志流由 Runtime 推送后接入。当前共享层只展示真实在线状态，不拼接伪日志。",
      icon: "memory",
      tone: mapRuntimeTone(runtimeStatusTone.value)
    })
  );
  if (projectStore.currentProject) {
    items.push(
      createItem("project", projectStore.currentProject.projectName, {
        description: "当前项目已接入日志上下文。",
        icon: "folder_open",
        tone: "brand"
      })
    );
  }

  return createRouteDetailContext("logs", {
    icon: "receipt_long",
    eyebrow: "任务与日志",
    title: `${currentPage.value.title} 日志`,
    description: "等待 Runtime 实时事件接入前，右侧保留统一的日志容器和接入提示。",
    badge: {
      label: statusBarMode.value,
      tone: "info"
    },
    sections: [
      {
        id: "log-summary",
        title: "日志通道",
        items
      },
      {
        id: "log-empty",
        title: "日志内容",
        emptyLabel: "当前没有可展示的实时日志。接入 WebSocket 或任务总线后，日志会出现在这里。"
      }
    ]
  });
}

function buildBindingDetailContext(): DetailContext {
  return createRouteDetailContext("binding", {
    icon: "link",
    eyebrow: "账号与执行绑定",
    title: `${currentPage.value.title} 绑定信息`,
    description: "共享层只展示真实授权、项目和 Runtime 状态，不伪造账号或设备数量。",
    badge: {
      label: licenseStatusLabel.value,
      tone: licenseStore.active ? "success" : "warning"
    },
    sections: [
      {
        id: "binding-core",
        title: "当前绑定链路",
        fields: [
          createField("project", "项目", projectLabel.value),
          createField("license", "许可证", licenseStatusLabel.value),
          createField("runtime", "Runtime", runtimeStatusLabel.value)
        ]
      },
      {
        id: "binding-note",
        title: "接入说明",
        items: [
          createItem("account", "账号绑定需要真实对象", {
            description: "不要在页面侧伪造 TikTok 账号、设备或浏览器实例。",
            icon: "manage_accounts"
          }),
          createItem("workspace", "工作区绑定需要真实目录", {
            description: "所有后续动作都应能回溯到本地工作区和执行环境。",
            icon: "desktop_windows"
          })
        ]
      }
    ]
  });
}

function buildSettingsDetailContext(): DetailContext {
  return createRouteDetailContext("settings", {
    icon: "settings",
    eyebrow: "系统诊断",
    title: "系统与 AI 可用性",
    description: "目录边界、配置状态和最近一次运行时版本统一收拢在这里。",
    badge: {
      label: configStatusLabel.value,
      tone: configBusStore.status === "error" ? "danger" : configBusStore.status === "ready" ? "success" : "warning"
    },
    metrics: [
      {
        id: "runtime-version",
        label: "Runtime 版本",
        value: health.value?.version ?? "待同步"
      },
      {
        id: "provider",
        label: "AI Provider",
        value: aiProviderLabel.value
      },
      {
        id: "theme",
        label: "主题",
        value: theme.value === "dark" ? "深色" : "浅色"
      }
    ],
    sections: [
      {
        id: "settings-state",
        title: "系统状态",
        fields: [
          createField("runtime", "Runtime", runtimeStatusLabel.value),
          createField("license", "许可证", licenseStatusLabel.value),
          createField("config", "配置总线", configStatusLabel.value),
          createField("project", "当前项目", projectLabel.value)
        ]
      },
      {
        id: "settings-paths",
        title: "目录与边界",
        fields: [
          createField("workspace-root", "工作区", configBusStore.settings?.runtime.workspaceRoot || "-"),
          createField("cache-dir", "缓存目录", configBusStore.settings?.paths.cacheDir || "-"),
          createField("export-dir", "导出目录", configBusStore.settings?.paths.exportDir || "-"),
          createField(
            "log-dir",
            "日志目录",
            configBusStore.settings?.paths.logDir || configBusStore.diagnostics?.logDir || "-"
          )
        ]
      }
    ]
  });
}

function sanitizeMode(value: unknown): DetailContextMode {
  return ["hidden", "contextual", "asset", "logs", "binding", "settings"].includes(String(value))
    ? (value as DetailContextMode)
    : "contextual";
}

function mapRuntimeTone(value: "idle" | "loading" | "online" | "offline") {
  switch (value) {
    case "online":
      return "success";
    case "offline":
      return "danger";
    case "loading":
      return "warning";
    default:
      return "info";
  }
}

function createField(
  id: string,
  label: string,
  value: string,
  options: Partial<DetailContextField> = {}
): DetailContextField {
  return {
    id,
    label,
    value,
    hint: options.hint,
    tone: options.tone,
    mono: options.mono,
    multiline: options.multiline
  };
}

function createItem(id: string, title: string, options: Partial<DetailContextItem> = {}): DetailContextItem {
  return {
    id,
    title,
    description: options.description,
    meta: options.meta,
    tone: options.tone,
    icon: options.icon
  };
}

function mapReferenceItem(reference: AssetReferenceDto): DetailContextItem {
  return {
    id: reference.id,
    title: reference.referenceType,
    description: reference.referenceId,
    meta: formatShanghaiDateTime(reference.createdAt),
    tone: "brand",
    icon: "link"
  };
}

function formatAssetType(type: string) {
  switch (type) {
    case "video":
      return "视频";
    case "image":
      return "图片";
    case "audio":
      return "音频";
    case "document":
      return "文档";
    default:
      return type || "未知";
  }
}

function formatBytes(bytes: number | null) {
  if (bytes === null) {
    return "未记录";
  }

  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatShanghaiDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).formatToParts(date);

  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")}`;
}

function formatShanghaiDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    hourCycle: "h23"
  }).formatToParts(date);

  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")} ${part("hour")}:${part("minute")}:${part("second")}`;
}
</script>

<style scoped>
.app-shell {
  background:
    radial-gradient(circle at top center, color-mix(in srgb, var(--color-brand-primary) 10%, transparent), transparent 48%),
    var(--color-bg-canvas);
  color: var(--color-text-primary);
  display: grid;
  grid-template-rows: var(--titlebar-height) minmax(0, 1fr) var(--statusbar-height);
  height: 100vh;
  height: 100dvh;
  max-width: 100%;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  width: 100%;
}

.app-shell__title-bar {
  border-bottom: 1px solid var(--color-border-subtle);
  min-height: 0;
  overflow: hidden;
  position: relative;
  z-index: var(--z-titlebar);
}

.app-shell__product-position {
  color: var(--color-text-secondary);
  display: none;
  font: var(--font-caption);
  pointer-events: none;
  position: absolute;
  right: var(--space-4);
  top: 50%;
  transform: translateY(-50%);
}

.app-shell__workspace {
  display: grid;
  grid-template-columns:
    var(--sidebar-width-expanded)
    minmax(0, 1fr)
    auto;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  position: relative;
  transition: grid-template-columns var(--motion-default) var(--ease-spring);
}

.app-shell[data-sidebar-collapsed="true"] .app-shell__workspace {
  grid-template-columns:
    var(--sidebar-width-collapsed)
    minmax(0, 1fr)
    auto;
}

.app-shell[data-sidebar-effective-collapsed="true"] .app-shell__workspace {
  grid-template-columns:
    var(--sidebar-width-collapsed)
    minmax(0, 1fr)
    auto;
}

.app-shell__workspace--wizard {
  grid-template-columns: minmax(0, 1fr);
}

.app-shell__sidebar {
  border-right: 1px solid var(--color-border-subtle);
  grid-column: 1;
  grid-row: 1;
  min-height: 0;
  overflow: hidden;
  transition:
    box-shadow var(--motion-fast) var(--ease-standard),
    transform var(--motion-default) var(--ease-spring);
}

.app-shell__content {
  background: var(--color-bg-canvas);
  flex: 1;
  grid-column: 2;
  grid-row: 1;
  min-height: 0;
  min-width: 0;
  overflow-x: hidden;
  overflow-y: auto;
  position: relative;
}

.app-shell[data-page-type="dashboard"] .app-shell__content :deep(.page-container),
.app-shell[data-page-type="settings"] .app-shell__content :deep(.settings-console) {
  max-width: min(1680px, 100%);
}

.app-shell[data-page-type="editor"] .app-shell__content :deep(.page-container),
.app-shell[data-page-type="workspace"] .app-shell__content :deep(.page-container),
.app-shell[data-page-type="queue"] .app-shell__content :deep(.page-container),
.app-shell[data-page-type="management"] .app-shell__content :deep(.page-container) {
  margin-left: 0;
  margin-right: 0;
  max-width: none;
}

.app-shell__detail {
  border-left: 1px solid var(--color-border-subtle);
  grid-column: 3;
  grid-row: 1;
  min-height: 0;
  opacity: 0;
  overflow: hidden;
  pointer-events: none;
  transform: translateX(16px);
  transition:
    width var(--motion-default) var(--ease-spring),
    opacity var(--motion-fast) var(--ease-standard),
    transform var(--motion-default) var(--ease-spring);
  width: 0;
}

.app-shell__detail.is-open {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(0);
  width: var(--detail-panel-width);
}

.app-shell__detail-rail {
  align-items: center;
  appearance: none;
  background: var(--color-bg-surface);
  border: 0;
  color: var(--color-text-secondary);
  cursor: pointer;
  display: flex;
  height: 100%;
  justify-content: center;
  padding: 0;
  width: 100%;
}

.app-shell__detail-rail:hover,
.app-shell__detail-rail:focus-visible {
  background: var(--color-bg-hover);
  color: var(--color-brand-primary);
}

.app-shell__detail-rail .material-symbols-outlined {
  font-size: 20px;
}

.app-shell[data-detail-mode="logs"] .app-shell__detail.is-open,
.app-shell[data-detail-mode="settings"] .app-shell__detail.is-open {
  width: var(--detail-panel-width-wide);
}

.app-shell__status {
  border-top: 1px solid var(--color-border-subtle);
  min-height: 0;
  z-index: var(--z-statusbar);
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition:
    opacity var(--motion-fast) var(--ease-standard),
    transform var(--motion-fast) var(--ease-standard);
}

.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@media (max-width: 1440px) {
  .app-shell__workspace {
    grid-template-columns: var(--sidebar-width-expanded) minmax(0, 1fr) auto;
  }

  .app-shell[data-sidebar-collapsed="true"] .app-shell__workspace {
    grid-template-columns: var(--sidebar-width-collapsed) minmax(0, 1fr) auto;
  }

  .app-shell[data-sidebar-effective-collapsed="true"] .app-shell__workspace {
    grid-template-columns: var(--sidebar-width-collapsed) minmax(0, 1fr) auto;
  }

  .app-shell__sidebar {
    background: var(--color-bg-canvas);
    box-shadow: none;
    position: relative;
    width: auto;
    z-index: auto;
  }
}

@media (max-width: 1199px) {
  .app-shell__workspace {
    grid-template-columns: var(--sidebar-width-expanded) minmax(0, 1fr) auto;
  }

  .app-shell[data-sidebar-collapsed="true"] .app-shell__workspace {
    grid-template-columns: var(--sidebar-width-collapsed) minmax(0, 1fr) auto;
  }

  .app-shell[data-sidebar-effective-collapsed="true"] .app-shell__workspace {
    grid-template-columns: var(--sidebar-width-collapsed) minmax(0, 1fr) auto;
  }
}

@media (max-width: 960px) {
  .app-shell__workspace,
  .app-shell[data-sidebar-collapsed="true"] .app-shell__workspace,
  .app-shell[data-sidebar-effective-collapsed="true"] .app-shell__workspace {
    grid-template-columns: minmax(0, 1fr);
  }

  .app-shell[data-detail-presentation="rail"] .app-shell__workspace {
    grid-template-columns: minmax(0, 1fr) var(--detail-rail-width);
  }

  .app-shell[data-detail-presentation="focus"] .app-shell__workspace {
    grid-template-columns: minmax(0, 1fr);
  }

  .app-shell__content {
    grid-column: 1;
  }

  .app-shell[data-detail-presentation="focus"] .app-shell__content {
    display: none;
  }

  .app-shell__sidebar {
    background: var(--color-bg-surface);
    border-right: 1px solid var(--color-border-subtle);
    bottom: 0;
    box-shadow: var(--shadow-lg);
    left: 0;
    position: absolute;
    top: 0;
    transform: translateX(0);
    width: var(--sidebar-width-expanded);
    z-index: calc(var(--z-sidebar) + 1);
  }

  .app-shell[data-sidebar-collapsed="true"] .app-shell__sidebar,
  .app-shell[data-sidebar-effective-collapsed="true"] .app-shell__sidebar {
    transform: translateX(calc(-1 * var(--sidebar-width-expanded)));
  }

  .app-shell[data-detail-presentation="rail"] .app-shell__detail {
    background: var(--color-bg-elevated);
    grid-column: 2;
    opacity: 1;
    pointer-events: auto;
    transform: translateX(0);
    width: var(--detail-rail-width);
  }

  .app-shell[data-detail-presentation="focus"] .app-shell__detail {
    background: var(--color-bg-elevated);
    grid-column: 1;
    opacity: 1;
    pointer-events: auto;
    transform: translateX(0);
    width: 100%;
  }
}

/* 侧边栏背景遮罩 — 仅在窄屏下可见 */
.app-shell__sidebar-backdrop {
  display: none;
}

@media (max-width: 960px) {
  .app-shell__sidebar-backdrop {
    background: rgba(0, 0, 0, 0.38);
    bottom: 0;
    display: block;
    left: 0;
    position: absolute;
    right: 0;
    top: 0;
    z-index: var(--z-sidebar);
  }
}

.backdrop-fade-enter-active,
.backdrop-fade-leave-active {
  transition: opacity var(--motion-default) var(--ease-standard);
}
.backdrop-fade-enter-from,
.backdrop-fade-leave-to {
  opacity: 0;
}
</style>

```

## ShellTitleBar.vue

- File: `apps/desktop/src/layouts/shell/ShellTitleBar.vue`
- Description: 顶部标题栏，呈现项目、页面、Runtime、AI、许可证与全局控制。

```vue
<template>
  <div class="shell-title-bar" data-tauri-drag-region>
    
    <!-- 左侧区 -->
    <div class="shell-title-bar__left" data-tauri-drag-region>
      <button
        v-if="showSidebarToggle"
        class="shell-title-bar__sidebar-toggle icon-button"
        :title="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
        :aria-label="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
        @click="emit('toggle-sidebar')"
      >
        <span class="material-symbols-outlined">
          {{ isCollapsed ? "menu_open" : "keyboard_double_arrow_left" }}
        </span>
      </button>

      <div class="shell-brand" data-tauri-drag-region>
        <TkopsBrandMark size="sm" />
        <span class="shell-brand__name" data-tauri-drag-region>TK-OPS</span>
      </div>
      
      <div class="shell-divider" data-tauri-drag-region>|</div>
      
      <div class="shell-project" data-tauri-drag-region>
        <span class="shell-project__name" :title="projectLabel" data-tauri-drag-region>
          {{ projectLabel }}
        </span>
      </div>
    </div>

    <!-- 中间区 -->
    <div class="shell-title-bar__center" data-tauri-drag-region>
      <span class="shell-page-title" :title="pageTitle" data-tauri-drag-region>{{ pageTitle }}</span>
    </div>

    <!-- 右侧区 -->
    <div class="shell-title-bar__right" data-tauri-drag-region>
      <div class="shell-status-item">
        <span class="status-dot status-dot--brand"></span>
        <span class="status-text">{{ aiProviderLabel }}</span>
      </div>
      
      <div class="shell-status-item">
        <span class="status-dot" :class="`status-dot--${runtimeStatusTone}`"></span>
        <span class="status-text">{{ runtimeLabel }}</span>
      </div>

      <Chip :variant="licenseChipTone" size="sm" class="shell-license-chip">
        {{ licenseLabel }}
      </Chip>

      <div class="shell-actions">
        <button
          v-if="showDetailToggle"
          class="shell-title-bar__detail-toggle icon-button"
          :class="{ 'is-active': detailOpen }"
          :title="detailOpen ? '收起右侧详情' : '展开右侧详情'"
          :aria-label="detailOpen ? '收起右侧详情' : '展开右侧详情'"
          :aria-pressed="String(detailOpen)"
          @click="emit('toggle-detail')"
        >
          <span class="material-symbols-outlined">
            {{ detailOpen ? "right_panel_close" : "right_panel_open" }}
          </span>
        </button>
        <button 
          class="icon-button" 
          :title="theme === 'dark' ? '切换浅色主题' : '切换深色主题'" 
          @click="emit('toggle-theme')"
        >
          <span class="material-symbols-outlined">{{ theme === 'dark' ? 'light_mode' : 'dark_mode' }}</span>
        </button>
        <button class="icon-button" title="系统设置">
          <span class="material-symbols-outlined">settings</span>
        </button>
      </div>

      <div class="shell-window-controls">
        <button class="icon-button" title="最小化" @click="handleMinimize">
          <span class="material-symbols-outlined">remove</span>
        </button>
        <button class="icon-button" title="最大化或还原" @click="handleToggleMaximize">
          <span class="material-symbols-outlined">crop_square</span>
        </button>
        <button class="icon-button window-close" title="关闭" @click="handleClose">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import TkopsBrandMark from "@/components/brand/TkopsBrandMark.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const props = defineProps<{
  aiProviderLabel: string;
  detailOpen: boolean;
  isCollapsed: boolean;
  licenseLabel: string;
  pageTitle: string;
  projectLabel: string;
  reducedMotion: boolean;
  runtimeLabel: string;
  runtimeTone: "idle" | "loading" | "online" | "offline";
  showDetailToggle: boolean;
  showSidebarToggle: boolean;
  theme: "light" | "dark";
}>();

const emit = defineEmits<{
  (event: "toggle-detail"): void;
  (event: "toggle-motion"): void;
  (event: "toggle-sidebar"): void;
  (event: "toggle-theme"): void;
}>();

const runtimeStatusTone = computed(() => {
  switch (props.runtimeTone) {
    case "online":
      return "success";
    case "offline":
      return "danger";
    case "loading":
      return "warning";
    default:
      return "info";
  }
});

const licenseChipTone = computed(() => (props.licenseLabel.includes("激活") ? "brand" : "warning"));

function handleWindowError(action: string, error: unknown) {
  console.warn(`[Tauri 模拟] ${action} 未在当前环境执行。`, error);
}

async function handleMinimize() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().minimize();
  } catch (error) {
    handleWindowError("最小化", error);
  }
}

async function handleToggleMaximize() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().toggleMaximize();
  } catch (error) {
    handleWindowError("最大化切换", error);
  }
}

async function handleClose() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().close();
  } catch (error) {
    handleWindowError("关闭", error);
  }
}
</script>

<style scoped>
.shell-title-bar {
  height: var(--titlebar-height, 48px);
  background: var(--color-bg-surface);
  border-bottom: 1px solid var(--color-border-subtle);
  padding: 0 var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  min-width: 0;
  overflow: hidden;
  width: 100%;
  -webkit-app-region: drag;
}

/* ====================
 * 左侧区 
 * ==================== */
.shell-title-bar__left {
  display: flex;
  align-items: center;
  gap: var(--space-3); /* 12px */
  flex: 0 1 280px;
  min-width: 0;
}

.shell-title-bar__sidebar-toggle {
  display: none;
  flex: 0 0 auto;
  -webkit-app-region: no-drag;
}

.shell-brand {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: var(--space-2);
}

.shell-brand__name {
  font: var(--font-title-sm);
  letter-spacing: 0;
  color: var(--color-text-primary);
}

.shell-divider {
  font-size: 14px;
  line-height: 14px;
  color: var(--color-border-default);
  user-select: none;
}

.shell-project {
  flex: 1;
  min-width: 0;
}

.shell-project__name {
  display: block;
  font: var(--font-body-md);
  letter-spacing: 0;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ====================
 * 中间区 
 * ==================== */
.shell-title-bar__center {
  flex: 1 1 220px;
  display: flex;
  justify-content: flex-start;
  max-width: 360px;
  min-width: 0;
}

.shell-page-title {
  color: var(--color-text-primary);
  display: block;
  font: var(--font-title-sm);
  letter-spacing: 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ====================
 * 右侧区 
 * ==================== */
.shell-title-bar__right {
  display: flex;
  align-items: center;
  flex: 0 1 auto;
  gap: var(--space-2); /* 8px */
  justify-content: flex-end;
  min-width: 0;
  overflow: hidden;
}

.shell-status-item {
  display: flex;
  align-items: center;
  flex: 0 1 auto;
  gap: 6px;
  min-width: 0;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-bg-muted);
}

.status-dot--success { background: var(--color-success); box-shadow: 0 0 8px var(--color-success); }
.status-dot--warning { background: var(--color-warning); box-shadow: 0 0 8px var(--color-warning); }
.status-dot--danger { background: var(--color-danger); box-shadow: 0 0 8px var(--color-danger); }
.status-dot--info { background: var(--color-info); }
.status-dot--brand { background: var(--color-brand-primary); box-shadow: 0 0 8px var(--color-brand-primary); }

.status-text {
  font: var(--font-caption);
  letter-spacing: 0;
  color: var(--color-text-secondary);
  max-width: 116px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shell-actions, .shell-window-controls {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 4px;
  -webkit-app-region: no-drag;
}

.shell-window-controls {
  flex: 0 0 auto;
}

.icon-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
}

.icon-button:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.shell-title-bar__detail-toggle.is-active {
  background: var(--color-bg-active);
  color: var(--color-brand-primary);
}

.icon-button .material-symbols-outlined {
  font-size: 18px;
}

.window-close:hover {
  background: var(--color-danger);
  color: #fff;
}

/* 适配窄屏 */
@media (max-width: 1160px) {
  .shell-title-bar__center {
    display: none;
  }
}
@media (max-width: 960px) {
  .shell-title-bar__sidebar-toggle {
    display: flex;
  }
  .shell-title-bar__left {
    width: auto;
  }
  .shell-divider, .shell-project {
    display: none;
  }
}
@media (max-width: 760px) {
  .shell-status-item,
  .shell-license-chip {
    display: none;
  }
}
</style>

```

## ShellSidebar.vue

- File: `apps/desktop/src/layouts/shell/ShellSidebar.vue`
- Description: 五组正式导航、项目上下文与折叠态。

```vue
<template>
  <aside class="shell-sidebar" :data-collapsed="String(isCollapsed)">
    <nav class="shell-sidebar__nav" aria-label="TK-OPS 页面导航">
      <section v-for="group in navGroups" :key="group.label" class="shell-sidebar__group">
        <p class="shell-sidebar__group-title">{{ group.label }}</p>

        <template v-for="item in group.items" :key="item.id">
          <RouterLink
            v-if="!item.requiresProjectContext || hasProject"
            :data-route-id="item.id"
            :title="isCollapsed ? item.title : ''"
            :to="item.path"
            active-class="is-active"
            class="shell-nav-link"
          >
            <span class="shell-nav-link__icon material-symbols-outlined">{{ item.icon }}</span>
            <span class="shell-nav-link__text">{{ item.title }}</span>
          </RouterLink>

          <div
            v-else
            :data-route-id="item.id"
            :title="isCollapsed ? item.title : '请先在创作总览选择项目'"
            class="shell-nav-link shell-nav-link--disabled"
          >
            <span class="shell-nav-link__icon material-symbols-outlined">{{ item.icon }}</span>
            <span class="shell-nav-link__text">{{ item.title }}</span>
          </div>
        </template>
      </section>
    </nav>

    <footer class="shell-sidebar__footer">
      <div class="shell-sidebar__user-card">
        <TkopsBrandMark class="shell-sidebar__brand-mark" size="md" />
        <div class="shell-sidebar__user-info">
          <span class="user-name">本地创作者</span>
          <span class="user-status">{{ hasProject ? "工作区已连接" : "离线授权" }}</span>
        </div>
      </div>

      <button class="shell-sidebar__toggle" :title="isCollapsed ? '展开侧边栏' : '折叠侧边栏'" @click="shellUiStore.toggleSidebar()">
        <span class="material-symbols-outlined">{{ isCollapsed ? "keyboard_double_arrow_right" : "keyboard_double_arrow_left" }}</span>
      </button>
    </footer>
  </aside>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import TkopsBrandMark from "@/components/brand/TkopsBrandMark.vue";
import type { RouteManifestItem } from "@/types/router";
import { useShellUiStore } from "@/stores/shell-ui";

defineProps<{
  hasProject: boolean;
  isCollapsed: boolean;
  navGroups: Array<{
    label: string;
    items: RouteManifestItem[];
  }>;
  projectLabel: string;
}>();

const shellUiStore = useShellUiStore();
</script>

<style scoped>
.shell-sidebar {
  background: var(--color-bg-canvas);
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  /* 展开态：padding: var(--space-4) var(--space-3) */
  padding: var(--space-4) var(--space-3);
  transition: padding var(--motion-default) var(--ease-spring);
}

.shell-sidebar[data-collapsed="true"] {
  /* 折叠态：padding: var(--space-4) var(--space-2) */
  padding: var(--space-4) var(--space-2);
}

.shell-sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-color: color-mix(in srgb, var(--color-text-tertiary) 44%, transparent) transparent;
  scrollbar-width: thin;
}

.shell-sidebar__nav::-webkit-scrollbar {
  width: 6px;
}

.shell-sidebar__nav::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-text-tertiary) 32%, transparent);
  border-radius: var(--radius-full);
}

.shell-sidebar[data-collapsed="true"] .shell-sidebar__nav {
  scrollbar-width: none;
}

.shell-sidebar[data-collapsed="true"] .shell-sidebar__nav::-webkit-scrollbar {
  width: 0;
}

.shell-sidebar__group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.shell-sidebar__group-title {
  align-items: center;
  color: var(--color-text-tertiary);
  display: flex;
  font: var(--font-caption);
  height: 24px;
  letter-spacing: 0.8px;
  margin: var(--space-2) 0 0;
  padding: 0 var(--space-3);
  text-transform: uppercase;
  white-space: nowrap;
  transition: opacity var(--motion-default) var(--ease-standard);
  opacity: 1;
}

.shell-sidebar[data-collapsed="true"] .shell-sidebar__group-title {
  opacity: 0;
  pointer-events: none;
  height: 0;
  margin: 0;
  overflow: hidden;
}

.shell-nav-link {
  align-items: center;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  display: flex;
  gap: var(--space-3);
  height: 40px;
  padding: 0 12px;
  text-decoration: none;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard),
    transform var(--motion-instant) var(--ease-bounce);
  white-space: nowrap;
  position: relative;
}

.shell-sidebar[data-collapsed="true"] .shell-nav-link {
  padding: 0;
  justify-content: center;
}

.shell-nav-link:hover:not(.shell-nav-link--disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.shell-nav-link:active:not(.shell-nav-link--disabled) {
  transform: scale(0.98);
}

.shell-nav-link.is-active {
  background: var(--color-bg-active);
  color: var(--color-brand-primary);
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--color-brand-primary);
  position: relative;
}

/* 活跃项左侧指示条微流光 */
.shell-nav-link.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, var(--color-brand-primary), var(--color-brand-secondary), var(--color-brand-primary));
  background-size: 100% 200%;
  animation: sidebar-active-flow var(--motion-breathe) ease-in-out infinite alternate;
}

@keyframes sidebar-active-flow {
  from { background-position: 0% 0%; }
  to { background-position: 0% 100%; }
}

.shell-nav-link__icon {
  font-size: 20px;
  flex-shrink: 0;
}

.shell-nav-link__text {
  font: var(--font-title-sm);
  letter-spacing: var(--ls-title-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  transition: opacity var(--motion-default) var(--ease-standard);
  opacity: 1;
}

.shell-sidebar[data-collapsed="true"] .shell-nav-link__text {
  opacity: 0;
  width: 0;
  display: none;
}

.shell-nav-link--disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

/* 底部固定区 */
.shell-sidebar__footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding-top: var(--space-4);
}

.shell-sidebar__user-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 40px;
  overflow: hidden;
  transition: opacity var(--motion-default) var(--ease-standard);
  white-space: nowrap;
}

.shell-sidebar[data-collapsed="true"] .shell-sidebar__user-card {
  opacity: 0;
  width: 0;
  display: none;
}

.shell-sidebar__brand-mark {
  flex-shrink: 0;
}

.shell-sidebar__user-info {
  display: flex;
  flex-direction: column;
}

.shell-sidebar__user-info .user-name {
  font: var(--font-title-sm);
  letter-spacing: 0;
  color: var(--color-text-primary);
  line-height: 1.2;
}

.shell-sidebar__user-info .user-status {
  font: var(--font-caption);
  letter-spacing: 0;
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.shell-sidebar__toggle {
  align-items: center;
  appearance: none;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  display: flex;
  flex-shrink: 0;
  height: 32px;
  justify-content: center;
  width: 32px;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}

.shell-sidebar[data-collapsed="true"] .shell-sidebar__toggle {
  margin: 0 auto;
}

.shell-sidebar__toggle:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.shell-sidebar__toggle:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
</style>

```

## ShellDetailPanel.vue

- File: `apps/desktop/src/layouts/shell/ShellDetailPanel.vue`
- Description: 上下文详情、属性、日志、版本与快捷动作容器。

```vue
<template>
  <div class="shell-detail-panel" :data-open="String(open)">
    <transition name="panel-fade" mode="out-in">
      <component :is="activeComponent" :closable="true" :context="context" @close="$emit('close')" />
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import AssetDetail from "@/components/shell/details/AssetDetail.vue";
import BindingDetail from "@/components/shell/details/BindingDetail.vue";
import ContextualDetail from "@/components/shell/details/ContextualDetail.vue";
import DetailContextRenderer from "@/components/shell/details/DetailContextRenderer.vue";
import LogDetail from "@/components/shell/details/LogDetail.vue";
import SystemStatusDetail from "@/components/shell/details/SystemStatusDetail.vue";
import type { DetailContext } from "@/stores/shell-ui";

const props = defineProps<{
  context: DetailContext;
  open: boolean;
}>();

defineEmits<{
  close: [];
}>();

const activeComponent = computed(() => {
  if (props.context.source === "route") {
    return DetailContextRenderer;
  }
  switch (props.context.mode) {
    case "settings":
      return SystemStatusDetail;
    case "asset":
      return AssetDetail;
    case "logs":
      return LogDetail;
    case "binding":
      return BindingDetail;
    case "hidden":
    case "contextual":
    default:
      return ContextualDetail;
  }
});
</script>

<style scoped>
.shell-detail-panel {
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.panel-fade-enter-active,
.panel-fade-leave-active {
  transition:
    opacity var(--motion-fast) var(--ease-standard),
    transform var(--motion-fast) var(--ease-standard);
}

.panel-fade-enter-from,
.panel-fade-leave-to {
  opacity: 0;
  transform: translateX(8px);
}
</style>

```

## ShellStatusBar.vue

- File: `apps/desktop/src/layouts/shell/ShellStatusBar.vue`
- Description: 持续状态栏，呈现任务、保存、同步、Runtime 与页面模式。

```vue
<template>
  <div class="shell-status-bar" :data-has-running-task="String(hasRunningTask)">
    
    <div class="shell-status-bar__left">
      <div class="status-item">
        <span class="status-dot" :class="`status-dot--${runtimeTone}`"></span>
        <span>{{ runtimeLabel }}</span>
      </div>
      
      <div class="status-item">
        <span class="material-symbols-outlined">queue</span>
        <span>{{ runningTasksCount }} 运行中 / {{ queuedTasksCount }} 排队</span>
      </div>

      <div class="status-item">
        <span class="material-symbols-outlined">auto_awesome</span>
        <span>{{ aiStatusLabel }}</span>
      </div>
    </div>

    <div class="shell-status-bar__right">
      <span class="status-item">{{ syncLabel }}</span>
      <span class="status-item">主题 · {{ themeLabel }}</span>
      <button class="status-icon-btn" title="快捷打开日志" @click="openLogs">
        <span class="material-symbols-outlined">receipt_long</span>
      </button>
    </div>
    
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useShellUiStore } from "@/stores/shell-ui";
import { useTaskBusStore } from "@/stores/task-bus";

const props = defineProps<{
  aiProviderLabel: string;
  detailOpen: boolean;
  mode: string;
  pageTitle: string;
  pageType: string;
  projectLabel: string;
  runtimeLabel: string;
  runtimeStatus: "online" | "offline" | "loading" | "idle";
  runtimeTone: string;
  syncLabel: string;
}>();

const shellUiStore = useShellUiStore();
const taskBusStore = useTaskBusStore();

const themeLabel = computed(() => shellUiStore.theme === "dark" ? "深色" : "浅色");

const runningTasksCount = computed(() => {
  let count = 0;
  taskBusStore.tasks.forEach((task) => {
    if (task.status === "running" || task.status === "processing") {
      count++;
    }
  });
  return count;
});

const queuedTasksCount = computed(() => {
  let count = 0;
  taskBusStore.tasks.forEach((task) => {
    if (task.status === "queued" || task.status === "pending") {
      count++;
    }
  });
  return count;
});

const hasRunningTask = computed(() => runningTasksCount.value > 0);

const aiStatusLabel = computed(() => {
  if (props.runtimeStatus === "loading") {
    return "AI 状态同步中";
  }

  if (props.runtimeStatus === "offline") {
    return "AI 状态未知 · Runtime 离线";
  }

  if (props.runtimeStatus !== "online") {
    return "AI 状态未知 · Runtime 待连接";
  }

  return props.aiProviderLabel === "AI 未配置" ? "AI 未配置 · 待配置" : `${props.aiProviderLabel} · 等待诊断`;
});

function openLogs() {
  shellUiStore.setDetailPanelOpen(true);
}
</script>

<style scoped>
.shell-status-bar {
  height: var(--statusbar-height, 28px);
  background: var(--color-bg-surface);
  border-top: 1px solid var(--color-border-subtle);
  padding: 0 var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-secondary);
  position: relative;
  z-index: var(--z-statusbar);
  min-width: 0;
}

/* 顶部发光线（任务运行时出现） */
.shell-status-bar::before {
  content: '';
  position: absolute;
  top: 0; 
  left: 0; 
  right: 0;
  height: 1px;
  background: var(--gradient-status-bar);
  background-size: 200% 100%;
  opacity: 0.4;
  animation: status-flow calc(var(--motion-flow) * 3) linear infinite;
  transition: opacity var(--motion-default) var(--ease-standard);
  pointer-events: none;
}

.shell-status-bar[data-has-running-task="true"]::before {
  opacity: 1;
  animation: status-flow var(--motion-flow) linear infinite;
}

.shell-status-bar__left,
.shell-status-bar__right {
  display: flex;
  align-items: center;
  gap: var(--space-4); /* 16px */
  min-width: 0;
}

.shell-status-bar__left {
  flex: 1 1 auto;
}

.shell-status-bar__right {
  flex: 0 1 auto;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-item span:last-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-item .material-symbols-outlined {
  font-size: 14px;
  flex: 0 0 auto;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-bg-muted);
  flex-shrink: 0;
}

.status-dot--success, .status-dot--online {
  background: var(--color-success);
  box-shadow: 0 0 6px var(--color-success);
  animation: device-heartbeat var(--motion-breathe) ease-in-out infinite;
}
.status-dot--warning, .status-dot--loading {
  background: var(--color-warning);
  box-shadow: 0 0 6px var(--color-warning);
  animation: device-heartbeat var(--motion-breathe) ease-in-out infinite;
}
.status-dot--danger, .status-dot--offline {
  background: var(--color-danger);
  box-shadow: 0 0 6px var(--color-danger);
  animation: device-heartbeat var(--motion-breathe) ease-in-out infinite;
}
.status-dot--info, .status-dot--idle { background: var(--color-info); }
.status-dot--brand {
  background: var(--color-brand-primary);
  box-shadow: 0 0 6px var(--color-brand-primary);
  animation: device-heartbeat var(--motion-breathe) ease-in-out infinite;
}

.status-icon-btn {
  background: transparent;
  border: none;
  color: currentColor;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  opacity: 0.8;
  transition: opacity var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
  outline: none;
}

.status-icon-btn:hover {
  opacity: 1;
  color: var(--color-text-primary);
}

.status-icon-btn:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
  border-radius: var(--radius-xs);
}

.status-icon-btn .material-symbols-outlined {
  font-size: 16px;
}

/* 窄屏适配 */
@media (max-width: 960px) {
  .shell-status-bar__right {
    gap: var(--space-2);
  }
  .shell-status-bar__right .status-item:not(:last-of-type) {
    display: none;
  }
}
@media (max-width: 640px) {
  .shell-status-bar__left .status-item:not(:first-child) {
    display: none;
  }
}
</style>

```
# Detail Panel 与 Status Bar 子视图

## AssetDetail.vue

- File: `apps/desktop/src/components/shell/details/AssetDetail.vue`
- Description: 全局 Shell 的共享详情或状态子视图。

```vue
<template>
  <DetailContextRenderer :closable="closable" :context="context" @close="$emit('close')" />
</template>

<script setup lang="ts">
import DetailContextRenderer from "@/components/shell/details/DetailContextRenderer.vue";
import type { DetailContext } from "@/stores/shell-ui";

defineProps<{
  closable?: boolean;
  context: DetailContext;
}>();

defineEmits<{
  close: [];
}>();
</script>

```

## BindingDetail.vue

- File: `apps/desktop/src/components/shell/details/BindingDetail.vue`
- Description: 全局 Shell 的共享详情或状态子视图。

```vue
<template>
  <DetailContextRenderer :closable="closable" :context="context" @close="$emit('close')" />
</template>

<script setup lang="ts">
import DetailContextRenderer from "@/components/shell/details/DetailContextRenderer.vue";
import type { DetailContext } from "@/stores/shell-ui";

defineProps<{
  closable?: boolean;
  context: DetailContext;
}>();

defineEmits<{
  close: [];
}>();
</script>

```

## ContextualDetail.vue

- File: `apps/desktop/src/components/shell/details/ContextualDetail.vue`
- Description: 全局 Shell 的共享详情或状态子视图。

```vue
<template>
  <DetailContextRenderer :closable="closable" :context="context" @close="$emit('close')" />
</template>

<script setup lang="ts">
import DetailContextRenderer from "@/components/shell/details/DetailContextRenderer.vue";
import type { DetailContext } from "@/stores/shell-ui";

defineProps<{
  closable?: boolean;
  context: DetailContext;
}>();

defineEmits<{
  close: [];
}>();
</script>

```

## DetailContextRenderer.vue

- File: `apps/desktop/src/components/shell/details/DetailContextRenderer.vue`
- Description: 全局 Shell 的共享详情或状态子视图。

```vue
<template>
  <div class="detail-context-renderer">
    <!-- Header -->
    <header class="detail-header">
      <div class="detail-header__content">
        <p v-if="context.eyebrow" class="detail-header__eyebrow">{{ context.eyebrow }}</p>
        <div class="detail-header__title-row">
          <span v-if="context.icon" class="material-symbols-outlined detail-header__icon">{{ context.icon }}</span>
          <h2 class="detail-header__title">{{ context.title }}</h2>
          <Chip v-if="context.badge" :variant="context.badge.tone ?? 'default'" size="sm">{{ context.badge.label }}</Chip>
        </div>
      </div>
      <button v-if="closable" class="detail-header__close" aria-label="关闭详情面板" @click="$emit('close')">
        <span class="material-symbols-outlined">close</span>
      </button>
    </header>

    <div class="detail-scroll-area">
      <!-- Metric Strip -->
      <div v-if="context.metrics?.length" class="detail-metrics">
        <div v-for="metric in context.metrics" :key="metric.id" class="detail-metric">
          <span class="detail-metric__label">{{ metric.label }}</span>
          <strong class="detail-metric__value">{{ metric.value }}</strong>
        </div>
      </div>

      <!-- Sections -->
      <section v-for="section in context.sections" :key="section.id" class="detail-section">
        <h3 class="detail-section__title">{{ section.title }}</h3>
        <p v-if="section.description" class="detail-section__description">{{ section.description }}</p>

        <!-- Empty State -->
        <div v-if="!section.fields?.length && !section.items?.length" class="detail-empty">
          <span v-if="section.emptyIcon" class="material-symbols-outlined detail-empty__icon">{{ section.emptyIcon }}</span>
          {{ section.emptyLabel || "当前没有可展示的上下文。" }}
        </div>

        <!-- Fields -->
        <div v-if="section.fields?.length" class="detail-fields-group">
          <div v-for="field in section.fields" :key="field.id" class="detail-field">
            <span class="detail-field__label">{{ field.label }}</span>
            <span 
              class="detail-field__value" 
              :data-mono="String(field.mono)"
              :style="field.multiline ? { whiteSpace: 'pre-wrap', textAlign: 'left', flex: 1 } : {}"
            >
              {{ field.value }}
            </span>
          </div>
        </div>

        <!-- Items -->
        <div v-if="section.items?.length" class="detail-items-group">
          <div v-for="item in section.items" :key="item.id" class="detail-item">
            <span v-if="item.icon" class="material-symbols-outlined detail-item__icon" :data-tone="item.tone">{{ item.icon }}</span>
            <div class="detail-item__body">
              <div class="detail-item__title">{{ item.title }}</div>
              <div v-if="item.description" class="detail-item__description">{{ item.description }}</div>
            </div>
            <span v-if="item.meta" class="detail-item__meta">{{ item.meta }}</span>
          </div>
        </div>
      </section>
    </div>

    <!-- Actions -->
    <footer v-if="context.actions?.length" class="detail-actions">
      <Button
        v-for="action in context.actions"
        :key="action.id"
        :disabled="action.disabled"
        :variant="mapActionVariant(action.tone)"
        size="sm"
      >
        <template v-if="action.icon" #leading>
          <span class="material-symbols-outlined">{{ action.icon }}</span>
        </template>
        {{ action.label }}
      </Button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import Button from "@/components/ui/Button/Button.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import type { DetailContext, DetailContextTone } from "@/stores/shell-ui";

defineProps<{
  closable?: boolean;
  context: DetailContext;
}>();

defineEmits<{
  close: [];
}>();

function mapActionVariant(tone: DetailContextTone | undefined) {
  switch (tone) {
    case "danger": return "danger";
    case "brand": return "ai";
    case "neutral": return "ghost";
    default: return "secondary";
  }
}
</script>

<style scoped>
.detail-context-renderer {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.detail-scroll-area {
  flex: 1;
  overflow-y: auto;
  padding-bottom: var(--space-6);
}

/* Header */
.detail-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 48px;
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
  flex-shrink: 0;
}
.detail-header__content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  gap: 2px;
  justify-content: center;
}
.detail-header__eyebrow {
  margin: 0;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.detail-header__title-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.detail-header__icon {
  font-size: 20px;
  color: var(--color-brand-primary);
}
.detail-header__title {
  margin: 0;
  font: var(--font-title-md);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.detail-header__close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
  flex-shrink: 0;
  padding: 0;
}
.detail-header__close .material-symbols-outlined {
  font-size: 18px;
}
.detail-header__close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

/* Metric Strip */
.detail-metrics {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
}
.detail-metric {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.detail-metric__value {
  font: var(--font-title-lg);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.detail-metric__label {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

/* Section */
.detail-section {
  padding: var(--space-4) var(--space-4) 0;
}
.detail-section__title {
  margin: 0 0 var(--space-3) 0;
  font: var(--font-title-sm);
  color: var(--color-text-secondary);
  letter-spacing: 0.3px;
  text-transform: uppercase;
}
.detail-section__description {
  margin: 0 0 var(--space-3) 0;
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
}

/* Empty State */
.detail-empty {
  text-align: center;
  padding: var(--space-10) var(--space-6);
  color: var(--color-text-tertiary);
  font: var(--font-body-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.detail-empty__icon {
  font-size: 40px;
  margin-bottom: var(--space-4);
  opacity: 0.4;
}

/* Fields */
.detail-fields-group {
  display: flex;
  flex-direction: column;
}
.detail-field {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border-subtle);
  gap: var(--space-4);
}
.detail-field:last-child {
  border-bottom: none;
}
.detail-field__label {
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
  flex-shrink: 0;
  width: 100px;
}
.detail-field__value {
  font: var(--font-body-md);
  color: var(--color-text-primary);
  text-align: right;
  word-break: break-all;
}
.detail-field__value[data-mono="true"] {
  font-family: var(--font-family-mono);
  font-size: 12px;
}

/* Items */
.detail-items-group {
  display: flex;
  flex-direction: column;
}
.detail-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border-subtle);
}
.detail-item:last-child {
  border-bottom: none;
}
.detail-item__icon {
  font-size: 18px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
  margin-top: 1px;
}
.detail-item__icon[data-tone="brand"] { color: var(--color-brand-primary); }
.detail-item__icon[data-tone="success"] { color: var(--color-success); }
.detail-item__icon[data-tone="danger"] { color: var(--color-danger); }
.detail-item__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.detail-item__title {
  font: var(--font-body-md);
  color: var(--color-text-primary);
}
.detail-item__description {
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
}
.detail-item__meta {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

/* Bottom Actions */
.detail-actions {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
  height: 56px;
  padding: 0 var(--space-4);
  background: var(--color-bg-surface);
  border-top: 1px solid var(--color-border-subtle);
  flex-shrink: 0;
  z-index: 10;
}
</style>
```

## LogDetail.vue

- File: `apps/desktop/src/components/shell/details/LogDetail.vue`
- Description: 全局 Shell 的共享详情或状态子视图。

```vue
<template>
  <DetailContextRenderer :closable="closable" :context="context" @close="$emit('close')" />
</template>

<script setup lang="ts">
import DetailContextRenderer from "@/components/shell/details/DetailContextRenderer.vue";
import type { DetailContext } from "@/stores/shell-ui";

defineProps<{
  closable?: boolean;
  context: DetailContext;
}>();

defineEmits<{
  close: [];
}>();
</script>

```

## SystemStatusDetail.vue

- File: `apps/desktop/src/components/shell/details/SystemStatusDetail.vue`
- Description: 全局 Shell 的共享详情或状态子视图。

```vue
<template>
  <DetailContextRenderer :closable="closable" :context="context" @close="$emit('close')" />
</template>

<script setup lang="ts">
import DetailContextRenderer from "@/components/shell/details/DetailContextRenderer.vue";
import type { DetailContext } from "@/stores/shell-ui";

defineProps<{
  closable?: boolean;
  context: DetailContext;
}>();

defineEmits<{
  close: [];
}>();
</script>

```

## EditingStatus.vue

- File: `apps/desktop/src/components/shell/status/EditingStatus.vue`
- Description: 全局 Shell 的共享详情或状态子视图。

```vue
<template>
  <div class="editing-status">
    <div class="editing-status__chip">
      <span class="material-symbols-outlined">edit</span>
      <span>{{ pageTitle }}</span>
    </div>
    <div class="editing-status__meta">
      <span>{{ projectLabel }}</span>
      <span>{{ detailOpen ? "详情面板已展开" : "详情面板已收起" }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  detailOpen: boolean;
  pageTitle: string;
  projectLabel: string;
}>();
</script>

<style scoped>
.editing-status {
  align-items: center;
  display: flex;
  gap: var(--space-3);
}

.editing-status__chip {
  align-items: center;
  color: var(--color-brand-primary);
  display: inline-flex;
  gap: 6px;
  font: var(--font-caption);
  font-family: var(--font-family-mono);
}

.editing-status__meta {
  color: var(--color-text-tertiary);
  display: flex;
  gap: var(--space-2);
}
</style>

```

## OverviewStatus.vue

- File: `apps/desktop/src/components/shell/status/OverviewStatus.vue`
- Description: 全局 Shell 的共享详情或状态子视图。

```vue
<template>
  <div class="overview-status">
    <div class="overview-status__chip" :class="`overview-status__chip--${runtimeStatus}`">
      <span class="material-symbols-outlined">auto_awesome</span>
      <span>{{ aiProviderLabel }}</span>
    </div>
    <div class="overview-status__meta">
      <span>{{ pageTitle }}</span>
      <span>{{ pageTypeLabel }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  aiProviderLabel: string;
  pageTitle: string;
  pageType: string;
  runtimeStatus: string;
}>();

const pageTypeLabel = computed(() => {
  switch (props.pageType) {
    case "wizard":
      return "首启链路";
    case "dashboard":
      return "创作总览";
    case "workspace":
      return "工作台";
    case "editor":
      return "编辑流";
    case "queue":
      return "任务队列";
    case "management":
      return "管理页";
    case "settings":
      return "系统设置";
    default:
      return props.pageType;
  }
});
</script>

<style scoped>
.overview-status {
  align-items: center;
  display: flex;
  gap: var(--space-3);
}

.overview-status__chip {
  align-items: center;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-xs);
  color: var(--color-text-secondary);
  display: inline-flex;
  gap: 4px;
  padding: 2px 8px;
}

.overview-status__chip--online {
  border-color: color-mix(in srgb, var(--color-success) 28%, var(--color-border-default));
  color: var(--color-brand-primary);
}

.overview-status__chip--offline {
  border-color: color-mix(in srgb, var(--color-danger) 32%, var(--color-border-default));
  color: var(--color-danger);
}

.overview-status__meta {
  color: var(--color-text-tertiary);
  display: flex;
  gap: var(--space-2);
}
</style>

```

## TaskProgressStatus.vue

- File: `apps/desktop/src/components/shell/status/TaskProgressStatus.vue`
- Description: 全局 Shell 的共享详情或状态子视图。

```vue
<template>
  <div class="task-progress-status">
    <Progress indeterminate class="task-progress-status__progress" />
    <span class="task-progress-status__label">{{ modeLabel }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import Progress from "@/components/ui/Progress/Progress.vue";

const props = defineProps<{
  mode: string;
}>();

const modeLabel = computed(() => {
  switch (props.mode) {
    case "rendering":
      return "渲染任务通道已接管";
    case "publishing":
      return "发布任务等待 Runtime 推送";
    case "review":
      return "复盘链路等待新事件";
    default:
      return "后台任务等待新事件";
  }
});
</script>

<style scoped>
.task-progress-status {
  align-items: center;
  display: flex;
  gap: var(--space-3);
  min-width: 220px;
}

.task-progress-status__progress {
  flex: 1;
}

.task-progress-status__label {
  color: var(--color-text-secondary);
  font: var(--font-caption);
  white-space: nowrap;
}
</style>

```

