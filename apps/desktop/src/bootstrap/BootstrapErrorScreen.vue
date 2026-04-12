<template>
  <section class="bootstrap-screen" data-bootstrap-screen="error">
    <div class="bootstrap-screen__backdrop" aria-hidden="true" />
    <div class="bootstrap-screen__panel">
      <p class="bootstrap-screen__eyebrow">启动检查未完成</p>
      <h1>暂时无法进入授权与初始化流程</h1>
      <p class="bootstrap-screen__summary">
        本地 Runtime 或配置读取存在异常。请先处理下方错误，再重新检查。
      </p>
      <p class="settings-page__error">{{ errorSummary }}</p>
      <div class="bootstrap-screen__actions">
        <button
          class="settings-page__button"
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
