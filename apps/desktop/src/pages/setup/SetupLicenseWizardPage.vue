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
          <p>AI 视频创作中枢</p>
        </div>
      </div>

      <div class="wizard-steps-indicator" v-if="currentStep > 0 && currentStep < 4">
        <div 
          v-for="step in 3" 
          :key="step" 
          class="step-dot" 
          :class="{ 'is-active': currentStep === step, 'is-completed': currentStep > step }"
        ></div>
      </div>

      <div class="wizard-content">
        <transition name="step-slide">
          
          <!-- Step 0: Welcome -->
          <div v-if="currentStep === 0" class="step-panel" key="step-0">
            <div class="step-body">
              <h2>欢迎使用</h2>
              <p>作为您的本地 AI 创作中枢，我们需要进行首次环境检查与设备授权，以确保所有功能正常运行。</p>
            </div>
            <div class="step-actions">
              <Button variant="ai" size="lg" block @click="goToStep(1)">开始初始化</Button>
            </div>
          </div>
          
          <!-- Step 1: License Activation -->
          <div v-else-if="currentStep === 1" class="step-panel" key="step-1">
            <div class="step-body">
              <h2>许可证激活</h2>
              <p>向管理员提供以下本机机器码，获取一机一码授权码。</p>
              
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
            </div>
            <div class="step-actions">
              <Button 
                variant="primary" 
                size="lg" 
                block 
                :running="licenseStore.status === 'submitting'"
                :disabled="!activationCode.trim() || licenseStore.status === 'submitting'"
                @click="handleActivate"
              >
                激活并继续
              </Button>
            </div>
          </div>
          
          <!-- Step 2: Runtime Health -->
          <div v-else-if="currentStep === 2" class="step-panel" key="step-2">
            <div class="step-body">
              <h2>Runtime 健康检查</h2>
              <p>正在检查本地 Python 核心服务的运行状态与依赖。</p>
              
              <ul class="health-checklist">
                <li>
                  <span class="material-symbols-outlined" :class="runtimeIconClass">{{ runtimeIcon }}</span>
                  <div class="check-info">
                    <strong>核心服务连接</strong>
                    <span>{{ runtimeStatusLabel }}</span>
                  </div>
                </li>
                <li>
                  <span class="material-symbols-outlined" :class="configIconClass">{{ configIcon }}</span>
                  <div class="check-info">
                    <strong>配置总线</strong>
                    <span>{{ configStatusLabel }}</span>
                  </div>
                </li>
              </ul>
              <div v-if="configBusStore.error" class="error-box">
                {{ configBusStore.error.message }}
              </div>
            </div>
            <div class="step-actions">
              <Button 
                variant="primary" 
                size="lg" 
                block 
                :disabled="configBusStore.runtimeStatus !== 'online'"
                @click="goToStep(3)"
              >
                下一步
              </Button>
              <Button 
                v-if="configBusStore.runtimeStatus !== 'online'"
                variant="ghost" 
                size="lg" 
                block 
                @click="retryCheck"
              >
                重试检查
              </Button>
            </div>
          </div>

          <!-- Step 3: Initialization & Complete -->
          <div v-else-if="currentStep === 3" class="step-panel" key="step-3">
            <div class="step-body">
              <h2>一切就绪</h2>
              <p>环境检查与授权已完成。如果您是首次使用，建议前往系统设置补齐工作区目录与 AI Provider 配置。</p>
              
              <ul class="init-checklist">
                <li v-for="item in initializationChecklist" :key="item.id">
                  <span class="material-symbols-outlined" :class="item.state === 'ready' ? 'text-success' : 'text-warning'">
                    {{ item.state === 'ready' ? 'check_circle' : 'pending' }}
                  </span>
                  <span>{{ item.label }}</span>
                </li>
              </ul>
            </div>
            <div class="step-actions">
              <Button 
                variant="secondary" 
                size="lg" 
                block 
                v-if="!isFullyInitialized"
                @click="goToSettings"
              >
                前往系统设置
              </Button>
              <Button 
                variant="ai" 
                size="lg" 
                block 
                @click="finishSetup"
              >
                进入创作总览
              </Button>
            </div>
          </div>
        </transition>
      </div>
    </div>
    
    <button v-if="currentStep > 0 && currentStep < 3" class="skip-btn" @click="finishSetup">跳过引导（受限模式）</button>
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

const bootstrapStore = useBootstrapStore();
const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const route = useRoute();
const router = useRouter();

const currentStep = ref(0);
const activationCode = ref("");
const burstActive = ref(false);

onMounted(() => {
  if (bootstrapStore.phase === "boot_loading") {
    void bootstrapStore.load();
  }
});

// Sync step based on actual status
watch(() => bootstrapStore.phase, (phase) => {
  if (currentStep.value === 0) return; // Keep welcome screen until they click start
  
  if (phase === "license_required") {
    currentStep.value = 1;
  } else if (phase === "boot_error") {
    currentStep.value = 2;
  } else if (phase === "initialization_required" || phase === "ready") {
    if (currentStep.value < 3) {
      currentStep.value = 3;
    }
  }
});

