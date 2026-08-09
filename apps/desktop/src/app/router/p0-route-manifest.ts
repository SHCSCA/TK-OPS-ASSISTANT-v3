import type { RouteManifestItem } from "@/types/router";
import P0SetupLicenseWizardPage from "@/pages/setup/P0SetupLicenseWizardPage.vue";

import { routeIds } from "./route-ids";

const loadPendingCapability = () =>
  import("@/pages/workspace-home/AccountCapabilityPendingPage.vue");

export const p0RouteManifest: RouteManifestItem[] = [
  {
    id: routeIds.setupLicenseWizard,
    path: "/setup/license",
    title: "首启与许可证",
    icon: "vpn_key",
    navOrder: null,
    navSection: "hidden",
    scope: "system",
    requiresLicense: false,
    requiresRuntimeReady: false,
    migrationState: "ready",
    detailPanelMode: "hidden",
    componentImport: "@/pages/setup/P0SetupLicenseWizardPage.vue",
    loadComponent: async () => ({ default: P0SetupLicenseWizardPage })
  },
  {
    id: routeIds.accountWorkspaceHome,
    path: "/workspace",
    title: "工作台",
    icon: "space_dashboard",
    navOrder: 1,
    navSection: "strategy",
    scope: "account",
    requiresLicense: true,
    requiresRuntimeReady: true,
    migrationState: "p0_foundation",
    detailPanelMode: "contextual",
    componentImport: "@/pages/workspace-home/AccountWorkspaceHomePage.vue",
    loadComponent: () =>
      import("@/pages/workspace-home/AccountWorkspaceHomePage.vue")
  },
  {
    id: routeIds.accountStrategyKnowledge,
    path: "/strategy-knowledge",
    title: "定位与知识",
    icon: "target",
    navOrder: 2,
    navSection: "strategy",
    scope: "account",
    requiresLicense: true,
    requiresRuntimeReady: true,
    migrationState: "p0_foundation",
    detailPanelMode: "contextual",
    componentImport:
      "@/pages/strategy-knowledge/AccountStrategyKnowledgePage.vue",
    loadComponent: () =>
      import(
        "@/pages/strategy-knowledge/AccountStrategyKnowledgePage.vue"
      )
  },
  {
    id: routeIds.accountScriptTopic,
    path: "/scripts",
    title: "脚本与选题",
    icon: "description",
    navOrder: 3,
    navSection: "creation",
    scope: "account",
    requiresLicense: true,
    requiresRuntimeReady: true,
    migrationState: "p1_pending",
    detailPanelMode: "contextual",
    componentImport: "@/pages/workspace-home/AccountCapabilityPendingPage.vue",
    loadComponent: loadPendingCapability
  },
  {
    id: routeIds.accountStoryboardPlanning,
    path: "/storyboards",
    title: "分镜规划",
    icon: "view_timeline",
    navOrder: 4,
    navSection: "creation",
    scope: "account",
    requiresLicense: true,
    requiresRuntimeReady: true,
    migrationState: "p1_pending",
    detailPanelMode: "contextual",
    componentImport: "@/pages/workspace-home/AccountCapabilityPendingPage.vue",
    loadComponent: loadPendingCapability
  },
  {
    id: routeIds.accountVideoDeconstruction,
    path: "/video-deconstruction",
    title: "视频拆解",
    icon: "video_library",
    navOrder: 5,
    navSection: "creation",
    scope: "account",
    requiresLicense: true,
    requiresRuntimeReady: true,
    migrationState: "p1_pending",
    detailPanelMode: "overlay",
    componentImport: "@/pages/workspace-home/AccountCapabilityPendingPage.vue",
    loadComponent: loadPendingCapability
  },
  {
    id: routeIds.accountBatchProduction,
    path: "/production/batches",
    title: "批量生产",
    icon: "deployed_code",
    navOrder: 6,
    navSection: "delivery",
    scope: "account",
    requiresLicense: true,
    requiresRuntimeReady: true,
    migrationState: "p1_pending",
    detailPanelMode: "overlay",
    componentImport: "@/pages/workspace-home/AccountCapabilityPendingPage.vue",
    loadComponent: loadPendingCapability
  },
  {
    id: routeIds.accountContentLibrary,
    path: "/content-library",
    title: "内容库",
    icon: "inventory_2",
    navOrder: 7,
    navSection: "delivery",
    scope: "account",
    requiresLicense: true,
    requiresRuntimeReady: true,
    migrationState: "p1_pending",
    detailPanelMode: "overlay",
    componentImport: "@/pages/workspace-home/AccountCapabilityPendingPage.vue",
    loadComponent: loadPendingCapability
  },
  {
    id: routeIds.accountMediaToolbox,
    path: "/media-tools",
    title: "媒体工具箱",
    icon: "construction",
    navOrder: 8,
    navSection: "delivery",
    scope: "account",
    requiresLicense: true,
    requiresRuntimeReady: true,
    migrationState: "p1_pending",
    detailPanelMode: "overlay",
    componentImport: "@/pages/workspace-home/AccountCapabilityPendingPage.vue",
    loadComponent: loadPendingCapability
  },
  {
    id: routeIds.accountPublishing,
    path: "/publishing",
    title: "发布",
    icon: "send",
    navOrder: 9,
    navSection: "delivery",
    scope: "account",
    requiresLicense: true,
    requiresRuntimeReady: true,
    migrationState: "p2_pending",
    detailPanelMode: "overlay",
    componentImport: "@/pages/workspace-home/AccountCapabilityPendingPage.vue",
    loadComponent: loadPendingCapability
  },
  {
    id: routeIds.accountReview,
    path: "/review",
    title: "复盘",
    icon: "monitoring",
    navOrder: 10,
    navSection: "delivery",
    scope: "account",
    requiresLicense: true,
    requiresRuntimeReady: true,
    migrationState: "p2_pending",
    detailPanelMode: "overlay",
    componentImport: "@/pages/workspace-home/AccountCapabilityPendingPage.vue",
    loadComponent: loadPendingCapability
  },
  {
    id: routeIds.accountManagement,
    path: "/settings/accounts",
    title: "账号管理",
    icon: "manage_accounts",
    navOrder: null,
    navSection: "hidden",
    scope: "system",
    requiresLicense: true,
    requiresRuntimeReady: true,
    migrationState: "ready",
    detailPanelMode: "overlay",
    componentImport:
      "@/pages/settings/accounts/AccountManagementPage.vue",
    loadComponent: () =>
      import("@/pages/settings/accounts/AccountManagementPage.vue")
  },
  {
    id: routeIds.aiSystemSettings,
    path: "/settings/ai-system",
    title: "AI 与系统设置",
    icon: "settings",
    navOrder: 11,
    navSection: "system",
    scope: "system",
    requiresLicense: true,
    requiresRuntimeReady: true,
    migrationState: "ready",
    detailPanelMode: "overlay",
    componentImport:
      "@/pages/settings/ai-system/AISystemSettingsPage.vue",
    loadComponent: () =>
      import("@/pages/settings/ai-system/AISystemSettingsPage.vue")
  }
];
