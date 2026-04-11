import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
  type Router,
  type RouterHistory
} from "vue-router";

import { routeManifest } from "./route-manifest";

function createRoutes(): RouteRecordRaw[] {
  return routeManifest.map((item) => ({
    path: item.path,
    name: item.id,
    component: item.loadComponent,
    meta: {
      detailPanelMode: item.detailPanelMode,
      navGroup: item.navGroup,
      pageType: item.pageType,
      routeId: item.id,
      statusBarMode: item.statusBarMode,
      title: item.title
    }
  }));
}

export function createAppRouter(history: RouterHistory = createWebHistory()): Router {
  return createRouter({
    history,
    routes: createRoutes()
  });
}

export * from "./route-ids";
export * from "./route-manifest";
