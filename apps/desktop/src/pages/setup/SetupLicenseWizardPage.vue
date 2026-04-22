<template>
  <div class="setup-wizard-page" :class="{ 'is-bursting': burstActive }">
    <div class="aurora-bg"></div>
    <div class="burst-particles" v-if="burstActive">
      <div class="particle" v-for="i in 6" :key="i"></div>
    </div>

    <div class="wizard-card">
      <div class="wizard-header">
        <div class="wizard-logo"></div>
        <div class="wizard-titles">
          <h1>TK-OPS</h1>
          <p>环境自检与初始化</p>
        </div>
        <!-- V2: Step progress indicator -->
        <div class="step-progress-badge" v-if="activeStep !== 'done'">
          步骤 {{ activeStepIndex + 1 }} / 3
        </div>
      </div>

      <div class="wizard-content step-list">
        <!-- 1. Runtime Health Check -->
        <div class="step-item" :class="getStepClass(runtimeState)">
          <div class="step-header">
            <span class="material-symbols-outlined step-icon" :class="{ 'spinning': isSpinning(runtimeState) }">
              {{ getIcon(runtimeState) }}
            </span>
            <div class="step-title">1. Runtime 健康检查</div>
            <div class="step-status">{{ getLabel(runtimeState) }}</div>
          </div>
          <div class="step-body" v-if="activeStep === 'runtime' || runtimeState === 'failed'">
            <p v-if="runtimeState === 'detecting' || runtimeState === 're-detecting'" class="step-desc">
              正在检查本地 Python 核心服务的运行状态与依赖...
            </p>
            <div v-if="runtimeState === 'failed'" class="step-error-area">
              <div class="error-box">
                <span class="material-symbols-outlined error-icon">warning</span>
                <span class="error-text">{{ configBusStore.error?.message || '无法连接到本地核心服务，请检查后端是否正常运行。' }}</span>
              </div>
              <div class="step-actions">
                <Button variant="primary" size="sm" @click="retryRuntime" :running="runtimeState === 're-detecting'">
                  重新检测 Runtime
                </Button>
              </div>
            </div>
          </div>
        </div>

        <!-- 2. License Activation -->
        <div class="step-item" :class="getStepClass(licenseState)">
          <div class="step-header">
            <span class="material-symbols-outlined step-icon" :class="{ 'spinning': isSpinning(licenseState) }">
              {{ getIcon(licenseState) }}
            </span>
            <div class="step-title">2. 许可证校验</div>
            <div class="step-status">{{ getLabel(licenseState) }}</div>
          </div>
          <div class="step-body" v-if="activeStep === 'license' || (licenseState === 'failed' && runtimeState === 'success')">
            <p v-if="licenseState === 'detecting'" class="step-desc">正在验证许可证信息...</p>
            <div v-if="licenseState === 'failed'" class="step-error-area">
              <p class="step-desc">当前设备尚未授权。请向管理员提供以下机器码获取授权。</p>
              
              <div class="machine-code-box">
                <code>{{ licenseStore.machineCode || "读取中..." }}</code>
                <Button variant="ghost" size="sm" icon-only @click="copyMachineCode" title="复制机器码">
                  <span class="material-symbols-outlined">content_copy</span>
                </Button>
              </div>

              <div class="form-field">
                <Input 
                  v-model="activationCode" 
                  placeholder="在此粘贴授权码" 
                  :error="!!licenseStore.error"
                  :hint="licenseStore.error?.message"
                />
              </div>
              <div class="step-actions">
                <Button 
                  variant="primary" 
                  size="sm" 
                  :running="licenseStore.status === 'submitting'"
                  :disabled="!activationCode.trim() || licenseStore.status === 'submitting'"
                  @click="handleActivate"
                >
                  激活并继续
                </Button>
                <!-- V2: Retry detection entry -->
                <Button variant="ghost" size="sm" @click="retryLicense" v-if="!licenseStore.active">
                  刷新授权状态
                </Button>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. Directory & Provider Initialization -->
        <div class="step-item" :class="getStepClass(initState)">
          <div class="step-header">
            <span class="material-symbols-outlined step-icon" :class="{ 'spinning': isSpinning(initState) }">
              {{ getIcon(initState) }}
            </span>
            <div class="step-title">3. 目录与组件初始化</div>
            <div class="step-status">{{ getLabel(initState) }}</div>
          </div>
          <div class="step-body" v-if="activeStep === 'init' || initState === 'failed'">
            <div v-if="initState === 'failed'" class="step-error-area">
              <p class="step-desc">检测到部分基础路径或 AI 提供商尚未配置：</p>
              
              <ul class="init-checklist">
                <li v-for="item in initializationChecklist" :key="item.id">
                  <span class="material-symbols-outlined" :class="item.state === 'ready' ? 'text-success' : 'text-warning'">
                    {{ item.state === 'ready' ? 'check_circle' : 'error' }}
                  </span>
                  <span>{{ item.label }} <span v-if="item.state !== 'ready'" class="text-warning text-xs">(缺失)</span></span>
                </li>
              </ul>
              <div class="step-actions">
                <Button variant="primary" size="sm" @click="goToSettings">去配置目录与 AI</Button>
                <Button variant="ghost" size="sm" @click="retryInit">重新检测配置</Button>
              </div>
            </div>
            <p v-else-if="initState === 'success'" class="step-desc text-success">所有基础环境已就绪。</p>
            <p v-else class="step-desc">等待前置步骤完成...</p>
          </div>
        </div>
      </div>

      <div class="wizard-footer">
        <transition name="fade">
          <Button v-if="activeStep === 'done'" variant="ai" size="lg" block @click="finishSetup">
            进入创作总览
          </Button>
          <button v-else class="skip-btn" @click="finishSetup">跳过引导（受限模式）</button>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useBootstrapStore } from "@/stores/bootstrap";
