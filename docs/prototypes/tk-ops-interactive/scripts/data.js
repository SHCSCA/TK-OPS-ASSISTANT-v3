(function registerPrototypeData(global) {
  "use strict";

  const namespace = global.TkPrototype = global.TkPrototype || {};

  namespace.navGroups = [
    {
      label: "启动与总览",
      pages: [
        { id: "setup_license_wizard", title: "首启与许可证", icon: "vpn_key", family: "setup", path: "/setup/license" },
        { id: "creator_dashboard", title: "创作总览", icon: "dashboard", family: "dashboard", path: "/dashboard" }
      ]
    },
    {
      label: "创作前置",
      pages: [
        { id: "script_topic_center", title: "脚本与选题", icon: "description", family: "script", path: "/scripts/topics" },
        { id: "storyboard_planning_center", title: "分镜规划", icon: "view_timeline", family: "storyboard", path: "/storyboards/planning" },
        { id: "video_deconstruction_center", title: "视频拆解", icon: "content_cut", family: "deconstruction", path: "/video/deconstruction" }
      ]
    },
    {
      label: "创作与媒体",
      pages: [
        { id: "ai_editing_workspace", title: "AI 剪辑工作台", icon: "movie_edit", family: "workspace", path: "/workspace/editing" },
        { id: "voice_studio", title: "配音中心", icon: "mic", family: "voice", path: "/voice/studio" },
        { id: "subtitle_alignment_center", title: "字幕对齐", icon: "subtitles", family: "subtitles", path: "/subtitles/alignment" },
        { id: "asset_library", title: "资产中心", icon: "inventory_2", family: "assets", path: "/assets/library" },
        { id: "render_export_center", title: "渲染与导出", icon: "output", family: "render", path: "/renders/export" }
      ]
    },
    {
      label: "执行与治理",
      pages: [
        { id: "account_management", title: "账号管理", icon: "manage_accounts", family: "accounts", path: "/accounts" },
        { id: "device_workspace_management", title: "设备与工作区", icon: "devices", family: "devices", path: "/devices/workspaces" },
        { id: "automation_console", title: "自动化执行", icon: "smart_toy", family: "automation", path: "/automation/console" },
        { id: "publishing_center", title: "发布中心", icon: "publish", family: "publishing", path: "/publishing/center" },
        { id: "review_optimization_center", title: "复盘与优化", icon: "analytics", family: "review", path: "/review/optimization" }
      ]
    },
    {
      label: "系统与 AI",
      pages: [
        { id: "ai_system_settings", title: "AI 与系统设置", icon: "settings", family: "settings", path: "/settings/ai-system" }
      ]
    }
  ];

  namespace.pages = namespace.navGroups
    .flatMap((group) => group.pages)
    .reduce((result, page) => {
      result[page.id] = page;
      return result;
    }, {});

  namespace.prototypeMedia = Object.freeze({
    assets: [
      { id: "asset-a", label: "片段 A", type: "video", icon: "videocam", tone: "video" },
      { id: "asset-b", label: "片段 B", type: "video", icon: "videocam", tone: "video" },
      { id: "asset-c", label: "旁白", type: "audio", icon: "graphic_eq", tone: "voice" }
    ],
    clips: [
      { id: "clip-a", label: "镜头 A", track: "画面", tone: "video", left: 4, width: 26 },
      { id: "clip-b", label: "镜头 B", track: "画面", tone: "video", left: 32, width: 22 },
      { id: "voice-a", label: "旁白", track: "配音", tone: "voice", left: 4, width: 52 },
      { id: "subtitle-a", label: "字幕", track: "字幕", tone: "subtitle", left: 6, width: 24 }
    ]
  });
})(window);
