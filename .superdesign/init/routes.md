# Superdesign 路由与页面映射

> 2026-07-19 原型覆盖：账号工作区保留 `workspace`、`knowledge`、`scripts`、`storyboard`、`deconstruction`、`production`、`library`、`toolbox`、`publishing`、`review` 十个入口；系统级入口为 `settings` 与账号切换器内的 `account_management`。本轮明确不设计 AI 剪辑工作台或时间线路由。

## 全局布局

- 正常工作态：`apps/desktop/src/layouts/AppShell.vue`
- 启动门禁：`apps/desktop/src/bootstrap/BootstrapGate.vue`
- 向导页：不显示正常 Sidebar / Detail Panel；其余页面使用稳定桌面壳。

## 16 页映射

| URL | Route ID | 页面 | 入口组件 | 页面类型 | Detail / Status |
| --- | --- | --- | --- | --- | --- |
| `/setup/license` | `setup_license_wizard` | 首启与许可证向导 | `apps/desktop/src/pages/setup/SetupLicenseWizardPage.vue` | wizard | hidden / setup |
| `/dashboard` | `creator_dashboard` | 创作总览 | `apps/desktop/src/pages/dashboard/CreatorDashboardPage.vue` | dashboard | contextual / overview |
| `/scripts/topics` | `script_topic_center` | 脚本与选题中心 | `apps/desktop/src/pages/scripts/ScriptTopicCenterPage.vue` | editor | contextual / editing |
| `/storyboards/planning` | `storyboard_planning_center` | 分镜规划中心 | `apps/desktop/src/pages/storyboards/StoryboardPlanningCenterPage.vue` | editor | contextual / editing |
| `/workspace/editing` | `ai_editing_workspace` | AI 剪辑工作台 | `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue` | workspace | asset / editing |
| `/video/deconstruction` | `video_deconstruction_center` | 视频拆解中心 | `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue` | workspace | logs / review |
| `/voice/studio` | `voice_studio` | 配音中心 | `apps/desktop/src/pages/voice/VoiceStudioPage.vue` | editor | contextual / editing |
| `/subtitles/alignment` | `subtitle_alignment_center` | 字幕对齐中心 | `apps/desktop/src/pages/subtitles/SubtitleAlignmentCenterPage.vue` | editor | contextual / editing |
| `/assets/library` | `asset_library` | 资产中心 | `apps/desktop/src/pages/assets/AssetLibraryPage.vue` | workspace | asset / overview |
| `/accounts` | `account_management` | 账号管理 | `apps/desktop/src/pages/accounts/AccountManagementPage.vue` | management | binding / system |
| `/devices/workspaces` | `device_workspace_management` | 设备与工作区管理 | `apps/desktop/src/pages/devices/DeviceWorkspaceManagementPage.vue` | management | binding / system |
| `/automation/console` | `automation_console` | 自动化执行中心 | `apps/desktop/src/pages/automation/AutomationConsolePage.vue` | queue | logs / tasks |
| `/publishing/center` | `publishing_center` | 发布中心 | `apps/desktop/src/pages/publishing/PublishingCenterPage.vue` | queue | binding / publishing |
| `/renders/export` | `render_export_center` | 渲染与导出中心 | `apps/desktop/src/pages/renders/RenderExportCenterPage.vue` | queue | logs / rendering |
| `/review/optimization` | `review_optimization_center` | 复盘与优化中心 | `apps/desktop/src/pages/review/ReviewOptimizationCenterPage.vue` | workspace | logs / review |
| `/settings/ai-system` | `ai_system_settings` | AI 与系统设置 | `apps/desktop/src/pages/settings/AISystemSettingsPage.vue` | settings | settings / system |

## 关键页面摘要

- 创作总览：最近项目、继续创作、任务与异常入口。
- 脚本与选题：三栏编辑流，维护主题、脚本、版本与 AI 动作。
- 分镜规划：脚本段落到镜头卡片的双向映射和同步状态。
- AI 剪辑工作台：素材、预览、属性、工具、时间线和智能粗剪审阅中枢。
- 视频拆解：导入、解析、转写、结构化与局部重试。
- 配音 / 字幕：共享脚本、音轨、字幕版本和生成 / 对齐状态。
- 渲染 / 发布：队列、预检、输出 / 回执与失败恢复。
- 设置：Provider、能力矩阵、配置总线、路径与诊断。

