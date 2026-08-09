(function registerOperationsRenderers(global) {
  "use strict";

  const namespace = global.TkPrototype = global.TkPrototype || {};
  namespace.renderers = namespace.renderers || {};

  function icon(name) {
    return `<span class="icon" aria-hidden="true">${name}</span>`;
  }

  function button(label, action, iconName, variant = "secondary") {
    return `<button class="button button--${variant}" type="button" data-action="${action}">${icon(iconName)}<span>${label}</span></button>`;
  }

  function emptyBinding(title, iconName, actionLabel, action) {
    return `
      <section class="page-canvas quiet-page">
        <header class="object-bar"><div class="object-bar__identity">${icon(iconName)}<strong>${title}</strong></div></header>
        <div class="quiet-empty"><span>${icon(iconName)}</span><strong>暂无真实对象</strong>${button(actionLabel, action, "add", "primary")}</div>
      </section>`;
  }

  function queuePage(title, iconName, primaryLabel, state, kind) {
    const status = state.error ? "failed" : state.taskStatus;
    const labels = { idle: "等待任务", queued: "排队", running: "运行中", completed: "已完成", failed: "失败" };
    return `
      <section class="page-canvas queue-canvas">
        <header class="object-bar"><div class="object-bar__identity">${icon(iconName)}<strong>${title}</strong></div><div class="object-bar__actions">${button(primaryLabel, "run-task", kind === "publish" ? "publish" : kind === "render" ? "movie" : "play_arrow", "primary")}</div></header>
        <div class="queue-board">
          <div class="queue-lane"><span class="queue-lane__label">队列</span><button class="task-row ${status !== "idle" ? "is-active" : ""}" type="button" data-action="open-task"><span class="task-row__icon">${icon(iconName)}</span><strong>原型任务</strong><span class="task-state task-state--${status}">${labels[status] || labels.idle}</span></button></div>
          <div class="queue-focus"><div class="queue-focus__visual">${icon(status === "failed" ? "error" : status === "completed" ? "check_circle" : iconName)}</div><strong>${labels[status] || labels.idle}</strong>${status === "failed" ? button("重试", "recover-error", "refresh", "primary") : status === "idle" ? button(primaryLabel, "run-task", "play_arrow", "primary") : ""}</div>
        </div>
      </section>`;
  }

  namespace.renderers.accounts = function renderAccounts() {
    return emptyBinding("账号管理", "manage_accounts", "绑定账号", "create-binding");
  };

  namespace.renderers.devices = function renderDevices() {
    return emptyBinding("设备与工作区", "devices", "添加工作区", "create-workspace");
  };

  namespace.renderers.review = function renderReview() {
    return emptyBinding("复盘与优化", "analytics", "选择已发布项目", "open-dashboard");
  };

  namespace.renderers.automation = function renderAutomation(state) {
    return queuePage("自动化执行", "smart_toy", "新建执行", state, "automation");
  };

  namespace.renderers.publishing = function renderPublishing(state) {
    return queuePage("发布中心", "publish", "准备发布", state, "publish");
  };

  namespace.renderers.render = function renderRender(state) {
    return queuePage("渲染与导出", "output", "开始渲染", state, "render");
  };

  namespace.renderers.settings = function renderSettings(state) {
    const section = state.settingsSection;
    return `
      <section class="page-canvas settings-canvas">
        <header class="object-bar"><div class="object-bar__identity">${icon("settings")}<strong>AI 与系统设置</strong></div><div class="object-bar__actions">${button("保存", "save", "save", "primary")}</div></header>
        <div class="settings-layout">
          <nav class="settings-rail" aria-label="设置分区">
            <button class="${section === "providers" ? "is-active" : ""}" type="button" data-action="settings-section" data-id="providers">${icon("hub")}<span>Provider</span></button>
            <button class="${section === "paths" ? "is-active" : ""}" type="button" data-action="settings-section" data-id="paths">${icon("folder") }<span>目录</span></button>
            <button class="${section === "diagnostics" ? "is-active" : ""}" type="button" data-action="settings-section" data-id="diagnostics">${icon("monitor_heart")}<span>诊断</span></button>
          </nav>
          ${renderSettingsPanel(section)}
        </div>
      </section>`;
  };

  function renderSettingsPanel(section) {
    if (section === "paths") {
      return `<div class="settings-panel"><label class="field"><span>工作区</span><input value="本地工作区" readonly></label><label class="field"><span>导出目录</span><input value="等待选择" readonly></label>${button("选择目录", "choose-path", "folder_open", "secondary")}</div>`;
    }
    if (section === "diagnostics") {
      return `<div class="settings-panel"><div class="diagnostic-row"><span class="status-dot status-dot--runtime"></span><strong>Runtime</strong><span>在线</span></div><div class="diagnostic-row"><span class="status-dot status-dot--ai"></span><strong>AI 能力</strong><span>可用</span></div>${button("重新检查", "diagnostics", "refresh", "secondary")}</div>`;
    }
    return `<div class="settings-panel"><label class="field"><span>Provider</span><select><option>本地原型 Provider</option></select></label><label class="field"><span>模型</span><select><option>等待真实配置</option></select></label>${button("连接测试", "diagnostics", "network_check", "secondary")}</div>`;
  }
})(window);
