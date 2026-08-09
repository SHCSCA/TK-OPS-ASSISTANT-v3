import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import { accountContextApplication } from "./app/account-context";
import { createAppRouter } from "./app/router";
import {
  installDesktopRuntimeConnectionProvider,
  onDesktopRuntimeConnectionRecovered,
  startDesktopRuntimeSupervisorMonitoring
} from "./app/runtime-client/connection";
import { useP0BootstrapStore } from "./modules/system/bootstrap-store";
import "./styles/index.css";

document.documentElement.dataset.theme ||= "light";
installDesktopRuntimeConnectionProvider();

const app = createApp(App);
const pinia = createPinia();
const router = createAppRouter(pinia);
accountContextApplication.configureRouter(router);
const bootstrapStore = useP0BootstrapStore(pinia);
onDesktopRuntimeConnectionRecovered(async () => {
  await bootstrapStore.load();
  if (bootstrapStore.phase === "ready") {
    await accountContextApplication.context.refreshCurrentAccount();
  }
});

app.use(pinia);
app.use(router);

function mountDesktopApp(): void {
  app.mount("#app");
  void router.isReady().catch((error) => {
    console.error("[desktop-bootstrap] 等待首个路由就绪失败", error);
  });
}

void startDesktopRuntimeSupervisorMonitoring()
  .catch((error) => {
    console.error("[desktop-bootstrap] 订阅 Runtime Supervisor 状态失败", error);
  })
  .finally(mountDesktopApp);
