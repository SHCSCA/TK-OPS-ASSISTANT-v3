export const routeIds = {
  setupLicenseWizard: "setup_license_wizard",
  accountWorkspaceHome: "account_workspace_home",
  accountStrategyKnowledge: "account_strategy_knowledge",
  accountScriptTopic: "account_script_topic",
  accountStoryboardPlanning: "account_storyboard_planning",
  accountVideoDeconstruction: "account_video_deconstruction",
  accountBatchProduction: "account_batch_production",
  accountContentLibrary: "account_content_library",
  accountMediaToolbox: "account_media_toolbox",
  accountPublishing: "account_publishing",
  accountReview: "account_review",
  accountManagement: "account_management",
  aiSystemSettings: "ai_system_settings"
} as const;

export type RouteId = (typeof routeIds)[keyof typeof routeIds];
