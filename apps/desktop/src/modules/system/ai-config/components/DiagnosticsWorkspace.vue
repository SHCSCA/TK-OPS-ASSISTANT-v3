<template>
  <section class="ai-workspace" aria-labelledby="diagnostics-heading">
    <header class="ai-workspace-header">
      <div>
        <span class="ai-eyebrow">脱敏证据</span>
        <h2 id="diagnostics-heading">日志与诊断</h2>
        <p>只返回安全摘要与修复动作，不读取完整日志文件。</p>
      </div>
      <button class="ai-button is-quiet" type="button" @click="store.loadDiagnostics">
        重新诊断
      </button>
    </header>

    <AIConfigStatePanel
      v-if="store.diagnosticsState !== 'ready'"
      :error-message="store.error?.message"
      :log-id="store.error?.logId"
      :state="store.diagnosticsState"
      @open-log="lookup"
      @retry="store.loadDiagnostics"
    />

    <template v-else>
      <div class="ai-diagnostics-grid">
        <section
          v-for="[key, value] in diagnosticEntries"
          :key="key"
          class="ai-runtime-card"
        >
          <header>
            <span class="material-symbols-outlined">{{ diagnosticIcon(key) }}</span>
            <div><h3>{{ diagnosticLabel(key) }}</h3><p>真实 Runtime 摘要</p></div>
          </header>
          <pre>{{ JSON.stringify(value, null, 2) }}</pre>
        </section>
      </div>

      <section class="ai-log-lookup">
        <header>
          <div>
            <span class="ai-eyebrow">关联日志</span>
            <h3>安全日志摘要</h3>
          </div>
        </header>
        <div v-if="store.error" class="ai-inline-feedback is-error">
          <span class="material-symbols-outlined">error</span>
          <span>{{ store.error.message }}</span>
          <button
            v-if="store.error.logId"
            class="ai-button is-quiet"
            type="button"
            @click="lookup(store.error.logId)"
          >
            查看关联日志
          </button>
        </div>
        <form @submit.prevent="store.lookupLog()">
          <label class="ai-search">
            <span class="material-symbols-outlined">receipt_long</span>
            <input
              v-model="store.logIdInput"
              maxlength="128"
              placeholder="输入 log_id"
            />
          </label>
          <button class="ai-button is-primary" type="submit">检索</button>
          <button
            v-if="store.logExcerpt"
            class="ai-button is-quiet"
            type="button"
            @click="store.clearLog"
          >
            清除
          </button>
        </form>
        <article v-if="store.logExcerpt" class="ai-log-excerpt">
          <header>
            <span class="ai-status-chip" :class="`is-${store.logExcerpt.severity}`">
              {{ store.logExcerpt.severity }}
            </span>
            <strong>{{ store.logExcerpt.summary }}</strong>
          </header>
          <dl class="ai-detail-list">
            <div><dt>日志 ID</dt><dd>{{ store.logExcerpt.logId }}</dd></div>
            <div><dt>错误码</dt><dd>{{ store.logExcerpt.errorCode ?? "无" }}</dd></div>
            <div><dt>阶段</dt><dd>{{ store.logExcerpt.stage ?? "未标记" }}</dd></div>
            <div><dt>发生时间</dt><dd>{{ store.logExcerpt.occurredAt }}</dd></div>
          </dl>
          <ul v-if="store.logExcerpt.suggestedActions.length" class="ai-issue-list">
            <li v-for="action in store.logExcerpt.suggestedActions" :key="action">
              <span>{{ action }}</span>
            </li>
          </ul>
        </article>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";

import { useSystemDiagnosticsStore } from "../system-diagnostics-store";
import AIConfigStatePanel from "./AIConfigStatePanel.vue";

const store = useSystemDiagnosticsStore();
const diagnosticEntries = computed(
  () => Object.entries(store.diagnostics ?? {}).filter(([key]) => key !== "checkedAt")
);

onMounted(() => {
  if (store.diagnosticsState === "idle") void store.loadDiagnostics();
});

function lookup(logId: string): void {
  void store.lookupLog(logId);
}

function diagnosticLabel(key: string): string {
  return {
    runtime: "Runtime",
    database: "数据库",
    directories: "目录",
    mediaTools: "媒体工具",
    sidecar: "Sidecar"
  }[key] ?? key;
}

function diagnosticIcon(key: string): string {
  return {
    runtime: "dns",
    database: "database",
    directories: "folder_open",
    mediaTools: "construction",
    sidecar: "memory"
  }[key] ?? "info";
}
</script>
