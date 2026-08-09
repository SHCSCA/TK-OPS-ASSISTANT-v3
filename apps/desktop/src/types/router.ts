import type { RouteComponent } from "vue-router";

import type { RouteId } from "@/app/router/route-ids";

export type RouteNavSection =
  | "strategy"
  | "creation"
  | "delivery"
  | "system"
  | "hidden";

export type RouteMigrationState =
  | "ready"
  | "p0_foundation"
  | "p1_pending"
  | "p2_pending";

export type RouteManifestItem = {
  id: RouteId;
  path: string;
  title: string;
  icon: string;
  navOrder: number | null;
  navSection: RouteNavSection;
  scope: "system" | "account";
  requiresLicense: boolean;
  requiresRuntimeReady: boolean;
  migrationState: RouteMigrationState;
  detailPanelMode: "hidden" | "contextual" | "overlay";
  componentImport: string;
  loadComponent: () => Promise<RouteComponent>;
};
