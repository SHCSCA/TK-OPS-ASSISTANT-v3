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
