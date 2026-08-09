import type {
  LocationQuery,
  LocationQueryRaw,
  RouteRecordRaw
} from "vue-router";

export const LEGACY_MIGRATION_QUERY_KEY = "__tkopsMigration";

type LegacyRedirectTarget = {
  path: string;
  migration: string;
  query?: LocationQueryRaw;
};

const LEGACY_REDIRECTS: Record<string, LegacyRedirectTarget> = {
  "/dashboard": {
    path: "/workspace",
    migration: "dashboard"
  },
  "/accounts": {
    path: "/settings/accounts",
    migration: "accounts"
  },
  "/devices/workspaces": {
    path: "/settings/ai-system",
    migration: "devices",
    query: { section: "runtime" }
  },
  "/automation/console": {
    path: "/workspace",
    migration: "automation"
  },
  "/scripts/topics": {
    path: "/scripts",
    migration: "scripts"
  },
  "/storyboards/planning": {
    path: "/storyboards",
    migration: "storyboards"
  },
  "/video/deconstruction": {
    path: "/video-deconstruction",
    migration: "video-deconstruction"
  },
  "/workspace/editing": {
    path: "/production/batches",
    migration: "editing"
  },
  "/assets/library": {
    path: "/content-library",
    migration: "assets"
  },
  "/voice/studio": {
    path: "/production/batches",
    migration: "voice"
  },
  "/subtitles/alignment": {
    path: "/production/batches",
    migration: "subtitles"
  },
  "/renders/export": {
    path: "/production/batches",
    migration: "renders"
  },
  "/publishing/center": {
    path: "/publishing",
    migration: "publishing"
  },
  "/review/optimization": {
    path: "/review",
    migration: "review"
  }
};

const MIGRATION_MESSAGES: Record<string, string> = {
  dashboard: "旧创作总览已迁移到当前账号的工作台。",
  accounts: "账号管理已迁移到左下角账号切换器。",
  devices: "设备与执行环境已归入 AI 与系统设置。",
  automation: "旧自动化中心已退出主导航，任务入口将按账号能力逐步接入。",
  scripts: "脚本与选题已迁移到当前账号的创作链路。",
  storyboards: "分镜规划已迁移到当前账号的创作链路。",
  "video-deconstruction": "视频拆解已迁移到当前账号的创作链路。",
  editing: "旧 AI 剪辑工作台已退出主线，自动合成统一由批量生产承接。",
  assets: "旧资产中心已迁移为按账号隔离的内容库。",
  voice: "独立配音入口已合并到批量生产阶段。",
  subtitles: "独立字幕入口已合并到批量生产阶段。",
  renders: "独立渲染入口已合并到批量生产阶段。",
  publishing: "发布中心已迁移到当前账号的发布页面。",
  review: "复盘与优化已迁移到当前账号的复盘页面。"
};

export function createLegacyRedirects(): RouteRecordRaw[] {
  return Object.entries(LEGACY_REDIRECTS).map(([path, target]) => ({
    path,
    redirect: (route) => ({
      path: target.path,
      query: mergeRedirectQuery(route, target),
      hash: route.hash
    })
  }));
}

export function resolveLegacyMigrationMessage(
  value: unknown
): string | null {
  if (typeof value !== "string") {
    return null;
  }
  return MIGRATION_MESSAGES[value] ?? null;
}

function mergeRedirectQuery(
  route: { query: LocationQuery },
  target: LegacyRedirectTarget
): LocationQueryRaw {
  const query: LocationQueryRaw = { ...route.query };
  for (const [key, value] of Object.entries(target.query ?? {})) {
    if (query[key] === undefined) {
      query[key] = value;
    }
  }
  if (query[LEGACY_MIGRATION_QUERY_KEY] === undefined) {
    query[LEGACY_MIGRATION_QUERY_KEY] = target.migration;
  }
  return query;
}