const runtimeStatusLabel = computed(() => {
  if (configBusStore.runtimeStatus === "online") return `在线 (${configBusStore.health?.version || "未知版本"})`;
  if (configBusStore.runtimeStatus === "loading") return "检查中...";
  return "离线";
});

const runtimeIcon = computed(() => {
  if (configBusStore.runtimeStatus === "online") return "check_circle";
  if (configBusStore.runtimeStatus === "loading") return "sync";
  return "error";
});

const runtimeIconClass = computed(() => {
  if (configBusStore.runtimeStatus === "online") return "text-success";
  if (configBusStore.runtimeStatus === "loading") return "text-info spinning";
  return "text-danger";
});

const configStatusLabel = computed(() => {
  if (configBusStore.settings) return "已加载";
  if (configBusStore.status === "loading") return "读取中...";
  return "异常";
});

const configIcon = computed(() => {
  if (configBusStore.settings) return "check_circle";
  if (configBusStore.status === "loading") return "sync";
  return "error";
});

const configIconClass = computed(() => {
  if (configBusStore.settings) return "text-success";
  if (configBusStore.status === "loading") return "text-info spinning";
  return "text-danger";
});

const isFullyInitialized = computed(() => hasCompletedBootstrapInitialization(configBusStore.settings));

const initializationChecklist = computed(() => {
  const settings = configBusStore.settings;
  return [
    { id: "workspace-root", label: "工作区目录", state: settings?.runtime?.workspaceRoot ? "ready" : "empty" },
    { id: "ai-model", label: "AI Provider配置", state: settings?.ai?.provider ? "ready" : "empty" }
  ];
});

function goToStep(step: number) {
  const isPreview = route.query.preview !== undefined;
  
  if (step === 1 && licenseStore.active && !isPreview) {
    // skip license if already active
    currentStep.value = 2;
    return;
  }
  if (step === 2 && configBusStore.runtimeStatus === 'online' && !isPreview) {
    // skip runtime check if already online? No, maybe show it quickly
  }
  currentStep.value = step;
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
    setTimeout(() => {
      goToStep(2);
    }, 1000);
  }
}

function retryCheck() {
  void bootstrapStore.retry();
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
  z-index: 9999; /* Overlay everything, do not use AppShell */
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
  width: 640px;
  height: 560px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-2xl);
  padding: var(--space-12);
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
  margin-bottom: var(--space-6);
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

/* Steps Indicator */
.wizard-steps-indicator {
  display: flex;
  justify-content: center;
  gap: var(--space-3);
  margin-bottom: var(--space-8);
}

.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-border-strong);
  transition: background-color var(--motion-default) var(--ease-standard);
}

.step-dot.is-active {
  background: var(--color-brand-primary);
  box-shadow: 0 0 8px var(--color-brand-glow);
}

.step-dot.is-completed {
  background: var(--color-brand-primary);
  opacity: 0.5;
}

/* Content Area */
.wizard-content {
  flex: 1;
  position: relative;
}

.step-panel {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
}

.step-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.step-body h2 {
  margin: 0 0 var(--space-3) 0;
  font: var(--font-title-lg);
  color: var(--color-text-primary);
}

.step-body p {
  margin: 0 0 var(--space-6) 0;
  font: var(--font-body-md);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.step-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: auto;
}

/* Animations */
.step-slide-enter-active,
.step-slide-leave-active {
  transition: opacity 0.4s cubic-bezier(0.22, 1, 0.36, 1), transform 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}

.step-slide-enter-from {
  opacity: 0;
  transform: translateX(32px);
}

.step-slide-leave-to {
  opacity: 0;
  transform: translateX(-32px);
}

/* Form Elements */
.machine-code-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-4);
}

.machine-code-box code {
  font: var(--font-mono-md);
  color: var(--color-text-primary);
  word-break: break-all;
  text-align: left;
}

.form-field {
  width: 100%;
  text-align: left;
}

/* Checklists */
.health-checklist {
  list-style: none;
  padding: 0;
  margin: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.health-checklist li {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  text-align: left;
}

.check-info {
  display: flex;
  flex-direction: column;
}

.check-info strong {
  font: var(--font-title-sm);
  color: var(--color-text-primary);
}

.check-info span {
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.init-checklist {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
  max-width: 320px;
}

.init-checklist li {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font: var(--font-body-sm);
  color: var(--color-text-primary);
  text-align: left;
}

/* Utilities */
.text-success { color: var(--color-success); }
.text-danger { color: var(--color-danger); }
.text-warning { color: var(--color-warning); }
.text-info { color: var(--color-info); }
.spinning { animation: spin 2s linear infinite; }

@keyframes spin { 100% { transform: rotate(360deg); } }

.error-box {
  margin-top: var(--space-4);
  padding: var(--space-3);
  background: rgba(255, 90, 99, 0.1);
  color: var(--color-danger);
  border-radius: var(--radius-md);
  font: var(--font-body-sm);
  width: 100%;
  text-align: left;
}

/* Skip Button */
.skip-btn {
  position: absolute;
  bottom: var(--space-8);
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
