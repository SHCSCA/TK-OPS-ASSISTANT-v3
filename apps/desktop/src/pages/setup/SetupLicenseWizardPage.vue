<template>
  <section class="setup-page" :data-setup-state="setupState">
    <header class="setup-hero" data-setup-section="hero">
      <div class="setup-hero__copy">
        <p class="setup-hero__eyebrow">首启与许可证向导</p>
        <h1>先完成授权，再校验 Runtime 和初始化配置</h1>
        <p class="setup-hero__summary">
          这里展示的每一项状态都来自真实 Runtime、许可证和初始化配置。授权未完成时不进入主工作流，初始化未完成时只保留可继续补齐的入口。
        </p>

        <div class="setup-hero__badges">
          <span class="status-chip" :data-tone="licenseTone">{{ licenseLabel }}</span>
          <span class="status-chip" :data-tone="runtimeTone">{{ runtimeLabel }}</span>
          <span class="status-chip" :data-tone="initializationTone">{{ initializationLabel }}</span>
        </div>
      </div>

      <div class="setup-hero__panel">
        <article class="setup-mini-card" data-setup-panel="license">
          <p class="setup-mini-card__label">本机机器码</p>
          <strong>{{ licenseStore.machineCode || "等待 Runtime 返回" }}</strong>
          <p>{{ machineCodeHint }}</p>
          <div class="setup-mini-card__actions">
            <button
              class="setup-button setup-button--secondary"
              type="button"
              data-action="copy-machine-code"
              :disabled="!licenseStore.machineCode"
              @click="handleCopyMachineCode"
            >
              {{ copyButtonLabel }}
            </button>
          </div>
        </article>

        <article class="setup-mini-card" data-setup-panel="runtime">
          <p class="setup-mini-card__label">Runtime 健康</p>
          <strong>{{ runtimeStatusLabel }}</strong>
          <p>{{ runtimeDetail }}</p>
        </article>
      </div>
    </header>

    <p v-if="feedbackMessage" class="setup-alert" :data-tone="feedbackTone">
      {{ feedbackMessage }}
    </p>

    <div class="setup-grid">
      <article class="setup-card" data-setup-section="authorization">
        <div class="setup-card__header">
          <div>
            <p class="detail-panel__label">步骤 1</p>
            <h2>授权</h2>
          </div>
          <span class="status-chip" :data-tone="licenseTone">{{ licenseLabel }}</span>
        </div>

        <p class="setup-card__summary">
          输入授权码后会直接走真实的许可证激活接口，不会伪造成“已完成”。
        </p>

        <label class="setup-field">
          <span>授权码</span>
          <textarea
            v-model="activationCode"
            class="setup-textarea"
            data-field="activationCode"
            :disabled="authorizationDisabled"
            placeholder="请粘贴授权人员提供的授权码"
          />
        </label>

        <div class="setup-card__actions">
          <button
            class="setup-button"
            type="button"
            data-action="activate-license"
            :disabled="authorizationDisabled || activationCode.trim().length === 0"
            @click="handleActivate"
          >
            完成授权
          </button>
          <button
            class="setup-button setup-button--secondary"
            type="button"
            data-action="refresh-bootstrap"
            :disabled="isRefreshing"
            @click="handleRefresh"
          >
            重新检查
          </button>
        </div>
      </article>

      <article class="setup-card" data-setup-section="runtime">
        <div class="setup-card__header">
          <div>
            <p class="detail-panel__label">步骤 2</p>
            <h2>Runtime 健康</h2>
          </div>
          <span class="status-chip" :data-tone="runtimeTone">{{ runtimeLabel }}</span>
        </div>

        <ul class="setup-metric-list">
          <li>
            <span>服务版本</span>
            <strong>{{ configBusStore.health?.version || "等待检查" }}</strong>
          </li>
          <li>
            <span>运行模式</span>
            <strong>{{ configBusStore.settings?.runtime?.mode || configBusStore.health?.mode || "等待检查" }}</strong>
          </li>
          <li>
            <span>健康状态</span>
            <strong>{{ configBusStore.diagnostics?.healthStatus || "等待检查" }}</strong>
          </li>
          <li>
            <span>最后同步</span>
            <strong>{{ configBusStore.lastSyncedAt || "尚未同步" }}</strong>
          </li>
        </ul>

        <p class="setup-card__hint">
          只有 Runtime 在线且返回配置与诊断后，初始化卡片才会进入可继续状态。
        </p>
      </article>

      <article class="setup-card" data-setup-section="initialization">
        <div class="setup-card__header">
          <div>
            <p class="detail-panel__label">步骤 3</p>
            <h2>初始化</h2>
          </div>
          <span class="status-chip" :data-tone="initializationTone">{{ initializationLabel }}</span>
        </div>

        <p class="setup-card__summary">
          这里显示的初始化清单来自 Runtime 当前保存的配置。如果字段不完整，页面会停留在空态而不是伪造通过。
        </p>

        <ul class="setup-checklist">
          <li v-for="item in initializationChecklist" :key="item.id" :data-state="item.state">
            <span class="setup-checklist__label">{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.hint }}</p>
          </li>
        </ul>

        <div class="setup-card__actions">
          <button
            class="setup-button setup-button--secondary"
            type="button"
            data-action="open-settings"
            :disabled="!canOpenSettings"
            @click="goToSettings"
          >
            前往系统设置
          </button>
          <button
            class="setup-button"
            type="button"
            data-action="open-dashboard"
            :disabled="!canOpenDashboard"
            @click="goToDashboard"
          >
            进入总览
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { hasCompletedBootstrapInitialization } from "@/bootstrap/bootstrap-form";
import { useBootstrapStore } from "@/stores/bootstrap";
import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";

