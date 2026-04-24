<template>
  <div class="setup-wizard-page" :class="{ 'is-bursting': burstActive }">
    <div class="aurora-bg"></div>
    <div v-if="burstActive" class="burst-particles">
      <div v-for="index in 6" :key="index" class="particle"></div>
    </div>

    <section class="wizard-card" :data-setup-state="setupState">
      <header class="wizard-header">
        <div class="wizard-logo"></div>
        <div class="wizard-titles">
          <h1>TK-OPS</h1>
          <p>首启与授权向导</p>
        </div>
        <div v-if="activeStep !== 'done'" class="step-progress-badge">
          步骤 {{ activeStepIndex + 1 }} / 3
        </div>
      </header>

      <div class="state-banner" :class="`is-${setupState}`">
        <strong>{{ stateHeadline }}</strong>
        <span>{{ stateDescription }}</span>
      </div>

      <div class="wizard-content step-list">
        <article class="step-item" :class="getStepClass(runtimeState)">
          <div class="step-header">
            <span class="material-symbols-outlined step-icon" :class="{ spinning: isSpinning(runtimeState) }">
              {{ getIcon(runtimeState) }}
            </span>
            <div class="step-title">1. Runtime 健康检查</div>
            <div class="step-status">{{ getLabel(runtimeState) }}</div>
          </div>
          <div v-if="activeStep === 'runtime' || runtimeState === 'failed'" class="step-body">
            <p v-if="runtimeState === 'detecting' || runtimeState === 're-detecting'" class="step-desc">
              正在检查本地 Python Runtime、健康状态与基础依赖。
            </p>
            <div v-else-if="runtimeState === 'failed'" class="step-error-area">
              <div class="error-box">
                <span class="material-symbols-outlined error-icon">warning</span>
                <div class="error-content">
                  <span class="error-text">{{ runtimeErrorMessage }}</span>
                  <span v-if="runtimeRequestId" class="error-meta">请求号：{{ runtimeRequestId }}</span>
                </div>
              </div>
              <div class="step-actions">
                <Button
                  variant="primary"
                  size="sm"
                  :running="runtimeState === 're-detecting'"
                  @click="retryRuntime"
                >
                  重新检测 Runtime
                </Button>
              </div>
            </div>
          </div>
        </article>

        <article class="step-item" :class="getStepClass(licenseState)">
          <div class="step-header">
            <span class="material-symbols-outlined step-icon" :class="{ spinning: isSpinning(licenseState) }">
              {{ getIcon(licenseState) }}
            </span>
            <div class="step-title">2. 许可证校验</div>
            <div class="step-status">{{ getLabel(licenseState) }}</div>
          </div>
          <div
            v-if="showLicensePanel"
            class="step-body"
          >
            <p v-if="licenseState === 'detecting'" class="step-desc">
              正在校验设备授权状态。
            </p>
            <div v-else class="step-error-area">
              <p class="step-desc">
                {{ licensePanelDescription }}
              </p>

              <div class="machine-code-box">
                <code>{{ machineCodeText }}</code>
                <Button
                  variant="ghost"
                  size="sm"
                  icon-only
                  title="复制机器码"
                  :disabled="!licenseStore.machineCode"
                  @click="copyMachineCode"
                >
                  <span class="material-symbols-outlined">content_copy</span>
                </Button>
              </div>

              <div class="form-field">
                <div
                  class="activation-input"
                  :class="{ 'has-error': Boolean(licenseStore.error), 'is-disabled': activationInputDisabled }"
                >
                  <input
                    v-model="activationCode"
                    data-field="activationCode"
                    type="text"
                    placeholder="在此粘贴授权码"
                    :disabled="activationInputDisabled"
                  />
                </div>
                <div v-if="licenseHint" class="activation-hint" :class="{ 'is-error': Boolean(licenseStore.error) }">
                  {{ licenseHint }}
                </div>
              </div>

              <div class="step-actions">
                <Button
                  variant="primary"
                  size="sm"
                  :running="licenseStore.status === 'submitting'"
                  :disabled="activateDisabled"
                  @click="handleActivate"
                >
                  激活并继续
                </Button>
                <Button
                  v-if="!licenseStore.active"
                  variant="ghost"
                  size="sm"
                  @click="retryLicense"
                >
                  刷新授权状态
                </Button>
              </div>
            </div>
          </div>
        </article>

        <article class="step-item" :class="getStepClass(initState)">
          <div class="step-header">
            <span class="material-symbols-outlined step-icon" :class="{ spinning: isSpinning(initState) }">
              {{ getIcon(initState) }}
            </span>
            <div class="step-title">3. 目录与 Provider 初始化</div>
            <div class="step-status">{{ getLabel(initState) }}</div>
          </div>
          <div v-if="showInitPanel" class="step-body">
            <div v-if="setupState === 'empty'" class="step-error-area">
              <p class="step-desc">
                当前目录与 AI Provider 还没有完成首启初始化，请继续初始化后再进入创作总览。
              </p>
              <ul class="init-checklist">
                <li v-for="item in initializationChecklist" :key="item.id">
                  <span class="material-symbols-outlined" :class="item.state === 'ready' ? 'text-success' : 'text-warning'">
                    {{ item.state === 'ready' ? 'check_circle' : 'error' }}
                  </span>
                  <span>
                    {{ item.label }}
                    <span v-if="item.state !== 'ready'" class="text-warning text-xs">未完成</span>
                  </span>
                </li>
              </ul>
              <div class="step-actions">
                <Button variant="primary" size="sm" @click="goToSettings">继续初始化</Button>
                <Button variant="ghost" size="sm" @click="retryInit">重新检测配置</Button>
              </div>
            </div>
            <div v-else-if="setupState === 'ready'" class="step-success">
              <p class="step-desc text-success">目录、Provider 与运行环境已就绪，可以进入创作总览。</p>
            </div>
            <div v-else-if="setupState === 'error'" class="step-error-area">
              <div class="error-box">
                <span class="material-symbols-outlined error-icon">warning</span>
                <div class="error-content">
                  <span class="error-text">{{ runtimeErrorMessage }}</span>
                  <span v-if="runtimeRequestId" class="error-meta">请求号：{{ runtimeRequestId }}</span>
                </div>
              </div>
              <div class="step-actions">
                <Button variant="primary" size="sm" @click="retryInit">重新检测配置</Button>
              </div>
            </div>
            <p v-else class="step-desc">等待前置步骤完成后再初始化目录与 Provider。</p>
          </div>
        </article>
      </div>

      <footer class="wizard-footer">
        <transition name="fade">
          <Button
            v-if="setupState === 'ready'"
            data-action="open-dashboard"
            variant="ai"
            size="lg"
            block
            @click="finishSetup"
          >
            进入创作总览
          </Button>
          <button v-else class="skip-btn" @click="finishSetup">跳过引导（受限模式）</button>
        </transition>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { hasCompletedBootstrapInitialization } from "@/bootstrap/bootstrap-form";
