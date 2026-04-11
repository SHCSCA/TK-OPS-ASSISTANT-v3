export type RouteManifestItem = {
  id: string;
  path: string;
  title: string;
  navGroup: string;
  icon: string;
  pageType: string;
  requiresLicense: boolean;
  requiresProjectContext: boolean;
  detailPanelMode: string;
  statusBarMode: string;
  componentImport: string;
  loadComponent: () => Promise<unknown>;
};
