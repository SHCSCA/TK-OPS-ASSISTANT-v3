import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import { createAppRouter } from "./app/router";
import "./styles/index.css";

document.documentElement.dataset.theme ||= "light";

const app = createApp(App);
const pinia = createPinia();
const router = createAppRouter();

app.use(pinia);
app.use(router);
app.mount("#app");