import Button from "@/components/ui/Button/Button.vue";
import { useConfigBusStore } from "@/stores/config-bus";
import { useBootstrapStore } from "@/stores/bootstrap";
import { useLicenseStore } from "@/stores/license";

type WizardStepState = "pending" | "detecting" | "re-detecting" | "success" | "failed";
type SetupState = "loading" | "blocked" | "empty" | "ready" | "error";

const bootstrapStore = useBootstrapStore();
const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const router = useRouter();

const activationCode = ref("");
const burstActive = ref(false);
const isRuntimeRetrying = ref(false);
const isLicenseRetrying = ref(false);
const isInitRetrying = ref(false);

onMounted(() => {
  if (bootstrapStore.phase === "boot_loading") {
    void bootstrapStore.load();
  }
});

const isFullyInitialized = computed(() => hasCompletedBootstrapInitialization(configBusStore.settings));

const runtimeState = computed<WizardStepState>(() => {
  if (configBusStore.runtimeStatus === "loading") {
    return isRuntimeRetrying.value ? "re-detecting" : "detecting";
  }
  if (configBusStore.runtimeStatus === "online") {
    return "success";
  }
  if (configBusStore.runtimeStatus === "offline" || configBusStore.status === "error") {
    return "failed";
  }
  return "pending";
});

const licenseState = computed<WizardStepState>(() => {
  if (runtimeState.value !== "success") {
    return "pending";
  }
  if (
    licenseStore.status === "loading" ||
    licenseStore.status === "submitting" ||
    isLicenseRetrying.value
  ) {
    return "detecting";
  }
  return licenseStore.active ? "success" : "failed";
});

const initState = computed<WizardStepState>(() => {
  if (licenseState.value !== "success") {
    return "pending";
  }
  if (configBusStore.status === "loading" || isInitRetrying.value) {
    return "detecting";
  }
  if (configBusStore.status === "error") {
    return "failed";
  }
  return isFullyInitialized.value ? "success" : "failed";
});

const setupState = computed<SetupState>(() => {
  if (runtimeState.value === "detecting" || licenseState.value === "detecting" || initState.value === "detecting") {
    return "loading";
  }
  if (configBusStore.status === "error" || configBusStore.runtimeStatus === "offline") {
    return "error";
  }
  if (licenseStore.status === "error") {
    return "error";
  }
  if (!licenseStore.active) {
    return "blocked";
  }
  if (!isFullyInitialized.value) {
    return "empty";
  }
  return "ready";
});

const activeStep = computed(() => {
  if (runtimeState.value !== "success") {
    return "runtime";
  }
  if (licenseState.value !== "success") {
    return "license";
  }
  if (initState.value !== "success") {
    return "init";
  }
  return "done";
});

const activeStepIndex = computed(() => {
  const steps = ["runtime", "license", "init", "done"];
  return steps.indexOf(activeStep.value);
});

