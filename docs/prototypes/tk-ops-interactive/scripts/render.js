(function registerRenderer(global) {
  "use strict";

  const namespace = global.TkPrototype = global.TkPrototype || {};
  const app = document.getElementById("app");
  const sidebar = document.getElementById("sidebar");
  const pageHost = document.getElementById("page-host");
  const detailHost = document.getElementById("detail-host");
  const globalStatus = document.getElementById("global-status");
  const commandMenu = document.getElementById("command-menu");
  const titlePage = document.getElementById("title-page");
  const toastRegion = document.getElementById("toast-region");

  function icon(name) {
    return `<span class="icon" aria-hidden="true">${name}</span>`;
  }

  function formatTime(seconds) {
    const safeSeconds = Math.max(0, Math.round(Number(seconds) || 0));
    const minutes = Math.floor(safeSeconds / 60);
    const remainder = safeSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
  }

  namespace.ui = Object.freeze({ icon, formatTime });

  namespace.toast = Object.freeze({
    show(message, tone = "info") {
      if (!toastRegion) return;
      const toast = document.createElement("div");
      toast.className = `toast toast--${tone}`;
      toast.textContent = message;
      toastRegion.appendChild(toast);
      global.setTimeout(() => toast.remove(), 2400);
    }
  });

  function renderSidebar(state) {
    sidebar.innerHTML = namespace.navGroups.map((group) => `
      <section class="sidebar-group">
        <p>${group.label}</p>
        ${group.pages.map((page) => `
          <button class="nav-item ${state.routeId === page.id ? "is-active" : ""}" type="button" data-nav-id="${page.id}" data-label="${page.title}" aria-label="${page.title}" title="${page.title}">
            ${icon(page.icon)}<span>${page.title}</span>
          </button>`).join("")}
      </section>`).join("");
  }

  function resolveSelectedObject(state) {
    const asset = namespace.prototypeMedia.assets.find((item) => item.id === state.selectedAssetId);
    if (asset) return { kind: "素材", label: asset.label, icon: asset.icon };
    const clip = namespace.prototypeMedia.clips.find((item) => item.id === state.selectedClipId);
    if (clip) return { kind: clip.track, label: clip.label, icon: clip.track === "画面" ? "videocam" : clip.track === "配音" ? "mic" : "subtitles" };
    return null;
  }

  function renderDetail(state) {
    if (!state.detailOpen) {
      detailHost.innerHTML = `
        <div class="detail-rail">
          <button class="detail-rail__item ${state.detailMode === "inspector" ? "is-active" : ""}" type="button" data-action="open-detail" data-mode="inspector" aria-label="检查器" title="检查器">${icon("tune")}</button>
          <button class="detail-rail__item ${state.detailMode === "ai" ? "is-active" : ""}" type="button" data-action="open-detail" data-mode="ai" aria-label="AI 建议" title="AI 建议">${icon("auto_awesome")}</button>
          <button class="detail-rail__item ${state.detailMode === "logs" ? "is-active" : ""}" type="button" data-action="open-detail" data-mode="logs" aria-label="日志" title="日志">${icon("receipt_long")}</button>
        </div>`;
      return;
    }

    detailHost.innerHTML = `<div class="detail-panel">${renderDetailContent(state)}</div>`;
  }

  function renderDetailContent(state) {
    const selected = resolveSelectedObject(state);
    const header = (title, iconName) => `<header class="detail-panel__header"><span>${icon(iconName)}<strong>${title}</strong></span><button class="icon-button icon-button--small" type="button" data-action="close-detail" aria-label="关闭详情">${icon("close")}</button></header>`;

    if (state.error) {
      return `${header("需要处理", "error")}<div class="detail-panel__body"><div class="detail-alert"><strong>预览同步失败</strong><span>工作区可继续编辑。</span></div><details><summary>技术详情</summary><code>preview.sync_failed · 原型事件</code></details><button class="button button--primary" type="button" data-action="recover-error">${icon("refresh")}<span>重试同步</span></button></div>`;
    }

    if (state.detailMode === "ai") {
      return `${header("AI 建议", "auto_awesome")}<div class="detail-panel__body"><div class="quiet-empty quiet-empty--small"><span>${icon("auto_awesome")}</span><strong>${state.taskStatus === "completed" ? "建议已生成" : "暂无建议"}</strong>${state.taskStatus === "completed" ? '<button class="button button--primary" type="button" data-action="apply-suggestion"><span class="icon">check</span><span>应用</span></button>' : '<button class="button button--ai" type="button" data-action="run-task"><span class="icon">play_arrow</span><span>生成</span></button>'}</div></div>`;
    }

    if (state.detailMode === "logs") {
      return `${header("操作日志", "receipt_long")}<div class="detail-panel__body"><ol class="compact-log"><li><time>刚刚</time><span>原型已就绪</span></li>${state.taskStatus !== "idle" ? `<li><time>任务</time><span>${state.taskStatus}</span></li>` : ""}</ol></div>`;
    }

    if (!selected) {
      return `${header("检查器", "tune")}<div class="detail-panel__body"><div class="quiet-empty quiet-empty--small"><span>${icon("touch_app")}</span><strong>选择一个对象</strong></div></div>`;
    }

    return `${header(selected.label, selected.icon)}<div class="detail-panel__body"><dl class="property-list"><div><dt>类型</dt><dd>${selected.kind}</dd></div><div><dt>状态</dt><dd><span class="status-dot status-dot--runtime"></span>可编辑</dd></div></dl><details><summary>高级属性</summary><dl class="property-list"><div><dt>来源</dt><dd>原型对象</dd></div><div><dt>引用</dt><dd>当前时间线</dd></div></dl></details></div>`;
  }

  function renderStatus(state, page) {
    const activeSignal = state.error
      ? `<span class="global-status__signal global-status__signal--danger">${icon("error")}预览失败</span>`
      : state.taskStatus === "running" || state.taskStatus === "queued"
        ? `<span class="global-status__signal global-status__signal--task">${icon("progress_activity")}任务${state.taskStatus === "queued" ? "排队" : "运行中"}</span>`
        : "";
    globalStatus.innerHTML = `<div><span class="status-dot ${state.error ? "status-dot--error" : "status-dot--runtime"}" title="${state.error ? "Runtime 事件异常" : "Runtime 已连接"}"></span>${activeSignal}</div><div><span title="已保存">${icon("cloud_done")}</span><span title="当前页面">${icon(page.icon)}</span><button type="button" data-action="open-detail" data-mode="logs" aria-label="打开日志">${icon("receipt_long")}</button></div>`;
  }

  function renderPage(state, page) {
    const renderer = namespace.renderers[page.family];
    if (typeof renderer !== "function") {
      throw new Error(`缺少页面渲染器：${page.family}`);
    }
    pageHost.innerHTML = renderer(state, page);
  }

  function render(state) {
    try {
      const page = namespace.pages[state.routeId] || namespace.pages[namespace.config.defaultRouteId];
      document.documentElement.dataset.theme = state.theme;
      app.dataset.sidebarCollapsed = String(state.sidebarCollapsed);
      app.dataset.detailOpen = String(state.detailOpen);
      app.dataset.routeType = page.family === "setup" ? "wizard" : "workspace";
      titlePage.textContent = page.title;
      commandMenu.hidden = !state.commandMenuOpen;
      renderSidebar(state);
      renderPage(state, page);
      renderDetail(state);
      renderStatus(state, page);
    } catch (error) {
      namespace.logger.error("render.failed", error);
      pageHost.innerHTML = `<div class="fatal-state"><span class="icon">error</span><strong>原型渲染失败</strong><button class="button button--primary" type="button" data-action="clear-prototype">重置</button></div>`;
    }
  }

  namespace.render = render;
})(window);