import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { hasCompletedBootstrapInitialization } from "@/bootstrap/bootstrap-form";

import Button from "@/components/ui/Button/Button.vue";
import Input from "@/components/ui/Input/Input.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const bootstrapStore = useBootstrapStore();
const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const route = useRoute();
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

const runtimeState = computed(() => {
  if (configBusStore.runtimeStatus === 'loading') {
    return isRuntimeRetrying.value ? 're-detecting' : 'detecting';
  }
  if (configBusStore.runtimeStatus === 'online') {
    return 'success';
  }
  if (configBusStore.runtimeStatus === 'offline' || configBusStore.status === 'error') {
    return 'failed';
  }
  return 'pending';
});

const licenseState = computed(() => {
  if (runtimeState.value !== 'success') return 'pending';
  if (licenseStore.status === 'loading' || licenseStore.status === 'submitting' || isLicenseRetrying.value) return 'detecting';
  if (licenseStore.active) return 'success';
  return 'failed';
});

const initState = computed(() => {
  if (licenseState.value !== 'success') return 'pending';
  if (configBusStore.status === 'loading' || isInitRetrying.value) return 'detecting';
  if (isFullyInitialized.value) return 'success';
  return 'failed';
});

const activeStep = computed(() => {
  if (runtimeState.value !== 'success') return 'runtime';
  if (licenseState.value !== 'success') return 'license';
  if (initState.value !== 'success') return 'init';
  return 'done';
});

const activeStepIndex = computed(() => {
  const steps = ['runtime', 'license', 'init', 'done'];
  return steps.indexOf(activeStep.value);
});

const initializationChecklist = computed(() => {
  const settings = configBusStore.settings;
  return [
    { id: "workspace-root", label: "工作区目录", state: settings?.runtime?.workspaceRoot ? "ready" : "empty" },
    { id: "ai-model", label: "AI Provider配置", state: settings?.ai?.provider ? "ready" : "empty" }
  ];
});

function getLabel(state: string) {
  switch (state) {
    case 'pending': return '等待中';
    case 'detecting': return '检测中...';
    case 're-detecting': return '重新检测中...';
    case 'success': return '检测成功';
    case 'failed': return '检测失败';
    default: return '';
  }
}

function getIcon(state: string) {
  switch (state) {
    case 'pending': return 'schedule';
    case 'detecting': 
    case 're-detecting': return 'sync';
    case 'success': return 'check_circle';
    case 'failed': return 'error';
    default: return 'help';
  }
}

function getStepClass(state: string) {
  return `is-${state}`;
}

function isSpinning(state: string) {
  return state === 'detecting' || state === 're-detecting';
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
    await licenseStore.load();
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
  if (licenseStore.machineCode) {
    try {
      await navigator.clipboard.writeText(licenseStore.machineCode);
    } catch (e) {
      // ignore
    }
  }
}

async function handleActivate() {
  if (!activationCode.value.trim()) return;
  
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
  setTimeout(() => {
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

<style scoped>
.setup-wizard-page {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-canvas);
  overflow: hidden;
  z-index: 9999;
}

/* Aurora Background */
.aurora-bg {
  position: absolute;
  inset: -50%;
  background: var(--gradient-aurora);
  filter: blur(80px);
  opacity: 0.28;
  animation: aurora-rotate var(--motion-rotate-med) linear infinite;
  z-index: 0;
  pointer-events: none;
}

/* Wizard Card */
.wizard-card {
  position: relative;
  z-index: 1;
  width: 580px;
  min-height: 520px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-2xl);
  padding: var(--space-8) var(--space-10);
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  transition: box-shadow var(--motion-fast) var(--ease-standard);
}

.wizard-card.is-bursting {
  box-shadow: 0 0 64px var(--color-brand-glow);
}

/* Header */
.wizard-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--space-4);
  margin-bottom: var(--space-8);
  position: relative;
}