const stateHeadline = computed(() => {
  switch (setupState.value) {
    case "loading":
      return "首启检查进行中";
    case "blocked":
      return "待授权";
    case "empty":
      return "初始化未完成";
    case "ready":
      return "环境已就绪";
    case "error":
      return "首启检查失败";
    default:
      return "";
  }
});

const stateDescription = computed(() => {
  switch (setupState.value) {
    case "loading":
      return "正在确认 Runtime、许可证和基础配置。";
    case "blocked":
      return "请先完成设备授权，再继续首启流程。";
    case "empty":
      return "许可证已通过，但目录与 AI Provider 还需要继续初始化。";
    case "ready":
      return "Runtime 健康、许可证校验和目录初始化均已完成。";
    case "error":
      return "Runtime 或配置读取失败，请根据错误信息重试。";
    default:
      return "";
  }
});

const showLicensePanel = computed(() => {
  return activeStep.value === "license" || setupState.value === "ready" || setupState.value === "blocked";
});

const showInitPanel = computed(() => {
  return activeStep.value === "init" || setupState.value === "ready" || setupState.value === "error";
});

const machineCodeText = computed(() => licenseStore.machineCode || "读取中...");

const activationInputDisabled = computed(() => setupState.value !== "blocked");

const activateDisabled = computed(() => {
  return (
    activationInputDisabled.value ||
    !activationCode.value.trim() ||
    licenseStore.status === "submitting"
  );
});

const licenseHint = computed(() => {
  if (licenseStore.error?.requestId) {
    return `${licenseStore.error.message}（请求号：${licenseStore.error.requestId}）`;
  }
  return licenseStore.error?.message || "";
});

const licensePanelDescription = computed(() => {
  if (setupState.value === "ready") {
    return "当前设备已完成授权，授权码输入框已锁定。";
  }
  return "当前设备尚未授权。请向管理员提供以下机器码并粘贴授权码完成激活。";
});

const initializationChecklist = computed(() => {
  const settings = configBusStore.settings;
  return [
    {
      id: "workspace-root",
      label: "工作区目录",
      state: settings?.runtime?.workspaceRoot ? "ready" : "empty"
    },
    {
      id: "ai-provider",
      label: "AI Provider",
      state: settings?.ai?.provider ? "ready" : "empty"
    }
  ];
});

const runtimeErrorMessage = computed(() => {
  if (licenseStore.status === "error") {
    return licenseStore.error?.message || "许可证请求失败，请稍后重试。";
  }
  return configBusStore.error?.message || "首启检查失败，请稍后重试。";
});

const runtimeRequestId = computed(() => {
  if (licenseStore.status === "error") {
    return licenseStore.error?.requestId || "";
  }
  return configBusStore.error?.requestId || "";
});

function getLabel(state: WizardStepState) {
  switch (state) {
    case "pending":
      return "等待中";
    case "detecting":
      return "检测中...";
    case "re-detecting":
      return "重新检测中...";
    case "success":
      return "检测成功";
    case "failed":
      return "检测失败";
    default:
      return "";
  }
}

function getIcon(state: WizardStepState) {
  switch (state) {
    case "pending":
      return "schedule";
    case "detecting":
    case "re-detecting":
      return "sync";
    case "success":
      return "check_circle";
    case "failed":
      return "error";
    default:
      return "help";
  }
}

function getStepClass(state: WizardStepState) {
  return `is-${state}`;
}

function isSpinning(state: WizardStepState) {
  return state === "detecting" || state === "re-detecting";
}

function retryRuntime() {
  isRuntimeRetrying.value = true;
  void bootstrapStore.retry().finally(() => {
    isRuntimeRetrying.value = false;
  });
}

async function retryLicense() {
  isLicenseRetrying.value = true;
  try {
    await licenseStore.loadStatus();
  } finally {
    isLicenseRetrying.value = false;
  }
}

async function retryInit() {
  isInitRetrying.value = true;
  try {
    await configBusStore.load();
  } finally {
    isInitRetrying.value = false;
  }
}

async function copyMachineCode() {
  if (!licenseStore.machineCode) {
    return;
  }

  try {
    await navigator.clipboard.writeText(licenseStore.machineCode);
  } catch {
    // 剪贴板失败不影响首启主链路。
  }
}

async function handleActivate() {
  if (activateDisabled.value) {
    return;
  }

  const success = await bootstrapStore.activateLicense({
    activationCode: activationCode.value.trim()
  });

  if (success) {
    activationCode.value = "";
    triggerBurst();
  }
}

function triggerBurst() {
  burstActive.value = true;
  window.setTimeout(() => {
    burstActive.value = false;
  }, 400);
}

function goToSettings() {
  void router.push("/settings/ai-system");
}

function finishSetup() {
  void router.push("/dashboard");
}
</script>

<style scoped src="./SetupLicenseWizardPage.css"></style>
