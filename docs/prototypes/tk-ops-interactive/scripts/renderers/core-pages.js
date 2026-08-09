(function registerCoreRenderers(global) {
  "use strict";

  const namespace = global.TkPrototype = global.TkPrototype || {};
  namespace.renderers = namespace.renderers || {};

  function icon(name) {
    return `<span class="icon" aria-hidden="true">${name}</span>`;
  }

  function actionButton(label, action, iconName, variant = "secondary") {
    return `<button class="button button--${variant}" type="button" data-action="${action}">${icon(iconName)}<span>${label}</span></button>`;
  }

  namespace.renderers.setup = function renderSetup() {
    return `
      <section class="setup-stage" aria-label="首启与许可证向导">
        <div class="setup-card">
          <div class="setup-card__mark">${icon("vpn_key")}</div>
          <div class="setup-card__steps" aria-label="首启进度">
            <span class="is-complete"></span><span class="is-current"></span><span></span>
          </div>
          <h1>激活本机</h1>
          <label class="field">
            <span>许可证码</span>
            <input value="" placeholder="输入许可证码" autocomplete="off">
          </label>
          ${actionButton("验证并继续", "setup-continue", "arrow_forward", "primary")}
          <button class="text-button" type="button" data-action="setup-diagnostics">连接诊断</button>
        </div>
      </section>`;
  };

  namespace.renderers.dashboard = function renderDashboard() {
    return `
      <section class="page-canvas dashboard-canvas">
        <header class="object-bar">
          <strong>继续创作</strong>
          ${actionButton("新建项目", "new-project", "add", "primary")}
        </header>
        <div class="project-strip">
          <button class="project-tile is-active" type="button" data-action="open-workspace">
            <span class="project-tile__visual">${icon("movie_edit")}</span>
            <span>原型项目</span>
            <small>AI 剪辑工作台</small>
          </button>
          <button class="project-tile project-tile--new" type="button" data-action="new-project">
            ${icon("add")}
            <span>新建</span>
          </button>
        </div>
        <div class="quiet-dock" aria-label="项目链路">
          <span class="is-done">脚本</span><i></i><span class="is-done">分镜</span><i></i><span class="is-current">剪辑</span><i></i><span>导出</span>
        </div>
      </section>`;
  };

  namespace.renderers.script = function renderScript() {
    return `
      <section class="page-canvas editor-canvas">
        <header class="object-bar">
          <div class="object-bar__identity">${icon("description")}<strong>脚本 v1</strong><span class="save-dot" title="已保存"></span></div>
          <div class="object-bar__actions">
            ${actionButton("AI 改写", "run-task", "auto_awesome", "ai")}
            ${actionButton("保存", "save", "save", "secondary")}
          </div>
        </header>
        <div class="editor-grid editor-grid--script">
          <aside class="compact-list" aria-label="脚本段落">
            <button class="compact-row is-active" type="button"><span>01</span><strong>开场</strong></button>
            <button class="compact-row" type="button"><span>02</span><strong>展开</strong></button>
            <button class="compact-row" type="button"><span>03</span><strong>收束</strong></button>
            <button class="compact-add" type="button">${icon("add")}</button>
          </aside>
          <article class="writing-surface">
            <div class="writing-surface__meta"><span>开场</span><span>原型段落</span></div>
            <textarea aria-label="脚本正文">先用一个清晰镜头建立主题，再进入主要内容。</textarea>
          </article>
          <aside class="version-rail" aria-label="脚本版本">
            <button class="is-active" type="button">v1</button>
            <button type="button">+</button>
          </aside>
        </div>
      </section>`;
  };

  namespace.renderers.storyboard = function renderStoryboard() {
    return `
      <section class="page-canvas storyboard-canvas">
        <header class="object-bar">
          <div class="object-bar__identity">${icon("view_timeline")}<strong>分镜</strong><span class="muted-label">3 个镜头</span></div>
          <div class="object-bar__actions">${actionButton("同步到剪辑", "open-workspace", "sync_alt", "primary")}</div>
        </header>
        <div class="storyboard-flow">
          <button class="shot-card is-active" type="button" data-action="select-shot" data-id="shot-a">
            <span class="shot-card__number">01</span><span class="shot-card__frame">${icon("image")}</span><strong>建立主题</strong>
          </button>
          <button class="shot-card" type="button" data-action="select-shot" data-id="shot-b">
            <span class="shot-card__number">02</span><span class="shot-card__frame">${icon("image")}</span><strong>展示细节</strong>
          </button>
          <button class="shot-card" type="button" data-action="select-shot" data-id="shot-c">
            <span class="shot-card__number">03</span><span class="shot-card__frame">${icon("image")}</span><strong>收束行动</strong>
          </button>
          <button class="shot-card shot-card--add" type="button">${icon("add")}</button>
        </div>
        <div class="storyboard-timeline"><span style="--start:4%;--width:27%"></span><span style="--start:34%;--width:29%"></span><span style="--start:66%;--width:27%"></span></div>
      </section>`;
  };
})(window);