type Tone = "neutral" | "brand" | "success" | "warning" | "danger" | "info";

const bootstrapStore = useBootstrapStore();
const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const router = useRouter();
const activationCode = ref("");
const copyButtonLabel = ref("复制机器码");

const setupState = computed(() => {
  if (
    bootstrapStore.phase === "boot_loading" ||
    licenseStore.status === "loading" ||
    licenseStore.status === "submitting" ||
    configBusStore.status === "loading" ||
    configBusStore.runtimeStatus === "loading"
  ) {
    return "loading";
  }

  if (bootstrapStore.phase === "boot_error" || licenseStore.status === "error" || configBusStore.status === "error") {
    return "error";
  }

  if (!licenseStore.active) {
    return "blocked";
  }

  if (!hasCompletedBootstrapInitialization(configBusStore.settings)) {
    return "empty";
  }

  return "ready";
});

const licenseLabel = computed(() => {
  if (licenseStore.status === "loading") return "授权校验中";
  if (licenseStore.status === "submitting") return "授权提交中";
  if (licenseStore.error) return "授权异常";
  if (licenseStore.active) return "已授权";
  return "待授权";
});

const licenseTone = computed<Tone>(() => {
  if (licenseStore.error) return "danger";
  if (licenseStore.active) return "success";
  if (licenseStore.status === "loading" || licenseStore.status === "submitting") return "info";
  return "warning";
});

const runtimeLabel = computed(() => {
  if (configBusStore.runtimeStatus === "online") return "Runtime 在线";
  if (configBusStore.runtimeStatus === "offline") return "Runtime 离线";
  if (configBusStore.runtimeStatus === "loading") return "Runtime 检查中";
  return "Runtime 待检查";
});

const runtimeTone = computed<Tone>(() => {
  if (configBusStore.runtimeStatus === "online") return "success";
  if (configBusStore.runtimeStatus === "offline" || configBusStore.status === "error") return "danger";
  if (configBusStore.runtimeStatus === "loading") return "info";
  return "neutral";
});

const initializationLabel = computed(() => {
  if (setupState.value === "ready") return "已完成";
  if (setupState.value === "empty") return "待补齐";
  if (setupState.value === "blocked") return "待授权";
  if (setupState.value === "error") return "初始化异常";
  return "初始化检查中";
});

const initializationTone = computed<Tone>(() => {
  if (setupState.value === "ready") return "success";
  if (setupState.value === "empty") return "warning";
  if (setupState.value === "blocked") return "warning";
  if (setupState.value === "error") return "danger";
  return "info";
});

const runtimeStatusLabel = computed(() => {
  const version = configBusStore.health?.version;
  const status = configBusStore.runtimeStatus;
  if (status === "online" && version) {
    return `在线 · ${version}`;
  }
  if (status === "offline") return "离线";
  if (status === "loading") return "检查中";
  return "等待检查";
});

