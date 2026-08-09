(function startPrototype(global) {
  "use strict";

  const namespace = global.TkPrototype;

  try {
    namespace.state.subscribe((state) => namespace.render(state));
    namespace.interactions.start();
    namespace.render(namespace.state.get());
    namespace.logger.info("app.ready", { routeId: namespace.state.get().routeId });
  } catch (error) {
    namespace.logger?.error("app.start_failed", error);
    const pageHost = document.getElementById("page-host");
    if (pageHost) pageHost.textContent = "原型启动失败，请查看控制台日志。";
  }
})(window);
