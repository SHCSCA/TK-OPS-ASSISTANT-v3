(function registerInteractions(global) {
  "use strict";

  const namespace = global.TkPrototype = global.TkPrototype || {};
  let playbackTimer = null;
  let taskToken = 0;

  function setState(patch, source) {
    namespace.state.set(patch, { source });
  }

  function navigate(routeId) {
    if (!namespace.pages[routeId]) throw new Error(`未知页面：${routeId}`);
    stopPlayback();
    setState({ routeId, detailOpen: false, commandMenuOpen: false, playback: "paused" }, "navigation");
    document.getElementById("page-host")?.focus({ preventScroll: true });
  }

  function startPlayback() {
    stopPlayback();
    setState({ playback: "playing" }, "playback.start");
    playbackTimer = global.setInterval(() => {
      const state = namespace.state.get();
      const nextSecond = state.currentSecond >= 45 ? 0 : state.currentSecond + 1;
      namespace.state.set({ currentSecond: nextSecond }, { source: "playback.tick" });
    }, 1000);
  }

  function stopPlayback() {
    if (playbackTimer !== null) {
      global.clearInterval(playbackTimer);
      playbackTimer = null;
    }
    if (namespace.state?.get().playback !== "paused") {
      namespace.state.set({ playback: "paused" }, { source: "playback.stop" });
    }
  }

  function runTask() {
    taskToken += 1;
    const currentToken = taskToken;
    setState({ taskStatus: "queued", error: null, commandMenuOpen: false }, "task.queued");
    namespace.toast.show("任务已进入队列", "info");

    global.setTimeout(() => {
      if (currentToken !== taskToken) return;
      setState({ taskStatus: "running" }, "task.running");
    }, namespace.config.taskDurations.queued);

    global.setTimeout(() => {
      if (currentToken !== taskToken) return;
      setState({ taskStatus: "completed", detailMode: "ai" }, "task.completed");
      namespace.toast.show("AI 建议已生成", "success");
    }, namespace.config.taskDurations.running);
  }

  function cancelTask() {
    taskToken += 1;
    setState({ taskStatus: "idle" }, "task.cancelled");
    namespace.toast.show("任务已取消", "warning");
  }

  function simulateError() {
    taskToken += 1;
    setState({
      error: { code: "preview.sync_failed", message: "预览同步失败" },
      taskStatus: "idle",
      detailOpen: true,
      detailMode: "inspector",
      commandMenuOpen: false
    }, "error.simulated");
  }

  function recoverError() {
    setState({ error: null, detailOpen: false }, "error.recovered");
    namespace.toast.show("同步已恢复", "success");
  }

  function handleAction(action, target) {
    const state = namespace.state.get();
    switch (action) {
      case "toggle-sidebar":
        setState({ sidebarCollapsed: !state.sidebarCollapsed }, "shell.sidebar");
        return;
      case "toggle-theme":
        setState({ theme: state.theme === "dark" ? "light" : "dark" }, "shell.theme");
        return;
      case "toggle-command-menu":
        setState({ commandMenuOpen: !state.commandMenuOpen }, "shell.command_menu");
        return;
      case "open-detail":
        setState({ detailOpen: true, detailMode: target.dataset.mode || "inspector" }, "detail.open");
        return;
      case "close-detail":
        setState({ detailOpen: false }, "detail.close");
        return;
      case "open-ai":
        setState({ detailOpen: true, detailMode: "ai" }, "detail.ai");
        return;
      case "open-runtime":
        setState({ detailOpen: true, detailMode: "logs" }, "detail.runtime");
        return;
      case "select-asset":
        setState({ selectedAssetId: target.dataset.id, selectedClipId: null, detailOpen: true, detailMode: "inspector" }, "selection.asset");
        return;
      case "select-clip":
        setState({ selectedClipId: target.dataset.id, selectedAssetId: null, detailOpen: true, detailMode: "inspector" }, "selection.clip");
        return;
      case "toggle-playback":
        state.playback === "playing" ? stopPlayback() : startPlayback();
        return;
      case "run-task":
        runTask();
        return;
      case "cancel-task":
        cancelTask();
        return;
      case "simulate-error":
        simulateError();
        return;
      case "recover-error":
        recoverError();
        return;
      case "save":
        namespace.toast.show("原型状态已保存", "success");
        setState({ commandMenuOpen: false }, "save");
        return;
      case "clear-prototype":
        taskToken += 1;
        stopPlayback();
        namespace.state.reset();
        namespace.toast.show("原型已重置", "info");
        return;
      case "open-workspace":
        navigate("ai_editing_workspace");
        return;
      case "open-dashboard":
        navigate("creator_dashboard");
        return;
      case "setup-continue":
        namespace.toast.show("许可证链路仅作交互演示", "info");
        navigate("creator_dashboard");
        return;
      case "settings-section":
        setState({ settingsSection: target.dataset.id }, "settings.section");
        return;
      case "apply-suggestion":
        setState({ taskStatus: "idle", detailOpen: false }, "task.applied");
        namespace.toast.show("建议已应用到原型时间线", "success");
        return;
      case "new-project":
      case "import-video":
      case "create-binding":
      case "create-workspace":
      case "choose-path":
      case "diagnostics":
      case "setup-diagnostics":
      case "select-shot":
      case "open-task":
        namespace.toast.show("这是本地交互原型，不创建真实对象。", "info");
        setState({ commandMenuOpen: false }, `prototype.${action}`);
        return;
      default:
        namespace.logger.warning("interaction.unknown_action", action);
    }
  }

  function handleDocumentClick(event) {
    const navTarget = event.target.closest("[data-nav-id]");
    if (navTarget) {
      try {
        navigate(navTarget.dataset.navId);
      } catch (error) {
        namespace.logger.error("navigation.failed", error);
      }
      return;
    }

    const actionTarget = event.target.closest("[data-action]");
    if (!actionTarget) {
      if (namespace.state.get().commandMenuOpen && !event.target.closest("#command-menu")) {
        setState({ commandMenuOpen: false }, "shell.command_menu_dismiss");
      }
      return;
    }

    try {
      handleAction(actionTarget.dataset.action, actionTarget);
    } catch (error) {
      namespace.logger.error("interaction.failed", error);
    }
  }

  function handleKeyboard(event) {
    const isTyping = event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement;
    if (isTyping) return;

    if (event.key === "Escape") {
      setState({ detailOpen: false, commandMenuOpen: false }, "keyboard.escape");
      return;
    }
    if (event.key === " " && namespace.state.get().routeId === "ai_editing_workspace") {
      event.preventDefault();
      namespace.state.get().playback === "playing" ? stopPlayback() : startPlayback();
      return;
    }
    if (event.key.toLowerCase() === "b") handleAction("toggle-sidebar", document.body);
    if (event.key.toLowerCase() === "d") handleAction(namespace.state.get().detailOpen ? "close-detail" : "open-detail", document.body);
    if (event.key.toLowerCase() === "t") handleAction("toggle-theme", document.body);
  }

  namespace.interactions = Object.freeze({
    start() {
      document.addEventListener("click", handleDocumentClick);
      document.addEventListener("keydown", handleKeyboard);
      namespace.logger.info("interactions.started");
    },
    stopPlayback
  });
})(window);
