(function registerMediaRenderers(global) {
  "use strict";

  const namespace = global.TkPrototype = global.TkPrototype || {};
  namespace.renderers = namespace.renderers || {};

  function icon(name) {
    return `<span class="icon" aria-hidden="true">${name}</span>`;
  }

  function button(label, action, iconName, variant = "secondary") {
    return `<button class="button button--${variant}" type="button" data-action="${action}">${icon(iconName)}<span>${label}</span></button>`;
  }

  function renderTaskStrip(state) {
    if (state.error) {
      return `<div class="signal-strip signal-strip--danger"><span>${icon("error")}预览同步失败</span><button type="button" data-action="recover-error">修复</button></div>`;
    }
    if (state.taskStatus === "idle") return "";
    const labels = { queued: "任务排队中", running: "AI 粗剪运行中", completed: "建议已生成" };
    return `<div class="signal-strip signal-strip--task" data-status="${state.taskStatus}"><span>${icon(state.taskStatus === "completed" ? "check_circle" : "auto_awesome")}${labels[state.taskStatus]}</span>${state.taskStatus === "running" ? '<button type="button" data-action="cancel-task">取消</button>' : ""}</div>`;
  }

  function renderAssetRail(state) {
    const assets = namespace.prototypeMedia.assets.map((asset) => `
      <button class="asset-tile ${state.selectedAssetId === asset.id ? "is-selected" : ""}" type="button" data-action="select-asset" data-id="${asset.id}" title="${asset.label}">
        <span class="asset-tile__preview asset-tile__preview--${asset.tone}">${icon(asset.icon)}</span>
        <span>${asset.label}</span>
      </button>`).join("");
    return `
      <aside class="asset-rail" aria-label="素材">
        <div class="panel-tools"><span>${icon("inventory_2")}</span><button class="icon-button icon-button--small" type="button" title="导入素材">${icon("add")}</button></div>
        <div class="asset-grid">${assets}</div>
      </aside>`;
  }

  function renderPreview(state) {
    const playIcon = state.playback === "playing" ? "pause" : "play_arrow";
    const playLabel = state.playback === "playing" ? "暂停" : "播放";
    return `
      <section class="preview-stage" aria-label="预览舞台">
        <div class="preview-badges"><span>9:16</span><span class="status-badge">原型</span></div>
        <div class="video-frame">
          <div class="video-frame__focus"></div>
          <div class="video-frame__caption">创作预览</div>
        </div>
        <div class="transport">
          <button class="icon-button" type="button" data-action="toggle-playback" aria-label="${playLabel}">${icon(playIcon)}</button>
          <time>${namespace.ui.formatTime(state.currentSecond)}</time>
          <div class="transport__track"><span style="--progress:${Math.min(100, state.currentSecond / 45 * 100)}%"></span></div>
          <button class="icon-button" type="button" title="全屏预览">${icon("fullscreen")}</button>
        </div>
      </section>`;
  }

  function renderTimeline(state) {
    const grouped = ["画面", "配音", "字幕"].map((track) => {
      const clips = namespace.prototypeMedia.clips.filter((clip) => clip.track === track).map((clip) => `
        <button class="timeline-clip timeline-clip--${clip.tone} ${state.selectedClipId === clip.id ? "is-selected" : ""}" type="button" data-action="select-clip" data-id="${clip.id}" style="--clip-left:${clip.left}%;--clip-width:${clip.width}%"><span>${clip.label}</span></button>`).join("");
      const trackIcon = track === "画面" ? "videocam" : track === "配音" ? "mic" : "subtitles";
      return `<div class="timeline-row"><div class="timeline-row__label">${icon(trackIcon)}<span>${track}</span></div><div class="timeline-row__lane">${clips}</div></div>`;
    }).join("");

    return `
      <section class="timeline-panel" aria-label="时间线">
        <div class="timeline-tools">
          <div class="tool-group">
            <button class="icon-button icon-button--small is-active" type="button" title="选择">${icon("near_me")}</button>
            <button class="icon-button icon-button--small" type="button" title="撤销">${icon("undo")}</button>
            <button class="icon-button icon-button--small" type="button" title="分割">${icon("content_cut")}</button>
            <button class="icon-button icon-button--small" type="button" title="删除">${icon("delete")}</button>
          </div>
          <div class="tool-group"><button class="icon-button icon-button--small is-active" type="button" title="磁吸">${icon("vertical_align_center")}</button><span class="zoom-label">100%</span></div>
        </div>
        <div class="timeline-ruler"><span></span><i>00:00</i><i>00:15</i><i>00:30</i><i>00:45</i></div>
        <div class="timeline-tracks"><div class="playhead" style="--playhead:${Math.min(96, state.currentSecond / 45 * 100)}%"></div>${grouped}</div>
      </section>`;
  }

  namespace.renderers.workspace = function renderWorkspace(state) {
    const selected = namespace.prototypeMedia.clips.find((clip) => clip.id === state.selectedClipId);
    return `
      <section class="page-canvas workspace-canvas">
        <header class="object-bar">
          <div class="object-bar__identity">${icon("movie_edit")}<strong>${selected?.label || "时间线"}</strong><span class="save-dot" title="已保存"></span></div>
          <div class="object-bar__actions">
            ${button("智能粗剪", "run-task", "auto_awesome", "ai")}
            ${button("保存", "save", "save", "secondary")}
            <button class="icon-button" type="button" data-action="toggle-command-menu" aria-label="更多操作">${icon("more_horiz")}</button>
          </div>
        </header>
        ${renderTaskStrip(state)}
        <div class="workspace-grid">${renderAssetRail(state)}${renderPreview(state)}${renderTimeline(state)}</div>
      </section>`;
  };

  namespace.renderers.deconstruction = function renderDeconstruction(state) {
    return `
      <section class="page-canvas media-process-canvas">
        <header class="object-bar"><div class="object-bar__identity">${icon("content_cut")}<strong>视频拆解</strong></div>${button("导入视频", "import-video", "add", "primary")}</header>
        ${renderTaskStrip(state)}
        <div class="drop-stage" data-action="import-video">
          <div class="drop-stage__visual">${icon("movie")}</div>
          <strong>拖入本地视频</strong>
          <span>或点击选择</span>
        </div>
        <div class="process-rail" aria-label="拆解阶段"><span class="is-ready">导入</span><i></i><span>画面</span><i></i><span>转写</span><i></i><span>结构</span></div>
      </section>`;
  };

  namespace.renderers.voice = function renderVoice(state) {
    return `
      <section class="page-canvas media-editor-canvas">
        <header class="object-bar"><div class="object-bar__identity">${icon("mic")}<strong>配音</strong></div><div class="object-bar__actions">${button("生成", "run-task", "auto_awesome", "ai")}${button("保存", "save", "save")}</div></header>
        ${renderTaskStrip(state)}
        <div class="voice-layout">
          <aside class="voice-profiles"><button class="voice-profile is-active" type="button"><span>${icon("record_voice_over")}</span><strong>标准音色</strong></button><button class="voice-profile" type="button"><span>${icon("add")}</span><strong>添加</strong></button></aside>
          <div class="voice-stage"><div class="waveform" aria-label="音频波形">${Array.from({ length: 44 }, (_, index) => `<i style="--wave:${28 + (index * 17 % 64)}%"></i>`).join("")}</div><div class="transport transport--standalone"><button class="icon-button" type="button" data-action="toggle-playback">${icon(state.playback === "playing" ? "pause" : "play_arrow")}</button><time>${namespace.ui.formatTime(state.currentSecond)}</time></div></div>
          <aside class="parameter-rail"><label>语速<input type="range" min="70" max="130" value="100"></label><label>音量<input type="range" min="0" max="100" value="78"></label></aside>
        </div>
      </section>`;
  };

  namespace.renderers.subtitles = function renderSubtitles(state) {
    return `
      <section class="page-canvas media-editor-canvas">
        <header class="object-bar"><div class="object-bar__identity">${icon("subtitles")}<strong>字幕对齐</strong></div><div class="object-bar__actions">${button("自动对齐", "run-task", "auto_awesome", "ai")}${button("保存", "save", "save")}</div></header>
        ${renderTaskStrip(state)}
        <div class="subtitle-layout">
          <div class="subtitle-preview"><div class="mini-video"><span>字幕预览</span></div><div class="transport transport--standalone"><button class="icon-button" type="button" data-action="toggle-playback">${icon(state.playback === "playing" ? "pause" : "play_arrow")}</button><time>${namespace.ui.formatTime(state.currentSecond)}</time></div></div>
          <div class="subtitle-list"><button class="subtitle-row is-active" type="button"><time>00:00</time><span>建立主题</span></button><button class="subtitle-row" type="button"><time>00:05</time><span>展示主要内容</span></button><button class="subtitle-row" type="button"><time>00:12</time><span>进入下一段</span></button></div>
        </div>
      </section>`;
  };

  namespace.renderers.assets = function renderAssets(state) {
    const tiles = namespace.prototypeMedia.assets.map((asset) => `<button class="library-tile ${state.selectedAssetId === asset.id ? "is-selected" : ""}" type="button" data-action="select-asset" data-id="${asset.id}"><span class="library-tile__visual">${icon(asset.icon)}</span><strong>${asset.label}</strong><small>${asset.type === "audio" ? "音频" : "视频"}</small></button>`).join("");
    return `<section class="page-canvas asset-canvas"><header class="object-bar"><div class="object-bar__identity">${icon("inventory_2")}<strong>资产</strong></div><div class="object-bar__actions"><button class="search-field" type="button">${icon("search")}<span>搜索</span></button>${button("导入", "import-video", "add", "primary")}</div></header><div class="asset-library">${tiles}<button class="library-tile library-tile--add" type="button" data-action="import-video">${icon("add")}<span>导入</span></button></div></section>`;
  };
})(window);
