<template>
  <div
    class="app-shell command-shell"
    :data-detail-mode="detailPanelMode"
    :data-detail-open="String(isDetailPanelOpen)"
    :data-has-running-task="String(hasRunningTask)"
    :data-page-type="currentPage.pageType"
    :data-reduced-motion="String(reducedMotion)"
    :data-sidebar-collapsed="String(sidebarCollapsed)"
    :data-theme="theme"
  >
    <header class="app-shell__title-bar">
      <ShellTitleBar
        :ai-provider-label="aiProviderLabel"
        :detail-open="isDetailPanelOpen"
        :is-collapsed="sidebarCollapsed"
        :license-label="licenseStatusLabel"
        :page-title="currentPage.title"
        :project-label="projectLabel"
        :reduced-motion="reducedMotion"
        :runtime-label="runtimeStatusLabel"
        :runtime-tone="runtimeStatusTone"
        :theme="theme"
        @toggle-detail="handleToggleDetailPanel"
        @toggle-motion="shellUiStore.toggleReducedMotion()"
        @toggle-sidebar="shellUiStore.toggleSidebar()"
        @toggle-theme="shellUiStore.toggleTheme()"
      />
    </header>

    <div class="app-shell__workspace" :class="{ 'app-shell__workspace--wizard': isWizardPage }">
      <aside
        v-if="showWorkspaceChrome"
        class="app-shell__sidebar"
        :class="{ 'is-collapsed': sidebarCollapsed }"
      >
        <ShellSidebar
          :has-project="Boolean(projectStore.currentProject)"
          :is-collapsed="sidebarCollapsed"
          :nav-groups="navGroups"
          :project-label="projectLabel"
        />
      </aside>

      <main class="app-shell__content content-host command-content-host">
        <RouterView v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </RouterView>
      </main>

      <aside
        v-if="showWorkspaceChrome"
        class="app-shell__detail detail-panel-container"
        :class="{ 'is-open': isDetailPanelOpen }"
      >
        <ShellDetailPanel
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
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, watch, watchEffect } from "vue";
import { RouterView, useRoute } from "vue-router";


import { routeManifest } from "@/app/router";
import type { AssetDto, AssetReferenceDto } from "@/types/runtime";
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

onMounted(() => {
  taskBusStore.connect();
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
  const labels = [...new Set(routeManifest.map((item) => item.navGroup))].filter((label) => label !== "HIDDEN");
  return labels.map((label) => ({
    label,
    items: routeManifest.filter((item) => item.navGroup === label)
  }));
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

function syncDetailContext() {
  if (!showWorkspaceChrome.value || detailPanelMode.value === "hidden") {
    shellUiStore.clearDetailContext("hidden");
    shellUiStore.closeDetailPanel();
    return;
  }

  switch (detailPanelMode.value) {
    case "asset":
      shellUiStore.setDetailContext(buildAssetDetailContext());
      if (selectedAsset.value) {
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
  overflow: hidden;
  width: 100vw;
}

.app-shell__title-bar {
  border-bottom: 1px solid var(--color-border-subtle);
  min-height: 0;
  z-index: var(--z-titlebar);
}

.app-shell__workspace {
  display: grid;
  grid-template-columns:
    var(--sidebar-width-expanded)
    minmax(var(--content-min-width), 1fr)
    auto;
  min-height: 0;
  position: relative;
}

.app-shell[data-sidebar-collapsed="true"] .app-shell__workspace {
  grid-template-columns:
    var(--sidebar-width-collapsed)
    minmax(var(--content-min-width), 1fr)
    auto;
}

.app-shell__workspace--wizard {
  grid-template-columns: minmax(0, 1fr);
}

.app-shell__sidebar {
  border-right: 1px solid var(--color-border-subtle);
  min-height: 0;
  overflow: hidden;
}

.app-shell__content {
  background: var(--color-bg-canvas);
  flex: 1;
  min-height: 0;
  min-width: 640px;
  overflow-y: auto;
  position: relative;
}

.app-shell__detail {
  border-left: 1px solid var(--color-border-subtle);
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

@media (max-width: 1280px) {
  .app-shell__workspace,
  .app-shell[data-sidebar-collapsed="true"] .app-shell__workspace {
    grid-template-columns: var(--sidebar-width-expanded) minmax(0, 1fr);
  }

  .app-shell__detail {
    background: var(--color-bg-elevated);
    bottom: 0;
    box-shadow: var(--shadow-lg);
    position: absolute;
    right: 0;
    top: 0;
    z-index: var(--z-sidebar);
  }
}

@media (max-width: 960px) {
  .app-shell__workspace,
  .app-shell[data-sidebar-collapsed="true"] .app-shell__workspace {
    grid-template-columns: minmax(0, 1fr);
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
    transition: transform var(--motion-default) var(--ease-spring);
    width: var(--sidebar-width-expanded);
    z-index: var(--z-sidebar);
  }

  .app-shell[data-sidebar-collapsed="true"] .app-shell__sidebar {
    transform: translateX(calc(-1 * var(--sidebar-width-expanded)));
  }
}
</style>
