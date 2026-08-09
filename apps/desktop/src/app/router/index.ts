import {
  createRouter,
  createWebHistory,
  type RouteLocationNormalized,
  type RouteRecordRaw,
  type Router,
  type RouterHistory
} from "vue-router";
import type { Pinia } from "pinia";

import { useP0BootstrapStore } from "@/modules/system/bootstrap-store";

import { resolveInternalRedirect } from "./internal-redirect";
import { createLegacyRedirects } from "./legacy-redirects";
import { routeIds } from "./route-ids";
import { routeManifest } from "./route-manifest";

function createRoutes(): RouteRecordRaw[] {
  const pages: RouteRecordRaw[] = routeManifest.map((item) => ({
    path: item.path,
    name: item.id,
    component: item.loadComponent,
    meta: {
      detailPanelMode: item.detailPanelMode,
      migrationState: item.migrationState,
      navOrder: item.navOrder,
      navSection: item.navSection,
      requiresLicense: item.requiresLicense,
      requiresRuntimeReady: item.requiresRuntimeReady,
      routeId: item.id,
      scope: item.scope,
      title: item.title
    }
  }));

  return [
    {
      path: "/",
      redirect: "/workspace"
    },
    ...pages,
    ...createLegacyRedirects(),
    {
      path: "/:pathMatch(.*)*",
      redirect: "/workspace"
    }
  ];
}

function findRouteItem(route: RouteLocationNormalized) {
  return routeManifest.find((item) => item.id === route.name);
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
    return guardP0Route(pinia, to);
  });

  return router;
}

async function guardP0Route(
  pinia: Pinia,
  to: RouteLocationNormalized
) {
  const target = findRouteItem(to);
  if (!target) return true;

  const bootstrapStore = useP0BootstrapStore(pinia);
  if (bootstrapStore.phase === "idle") {
    await bootstrapStore.load();
  }
  if (
    target.id === routeIds.setupLicenseWizard
    && bootstrapStore.phase === "ready"
    && !to.query.preview
  ) {
    return resolveInternalRedirect(to.query.redirect, "/workspace");
  }
  if (
    (
      target.requiresLicense
      || target.requiresRuntimeReady
    )
    && bootstrapStore.phase !== "ready"
  ) {
    return {
      path: "/setup/license",
      query: { redirect: to.fullPath }
    };
  }
  return true;
}

export * from "./route-ids";
export * from "./route-manifest";
export {
  LEGACY_MIGRATION_QUERY_KEY,
  resolveLegacyMigrationMessage
} from "./legacy-redirects";
