(function registerState(global) {
  "use strict";

  const namespace = global.TkPrototype = global.TkPrototype || {};
  const listeners = new Set();
  const config = namespace.config;

  function readStoredPreferences() {
    try {
      const raw = global.localStorage.getItem(config.storageKey);
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (error) {
      namespace.logger?.warning("state.read_preferences_failed", error);
      return {};
    }
  }

  const stored = readStoredPreferences();
  let state = createInitialState(stored);

  function createInitialState(preferences = {}) {
    return {
      routeId: config.defaultRouteId,
      theme: preferences.theme === "light" ? "light" : config.defaultTheme,
      sidebarCollapsed: preferences.sidebarCollapsed !== false,
      detailOpen: false,
      detailMode: "inspector",
      selectedAssetId: null,
      selectedClipId: "clip-a",
      playback: "paused",
      currentSecond: 12,
      taskStatus: "idle",
      error: null,
      commandMenuOpen: false,
      settingsSection: "providers"
    };
  }

  function persistPreferences(nextState) {
    try {
      global.localStorage.setItem(config.storageKey, JSON.stringify({
        theme: nextState.theme,
        sidebarCollapsed: nextState.sidebarCollapsed
      }));
    } catch (error) {
      namespace.logger?.warning("state.persist_preferences_failed", error);
    }
  }

  function notify(meta) {
    listeners.forEach((listener) => {
      try {
        listener(state, meta);
      } catch (error) {
        namespace.logger?.error("state.listener_failed", error);
      }
    });
  }

  namespace.state = Object.freeze({
    get() {
      return state;
    },
    set(patch, meta = { source: "unknown" }) {
      state = { ...state, ...patch };
      persistPreferences(state);
      namespace.logger?.info("state.changed", { source: meta.source, keys: Object.keys(patch) });
      notify(meta);
    },
    reset() {
      state = createInitialState({ theme: state.theme, sidebarCollapsed: true });
      persistPreferences(state);
      notify({ source: "reset" });
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    }
  });
})(window);