## 完整路由源码

### route-ids.ts

```ts
export const routeIds = {
  setupLicenseWizard: "setup_license_wizard",
  creatorDashboard: "creator_dashboard",
  scriptTopicCenter: "script_topic_center",
  storyboardPlanningCenter: "storyboard_planning_center",
  aiEditingWorkspace: "ai_editing_workspace",
  videoDeconstructionCenter: "video_deconstruction_center",
  voiceStudio: "voice_studio",
  subtitleAlignmentCenter: "subtitle_alignment_center",
  assetLibrary: "asset_library",
  accountManagement: "account_management",
  deviceWorkspaceManagement: "device_workspace_management",
  automationConsole: "automation_console",
  publishingCenter: "publishing_center",
  renderExportCenter: "render_export_center",
  reviewOptimizationCenter: "review_optimization_center",
  aiSystemSettings: "ai_system_settings"
} as const;

export type RouteId = (typeof routeIds)[keyof typeof routeIds];

```

### route-manifest.ts

```ts
import type { RouteManifestItem } from "@/types/router";
import SetupLicenseWizardPage from "@/pages/setup/SetupLicenseWizardPage.vue";

import { routeIds } from "./route-ids";

export const routeManifest: RouteManifestItem[] = [
  {
    id: routeIds.setupLicenseWizard,
    path: "/setup/license",
    title: "首启与许可证向导",
    navGroup: "HIDDEN",
    icon: "vpn_key",
    pageType: "wizard",
    requiresLicense: false,
    requiresProjectContext: false,
    detailPanelMode: "hidden",
    statusBarMode: "setup",
    componentImport: "@/pages/setup/SetupLicenseWizardPage.vue",
    loadComponent: async () => ({ default: SetupLicenseWizardPage })
  },
  {
    id: routeIds.creatorDashboard,
    path: "/dashboard",
    title: "创作总览",
    navGroup: "启动与总览",
    icon: "dashboard",
    pageType: "dashboard",
    requiresLicense: true,
    requiresProjectContext: false,
    detailPanelMode: "contextual",
    statusBarMode: "overview",
    componentImport: "@/pages/dashboard/CreatorDashboardPage.vue",
    loadComponent: () => import("@/pages/dashboard/CreatorDashboardPage.vue")
  },
  {
    id: routeIds.accountManagement,
    path: "/accounts",
    title: "账号管理",
    navGroup: "执行与治理",
    icon: "manage_accounts",
    pageType: "management",
    requiresLicense: true,
    requiresProjectContext: false,
    detailPanelMode: "binding",
    statusBarMode: "system",
    componentImport: "@/pages/accounts/AccountManagementPage.vue",
    loadComponent: () => import("@/pages/accounts/AccountManagementPage.vue")
  },
  {
    id: routeIds.deviceWorkspaceManagement,
    path: "/devices/workspaces",
    title: "设备与工作区管理",
    navGroup: "执行与治理",
    icon: "devices",
    pageType: "management",
    requiresLicense: true,
    requiresProjectContext: false,
    detailPanelMode: "binding",
    statusBarMode: "system",
    componentImport: "@/pages/devices/DeviceWorkspaceManagementPage.vue",
    loadComponent: () => import("@/pages/devices/DeviceWorkspaceManagementPage.vue")
  },
  {
    id: routeIds.automationConsole,
    path: "/automation/console",
    title: "自动化执行中心",
    navGroup: "执行与治理",
    icon: "smart_toy",
    pageType: "queue",
    requiresLicense: true,
    requiresProjectContext: false,
    detailPanelMode: "logs",
    statusBarMode: "tasks",
    componentImport: "@/pages/automation/AutomationConsolePage.vue",
    loadComponent: () => import("@/pages/automation/AutomationConsolePage.vue")
  },
  {
    id: routeIds.aiSystemSettings,
    path: "/settings/ai-system",
    title: "AI 与系统设置",
    navGroup: "系统与 AI",
    icon: "settings",
    pageType: "settings",
    requiresLicense: true,
    requiresProjectContext: false,
    detailPanelMode: "settings",
    statusBarMode: "system",
    componentImport: "@/pages/settings/AISystemSettingsPage.vue",
    loadComponent: () => import("@/pages/settings/AISystemSettingsPage.vue")
  },
  {
    id: routeIds.scriptTopicCenter,
    path: "/scripts/topics",
    title: "企划: 脚本与选题",
    navGroup: "创作前置",
    icon: "description",
    pageType: "editor",
    requiresLicense: true,
    requiresProjectContext: true,
    detailPanelMode: "contextual",
    statusBarMode: "editing",
    componentImport: "@/pages/scripts/ScriptTopicCenterPage.vue",
    loadComponent: () => import("@/pages/scripts/ScriptTopicCenterPage.vue")
  },
  {
    id: routeIds.storyboardPlanningCenter,
    path: "/storyboards/planning",
    title: "企划: 分镜规划",
    navGroup: "创作前置",
    icon: "view_timeline",
    pageType: "editor",
    requiresLicense: true,
    requiresProjectContext: true,
    detailPanelMode: "contextual",
    statusBarMode: "editing",
    componentImport: "@/pages/storyboards/StoryboardPlanningCenterPage.vue",
    loadComponent: () => import("@/pages/storyboards/StoryboardPlanningCenterPage.vue")
  },
  {
    id: routeIds.videoDeconstructionCenter,
    path: "/video/deconstruction",
    title: "制作: 视频拆解",
    navGroup: "创作前置",
    icon: "content_cut",
    pageType: "workspace",
    requiresLicense: true,
    requiresProjectContext: true,
    detailPanelMode: "logs",
    statusBarMode: "review",
    componentImport: "@/pages/video/VideoDeconstructionCenterPage.vue",
    loadComponent: () => import("@/pages/video/VideoDeconstructionCenterPage.vue")
  },
  {
    id: routeIds.aiEditingWorkspace,
    path: "/workspace/editing",
    title: "制作: AI 剪辑工作台",
    navGroup: "创作与媒体",
    icon: "movie_edit",
    pageType: "workspace",
    requiresLicense: true,
    requiresProjectContext: true,
    detailPanelMode: "asset",
    statusBarMode: "editing",
    componentImport: "@/pages/workspace/AIEditingWorkspacePage.vue",
    loadComponent: () => import("@/pages/workspace/AIEditingWorkspacePage.vue")
  },
  {
    id: routeIds.assetLibrary,
    path: "/assets/library",
    title: "制作: 资产中心",
    navGroup: "创作与媒体",
    icon: "inventory",
    pageType: "workspace",
    requiresLicense: true,
    requiresProjectContext: true,
    detailPanelMode: "asset",
    statusBarMode: "overview",
    componentImport: "@/pages/assets/AssetLibraryPage.vue",
    loadComponent: () => import("@/pages/assets/AssetLibraryPage.vue")
  },
  {
    id: routeIds.voiceStudio,
    path: "/voice/studio",
    title: "媒体: 配音中心",
    navGroup: "创作与媒体",
    icon: "mic",
    pageType: "editor",
    requiresLicense: true,
    requiresProjectContext: true,
    detailPanelMode: "contextual",
    statusBarMode: "editing",
    componentImport: "@/pages/voice/VoiceStudioPage.vue",
    loadComponent: () => import("@/pages/voice/VoiceStudioPage.vue")
  },
  {
    id: routeIds.subtitleAlignmentCenter,
    path: "/subtitles/alignment",
    title: "媒体: 字幕对齐",
    navGroup: "创作与媒体",
    icon: "subtitles",
    pageType: "editor",
    requiresLicense: true,
    requiresProjectContext: true,
    detailPanelMode: "contextual",
    statusBarMode: "editing",
    componentImport: "@/pages/subtitles/SubtitleAlignmentCenterPage.vue",
    loadComponent: () => import("@/pages/subtitles/SubtitleAlignmentCenterPage.vue")
  },
  {
    id: routeIds.renderExportCenter,
    path: "/renders/export",
    title: "交付: 渲染与导出",
    navGroup: "创作与媒体",
    icon: "output",
    pageType: "queue",
    requiresLicense: true,
    requiresProjectContext: true,
    detailPanelMode: "logs",
    statusBarMode: "rendering",
    componentImport: "@/pages/renders/RenderExportCenterPage.vue",
    loadComponent: () => import("@/pages/renders/RenderExportCenterPage.vue")
  },
  {
    id: routeIds.publishingCenter,
    path: "/publishing/center",
    title: "交付: 发布中心",
    navGroup: "执行与治理",
    icon: "publish",
    pageType: "queue",
    requiresLicense: true,
    requiresProjectContext: true,
    detailPanelMode: "binding",
    statusBarMode: "publishing",
    componentImport: "@/pages/publishing/PublishingCenterPage.vue",
    loadComponent: () => import("@/pages/publishing/PublishingCenterPage.vue")
  },
  {
    id: routeIds.reviewOptimizationCenter,
    path: "/review/optimization",
    title: "交付: 复盘与优化",
    navGroup: "执行与治理",
    icon: "analytics",
    pageType: "workspace",
    requiresLicense: true,
    requiresProjectContext: true,
    detailPanelMode: "logs",
    statusBarMode: "review",
    componentImport: "@/pages/review/ReviewOptimizationCenterPage.vue",
    loadComponent: () => import("@/pages/review/ReviewOptimizationCenterPage.vue")
  }
];

```

