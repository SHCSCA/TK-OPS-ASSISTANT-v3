<template>
  <section class="bootstrap-screen" data-bootstrap-screen="error">
    <div class="bootstrap-screen__backdrop" aria-hidden="true" />
    <div
      class="bootstrap-screen__panel bootstrap-error__panel bootstrap-error__panel-enter"
      data-testid="bootstrap-error-panel"
    >
      <div class="bootstrap-error__header">
        <div class="bootstrap-error__icon-wrap" aria-hidden="true">
          <span class="material-symbols-outlined bootstrap-error__icon">error</span>
        </div>
        <div class="bootstrap-screen__copy">
          <p class="bootstrap-screen__eyebrow">启动检查未完成</p>
          <h1>暂时无法进入授权与初始化流程</h1>
          <p class="bootstrap-screen__summary">
            本地 Runtime 或配置读取存在异常。请先处理下方错误，再重新检查。
          </p>
        </div>
      </div>

      <p class="bootstrap-error__message">{{ errorSummary }}</p>

      <ul class="bootstrap-error__checklist" data-testid="bootstrap-error-checklist">
        <li>确认桌面 Runtime 进程没有被安全软件拦截</li>
        <li>如刚完成升级，请等待数据库迁移与结构校验结束</li>
        <li>确认配置文件与工作区目录没有被占用</li>
      </ul>

      <div class="bootstrap-screen__actions">
        <button
          v-if="canRestart"
          class="settings-page__button bootstrap-error__restart-btn"
          type="button"
          :disabled="restarting"
          data-action="restart-runtime"
          @click="$emit('restart')"
        >
          {{ restarting ? "正在重新启动…" : "重新启动 Runtime" }}
        </button>
        <button
          class="settings-page__button bootstrap-error__retry-btn"
          type="button"
          data-action="retry-bootstrap"
          @click="$emit('retry')"
        >
          重新检查
        </button>
        <button
          class="settings-page__button"
          type="button"
          :disabled="diagnosticsBusy || !diagnostics"
          data-action="copy-runtime-diagnostics"
          @click="copyDiagnostics"
        >
          复制诊断摘要
        </button>
        <button
          class="settings-page__button"
          type="button"
          :disabled="diagnosticsBusy"
          data-action="export-runtime-diagnostics"
          @click="exportDiagnostics"
        >
          {{ diagnosticsBusy ? "正在处理…" : "导出诊断" }}
        </button>
      </div>
      <p
        v-if="diagnosticsFeedback"
        class="bootstrap-error__diagnostics-feedback"
        role="status"
      >
        {{ diagnosticsFeedback }}
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import {
  exportDesktopRuntimeSupervisorDiagnostics,
  getDesktopRuntimeSupervisorDiagnostics,
  type RuntimeSupervisorDiagnostics
} from "@/app/runtime-client/connection";

defineEmits<{
  restart: [];
  retry: [];
}>();

defineProps<{
  canRestart?: boolean;
  errorSummary: string;
  restarting?: boolean;
}>();

const diagnostics = ref<RuntimeSupervisorDiagnostics | null>(null);
const diagnosticsBusy = ref(false);
const diagnosticsFeedback = ref("");

onMounted(() => {
  void loadDiagnostics();
});

async function loadDiagnostics(): Promise<void> {
  try {
    diagnostics.value = await getDesktopRuntimeSupervisorDiagnostics();
  } catch {
    diagnostics.value = null;
    diagnosticsFeedback.value = "暂时无法读取脱机诊断，可直接尝试导出。";
  }
}

async function copyDiagnostics(): Promise<void> {
  if (!diagnostics.value) return;
  try {
    await navigator.clipboard.writeText(
      JSON.stringify(diagnostics.value, null, 2)
    );
    diagnosticsFeedback.value = "诊断摘要已复制。";
  } catch {
    diagnosticsFeedback.value = "复制失败，请改用导出诊断。";
  }
}

async function exportDiagnostics(): Promise<void> {
  diagnosticsBusy.value = true;
  try {
    const result = await exportDesktopRuntimeSupervisorDiagnostics();
    diagnosticsFeedback.value = `诊断已导出：${result.fileName}`;
  } catch {
    diagnosticsFeedback.value = "导出失败，请检查应用数据目录权限后重试。";
  } finally {
    diagnosticsBusy.value = false;
  }
}
</script>

<style scoped>
/* 面板入场 */
.bootstrap-error__panel-enter {
  animation: bootstrap-panel-in var(--bootstrap-panel-enter-duration) var(--ease-decelerate) both;
}

@keyframes bootstrap-panel-in {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* 错误边框呼吸 */
.bootstrap-error__icon-wrap {
  animation: exception-breathe var(--motion-breathe) ease-in-out infinite;
}

/* 重试按钮悬停微交互 */
.bootstrap-error__retry-btn {
  transition:
    transform var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard);
}

.bootstrap-error__retry-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.bootstrap-error__retry-btn:active {
  transform: translateY(0) scale(0.98);
}

.bootstrap-error__restart-btn {
  border-color: var(--brand-primary);
  color: var(--color-text-on-brand);
  background: var(--brand-primary);
}

.bootstrap-error__diagnostics-feedback {
  margin: var(--space-3) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}
</style>
