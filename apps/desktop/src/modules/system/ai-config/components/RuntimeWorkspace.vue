<template>
  <section class="ai-workspace" aria-labelledby="runtime-heading">
    <header class="ai-workspace-header">
      <div>
        <span class="ai-eyebrow">统一配置总线</span>
        <h2 id="runtime-heading">Runtime 与工作区</h2>
        <p>只展示 Runtime 返回的系统配置、目录和 sidecar 证据。</p>
      </div>
      <button class="ai-button is-quiet" type="button" @click="store.loadRuntime">
        刷新
      </button>
    </header>

    <AIConfigStatePanel
      v-if="store.runtimeState !== 'ready'"
      :error-message="store.error?.message"
      :log-id="store.error?.logId"
      :state="store.runtimeState"
      @open-log="$emit('openLog', $event)"
      @retry="store.loadRuntime"
    />

    <div v-else class="ai-runtime-grid">
      <section class="ai-runtime-card">
        <header>
          <span class="material-symbols-outlined">dns</span>
          <div><h3>Runtime</h3><p>{{ checkedAt }}</p></div>
        </header>
        <pre>{{ formatValue(store.diagnostics?.runtime) }}</pre>
      </section>
      <section class="ai-runtime-card">
        <header>
          <span class="material-symbols-outlined">folder_open</span>
          <div><h3>工作区目录</h3><p>路径由配置总线解析</p></div>
        </header>
        <pre>{{ formatValue(store.diagnostics?.directories) }}</pre>
      </section>
      <section class="ai-runtime-card">
        <header>
          <span class="material-symbols-outlined">memory</span>
          <div><h3>Sidecar</h3><p>本机执行进程</p></div>
        </header>
        <pre>{{ formatValue(store.diagnostics?.sidecar) }}</pre>
      </section>
      <section class="ai-runtime-card is-wide">
        <header>
          <span class="material-symbols-outlined">tune</span>
          <div>
            <h3>公开配置</h3>
            <p>修订 {{ store.config?.revision ?? "—" }}</p>
          </div>
        </header>
        <dl class="ai-config-values">
          <div v-for="[key, value] in configEntries" :key="key">
            <dt>{{ key }}</dt>
            <dd>{{ formatValue(value) }}</dd>
          </div>
        </dl>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";

import { useSystemDiagnosticsStore } from "../system-diagnostics-store";
import AIConfigStatePanel from "./AIConfigStatePanel.vue";

defineEmits<{ openLog: [logId: string] }>();

const store = useSystemDiagnosticsStore();
const configEntries = computed(() => Object.entries(store.config?.values ?? {}));
const checkedAt = computed(
  () => store.diagnostics?.checkedAt
    ? `检查时间 ${store.diagnostics.checkedAt}`
    : "尚无检查时间"
);

onMounted(() => {
  if (store.runtimeState === "idle") void store.loadRuntime();
});

function formatValue(value: unknown): string {
  if (value === undefined || value === null) return "暂无";
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}
</script>
