(function bootstrapConfig(global) {
  "use strict";

  const namespace = global.TkPrototype = global.TkPrototype || {};

  namespace.config = Object.freeze({
    appName: "TK-OPS 本地交互原型",
    defaultRouteId: "ai_editing_workspace",
    defaultTheme: "dark",
    storageKey: "tkops-prototype-v1",
    taskDurations: Object.freeze({ queued: 650, running: 1700, completed: 2300 }),
    viewport: Object.freeze({ compact: 1200, minimumWidth: 960, minimumHeight: 640 }),
    shell: Object.freeze({
      titleBarHeight: 48,
      sidebarCollapsed: 64,
      sidebarExpanded: 280,
      detailRail: 44,
      detailPanel: 360,
      statusBarHeight: 28
    }),
    labels: Object.freeze({
      project: "原型项目",
      runtimeOnline: "Runtime 已连接",
      runtimeOffline: "Runtime 连接异常",
      noSelection: "未选择对象"
    })
  });
})(window);