const runtimeDetail = computed(() => {
  if (configBusStore.error) {
    return configBusStore.error.requestId
      ? `${configBusStore.error.message}（${configBusStore.error.requestId}）`
      : configBusStore.error.message;
  }

  if (configBusStore.health) {
    return `当前模式 ${configBusStore.health.mode}，最近一次检查 ${configBusStore.health.now}`;
  }

  return "请先读取 Runtime 健康与配置。";
});

const machineCodeHint = computed(() => {
  if (licenseStore.active) {
    return "授权已激活，机器码仍保留用于审计与回溯。";
  }
  if (licenseStore.status === "loading") {
    return "正在向 Runtime 读取机器码。";
  }
  return "把这串机器码发给授权人员，用来生成一机一码授权码。";
});

const feedbackMessage = computed(() => {
  if (licenseStore.error) {
    return licenseStore.error.requestId
      ? `${licenseStore.error.message}（${licenseStore.error.requestId}）`
      : licenseStore.error.message;
  }

  if (configBusStore.error) {
    return configBusStore.error.requestId
      ? `${configBusStore.error.message}（${configBusStore.error.requestId}）`
      : configBusStore.error.message;
  }

  return "";
});

const feedbackTone = computed<Tone>(() => {
  if (licenseStore.error || configBusStore.error) return "danger";
  return "neutral";
});

const authorizationDisabled = computed(
  () =>
    setupState.value === "loading" ||
    setupState.value === "error" ||
    licenseStore.status === "submitting" ||
    licenseStore.active
);
const isRefreshing = computed(() => bootstrapStore.phase === "boot_loading");
const canOpenSettings = computed(
  () =>
    setupState.value === "empty" ||
    setupState.value === "ready" ||
    setupState.value === "blocked"
);
const canOpenDashboard = computed(() => setupState.value === "ready");

const initializationChecklist = computed(() => {
  const settings = configBusStore.settings;
  const ready = hasCompletedBootstrapInitialization(settings);

  return [
    {
      id: "runtime-mode",
      label: "运行模式",
      state: settings?.runtime?.mode ? "ready" : "empty",
      value: settings?.runtime?.mode || "尚未配置",
      hint: "决定 Runtime 的执行方式。"
    },
    {
      id: "workspace-root",
      label: "工作区目录",
      state: settings?.runtime?.workspaceRoot ? "ready" : "empty",
      value: settings?.runtime?.workspaceRoot || "尚未配置",
      hint: "用于承载本地项目和缓存。"
    },
    {
      id: "cache-dir",
      label: "缓存目录",
      state: settings?.paths?.cacheDir ? "ready" : "empty",
      value: settings?.paths?.cacheDir || "尚未配置",
      hint: "保存中间产物和临时数据。"
    },
    {
      id: "export-dir",
      label: "导出目录",
      state: settings?.paths?.exportDir ? "ready" : "empty",
      value: settings?.paths?.exportDir || "尚未配置",
      hint: "保存渲染和导出文件。"
    },
    {
      id: "log-dir",
      label: "日志目录",
      state: settings?.paths?.logDir ? "ready" : "empty",
      value: settings?.paths?.logDir || "尚未配置",
      hint: "用于异常追踪与回溯。"
    },
    {
      id: "ai-model",
      label: "AI 默认模型",
      state: settings?.ai?.model ? "ready" : "empty",
      value: settings?.ai?.model || "尚未配置",
      hint: ready ? "初始化已完成。" : "继续初始化。"
    }
  ];
});

onMounted(() => {
  if (bootstrapStore.phase === "boot_loading") {
    void bootstrapStore.load();
  }
});

async function handleActivate(): Promise<void> {
  if (activationCode.value.trim().length === 0) {
    return;
  }

  await bootstrapStore.activateLicense({
    activationCode: activationCode.value.trim()
  });

  if (licenseStore.active) {
    activationCode.value = "";
  }
}

async function handleRefresh(): Promise<void> {
  await bootstrapStore.retry();
}

async function handleCopyMachineCode(): Promise<void> {
  if (!licenseStore.machineCode) {
    return;
  }

  try {
    await navigator.clipboard.writeText(licenseStore.machineCode);
    copyButtonLabel.value = "已复制";
  } catch {
    copyButtonLabel.value = "复制失败";
  }
}

function goToSettings(): void {
  void router.push("/settings/ai-system");
}

function goToDashboard(): void {
  void router.push("/dashboard");
}
</script>

<style scoped>
.setup-page {
  display: grid;
  gap: var(--space-6);
}