### index.ts

```ts
import {
  createRouter,
  createWebHistory,
  type RouteLocationNormalized,
  type RouteRecordRaw,
  type Router,
  type RouterHistory
} from "vue-router";
import type { Pinia } from "pinia";

import { useLicenseStore } from "@/stores/license";
import { useProjectStore } from "@/stores/project";

import { routeIds } from "./route-ids";
import { routeManifest } from "./route-manifest";

function createRoutes(): RouteRecordRaw[] {
  const pages: RouteRecordRaw[] = routeManifest.map((item) => ({
    path: item.path,
    name: item.id,
    component: item.loadComponent,
    meta: {
      detailPanelMode: item.detailPanelMode,
      navGroup: item.navGroup,
      pageType: item.pageType,
      requiresLicense: item.requiresLicense,
      routeId: item.id,
      statusBarMode: item.statusBarMode,
      title: item.title
    }
  }));

  return [
    { path: "/", redirect: "/dashboard" },
    ...pages,
    { path: "/:pathMatch(.*)*", redirect: "/dashboard" }
  ];
}

function findRouteItem(route: RouteLocationNormalized) {
  return routeManifest.find((item) => item.id === route.name);
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

export function createAppRouter(
  pinia: Pinia,
  history: RouterHistory = createWebHistory()
): Router {
  const router = createRouter({
    history,
    routes: createRoutes()
  });

  router.beforeEach(async (to) => {
    const licenseStore = useLicenseStore(pinia);
    const projectStore = useProjectStore(pinia);
    const target = findRouteItem(to);
    if (!target) {
      return true;
    }

    if (licenseStore.status === "idle") {
      await licenseStore.loadStatus();
    }

    if (target.id === routeIds.setupLicenseWizard && licenseStore.active && !to.query.preview) {
      return resolveRedirectTarget(to.query.redirect);
    }

    if (target.requiresLicense && !licenseStore.active) {
      return {
        path: "/setup/license",
        query: {
          redirect: to.fullPath
        }
      };
    }

    if (target.requiresProjectContext) {
      if (projectStore.status === "idle") {
        await projectStore.load();
      }
      // Removed hard redirect to /dashboard.
      // Individual pages will handle missing context via ProjectContextGuard.
    }

    return true;
  });

  return router;
}

export * from "./route-ids";
export * from "./route-manifest";

```