.step-progress-badge {
  position: absolute;
  top: 0;
  right: 0;
  font: var(--font-caption);
  color: var(--color-brand-primary);
  background: color-mix(in srgb, var(--color-brand-primary) 10%, transparent);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-weight: 700;
}

.wizard-logo {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  background: var(--gradient-ai-primary);
  box-shadow: var(--shadow-glow-brand);
  animation: subtle-pulse var(--motion-breathe) infinite;
}

.wizard-titles h1 {
  margin: 0;
  font: var(--font-display-md);
  letter-spacing: var(--ls-display-md);
  color: var(--color-text-primary);
}

.wizard-titles p {
  margin: 4px 0 0 0;
  font: var(--font-body-md);
  letter-spacing: 4px;
  color: var(--color-text-secondary);
  text-transform: uppercase;
}

/* Step List */
.step-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  flex: 1;
}

.step-item {
  display: flex;
  flex-direction: column;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  transition: all var(--motion-default) var(--ease-standard);
}

.step-item.is-pending {
  opacity: 0.5;
  filter: grayscale(1);
}

.step-item.is-detecting,
.step-item.is-re-detecting {
  border-color: var(--color-border-strong);
  box-shadow: 0 0 12px rgba(0, 0, 0, 0.05);
}

.step-item.is-failed {
  border-color: var(--color-danger);
  background: rgba(255, 90, 99, 0.05);
}

.step-item.is-success {
  border-color: var(--color-success);
  background: rgba(14, 204, 131, 0.05);
}

.step-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.step-icon {
  font-size: 24px;
}
.is-pending .step-icon { color: var(--color-text-tertiary); }
.is-detecting .step-icon, .is-re-detecting .step-icon { color: var(--color-info); }
.is-success .step-icon { color: var(--color-success); }
.is-failed .step-icon { color: var(--color-danger); }

.step-title {
  flex: 1;
  font: var(--font-title-sm);
  color: var(--color-text-primary);
}

.step-status {
  font: var(--font-caption);
  color: var(--color-text-secondary);
}
.is-success .step-status { color: var(--color-success); }
.is-failed .step-status { color: var(--color-danger); font-weight: 500; }
.is-detecting .step-status, .is-re-detecting .step-status { color: var(--color-info); }

.step-body {
  margin-top: var(--space-3);
  padding-left: calc(24px + var(--space-3));
}

.step-desc {
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-3) 0;
}

.step-error-area {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.error-box {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  background: rgba(255, 90, 99, 0.1);
  color: var(--color-danger);
  border-radius: var(--radius-md);
}

.error-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.error-text {
  font: var(--font-body-sm);
  line-height: 1.4;
}

.step-actions {
  display: flex;
  gap: var(--space-2);
}

/* Machine Code Box */
.machine-code-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-canvas);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-3);
}

.machine-code-box code {
  font: var(--font-mono-sm);
  color: var(--color-text-primary);
  word-break: break-all;
}

/* Checklists */
.init-checklist {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.init-checklist li {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font: var(--font-body-sm);
  color: var(--color-text-primary);
}

.text-success { color: var(--color-success); }
.text-warning { color: var(--color-warning); }
.text-xs { font-size: 12px; }

/* Utilities */
.spinning { animation: spin 2s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

/* Footer */
.wizard-footer {
  margin-top: var(--space-6);
  min-height: 48px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.skip-btn {
  background: transparent;
  border: none;
  color: var(--color-text-tertiary);
  font: var(--font-body-sm);
  cursor: pointer;
  transition: color var(--motion-fast) var(--ease-standard);
}

.skip-btn:hover {
  color: var(--color-text-secondary);
  text-decoration: underline;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--motion-default) var(--ease-standard);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Particles Burst */
.burst-particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
}

.particle {
  position: absolute;
  width: 8px;
  height: 8px;
  background: var(--color-brand-primary);
  border-radius: 50%;
  box-shadow: 0 0 12px var(--color-brand-primary);
  animation: activation-burst var(--motion-slow) var(--ease-decelerate) forwards;
}

.particle:nth-child(1) { transform-origin: -40px -40px; }
.particle:nth-child(2) { transform-origin: 40px -40px; }
.particle:nth-child(3) { transform-origin: -40px 40px; }
.particle:nth-child(4) { transform-origin: 40px 40px; }
.particle:nth-child(5) { transform-origin: -60px 0; }
.particle:nth-child(6) { transform-origin: 60px 0; }
</style>
