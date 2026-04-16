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

    if (target.id === routeIds.setupLicenseWizard && licenseStore.active) {
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