.setup-hero {
  display: grid;
  gap: var(--space-5);
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
  align-items: stretch;
}

.setup-hero__copy,
.setup-hero__panel,
.setup-card,
.setup-mini-card {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
}

.setup-hero__copy {
  padding: var(--space-8);
  background:
    linear-gradient(160deg, rgba(0, 188, 212, 0.10), transparent 42%),
    linear-gradient(320deg, rgba(112, 0, 255, 0.08), transparent 38%),
    var(--color-bg-surface);
}

.setup-hero__copy h1,
.setup-hero__copy p,
.setup-mini-card p,
.setup-card h2,
.setup-card p {
  margin: 0;
}

.setup-hero__eyebrow {
  color: var(--color-brand-primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}

.setup-hero__copy h1 {
  margin-top: var(--space-3);
  font-size: 30px;
  line-height: 1.2;
  letter-spacing: -0.4px;
}

.setup-hero__summary {
  margin-top: var(--space-4);
  max-width: 720px;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.setup-hero__badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-5);
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.status-chip[data-tone="success"] {
  background: rgba(34, 211, 154, 0.12);
  border-color: rgba(34, 211, 154, 0.20);
  color: var(--color-success);
}

.status-chip[data-tone="warning"] {
  background: rgba(245, 183, 64, 0.12);
  border-color: rgba(245, 183, 64, 0.20);
  color: var(--color-warning);
}

.status-chip[data-tone="danger"] {
  background: rgba(255, 90, 99, 0.12);
  border-color: rgba(255, 90, 99, 0.18);
  color: var(--color-danger);
}

.status-chip[data-tone="info"],
.status-chip[data-tone="brand"] {
  background: var(--color-bg-active);
  border-color: var(--color-border-subtle);
  color: var(--color-brand-primary);
}

.status-chip[data-tone="neutral"] {
  background: var(--color-bg-muted);
  border-color: var(--color-border-subtle);
  color: var(--color-text-secondary);
}

.setup-hero__panel {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4);
}

.setup-mini-card {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
}

.setup-mini-card__label,
.setup-card__summary,
.setup-card__hint,
.setup-alert {
  color: var(--color-text-secondary);
}

.setup-mini-card strong {
  font-size: 18px;
  line-height: 1.35;
  word-break: break-word;
}

.setup-mini-card__actions,
.setup-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.setup-alert {
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-muted);
  line-height: 1.6;
}

.setup-alert[data-tone="danger"] {
  border-color: rgba(255, 90, 99, 0.20);
  background: rgba(255, 90, 99, 0.08);
  color: var(--color-danger);
}

.setup-grid {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-items: start;
}

.setup-card {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
  min-height: 100%;
}

.setup-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.setup-card__header h2 {
  margin-top: 4px;
  font-size: 18px;
  line-height: 1.3;
}

.setup-card__summary {
  line-height: 1.7;
}

.setup-field {
  display: grid;
  gap: 8px;
}

.setup-field > span {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.setup-textarea {
  min-height: 120px;
  resize: vertical;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-canvas);
  color: var(--color-text-primary);
  padding: 12px 14px;
  font-family: inherit;
  line-height: 1.6;
}

.setup-textarea:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.setup-metric-list,
.setup-checklist {
  display: grid;
  gap: var(--space-3);
}

.setup-metric-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.setup-metric-list li,
.setup-checklist li {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
}

.setup-metric-list span,
.setup-checklist__label {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.setup-metric-list strong,
.setup-checklist strong {
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}

.setup-metric-list strong {
  font-weight: 600;
}

.setup-checklist p,
.setup-card__hint {
  line-height: 1.6;
}

.setup-checklist li[data-state="ready"] {
  border-color: rgba(34, 211, 154, 0.18);
}

.setup-checklist li[data-state="empty"] {
  border-color: rgba(245, 183, 64, 0.18);
}

.setup-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 36px;
  padding: 0 var(--space-4);
  border: 0;
  border-radius: var(--radius-md);
  background: var(--color-brand-primary);
  color: var(--color-text-on-brand);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.setup-button--secondary {
  background: transparent;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-default);
}

.setup-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 1180px) {
  .setup-hero,
  .setup-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .setup-hero__copy {
    padding: var(--space-5);
  }

  .setup-card,
  .setup-hero__panel {
    padding: var(--space-4);
  }

  .setup-metric-list {
    grid-template-columns: 1fr;
  }
}
</style>
