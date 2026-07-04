export type RouteNavGroup = "启动与总览" | "创作前置" | "创作与媒体" | "执行与治理" | "系统与 AI" | "HIDDEN";

export type RouteManifestItem = {
  id: string;
  path: string;
  title: string;
  navGroup: RouteNavGroup;
  icon: string;
  pageType: string;
  requiresLicense: boolean;
  requiresProjectContext: boolean;
  detailPanelMode: string;
  statusBarMode: string;
  componentImport: string;
  loadComponent: () => Promise<unknown>;
};
