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
        <li>确认本地 Runtime 服务已启动</li>
        <li>检查 127.0.0.1:8000 端口是否可访问</li>
        <li>确认配置文件与工作区目录没有被占用</li>
      </ul>

      <div class="bootstrap-screen__actions">
        <button
          class="settings-page__button bootstrap-error__retry-btn"
          type="button"
          data-action="retry-bootstrap"
          @click="$emit('retry')"
        >
          重新检查
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
defineEmits<{ retry: [] }>();

defineProps<{ errorSummary: string }>();
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
  animation: exception-breathe var(--bootstrap-error-breathe-duration) ease-in-out infinite;
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
</style>
