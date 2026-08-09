(function registerLogger(global) {
  "use strict";

  const namespace = global.TkPrototype = global.TkPrototype || {};

  function serializeDetail(detail) {
    if (detail === undefined) return "";
    if (detail instanceof Error) return detail.message;
    try {
      return typeof detail === "string" ? detail : JSON.stringify(detail);
    } catch (error) {
      return String(detail);
    }
  }

  function log(level, event, detail) {
    const timestamp = new Date().toISOString();
    const suffix = serializeDetail(detail);
    const message = `[TK-OPS-PROTOTYPE][${timestamp}][${level.toUpperCase()}][${event}]${suffix ? ` ${suffix}` : ""}`;
    const method = level === "error" ? "error" : level === "warning" ? "warn" : "info";
    console[method](message);
  }

  namespace.logger = Object.freeze({
    info(event, detail) {
      log("info", event, detail);
    },
    warning(event, detail) {
      log("warning", event, detail);
    },
    error(event, error) {
      log("error", event, error);
      namespace.toast?.show("原型操作失败，请重试。", "danger");
    }
  });

  global.addEventListener("error", (event) => {
    namespace.logger.error("window.error", event.error || event.message);
  });

  global.addEventListener("unhandledrejection", (event) => {
    namespace.logger.error("window.unhandledrejection", event.reason);
  });
})(window);
