<template>
  <section class="placeholder-page">
    <div class="placeholder-page__header">
      <div>
        <p class="placeholder-page__eyebrow">正式入口已接入</p>
        <h1>{{ title }}</h1>
      </div>
      <div class="placeholder-page__meta">
        <span class="page-chip">正式路由</span>
        <span class="page-chip page-chip--muted">{{ pageTypeLabel }}</span>
      </div>
    </div>

    <div class="placeholder-page__body">
      <div class="command-panel">
        <h2>当前状态</h2>
        <p>{{ description }}</p>
      </div>
      <div class="command-panel">
        <h2>后续落点</h2>
        <p>
          本页已经接入正式路由和全局壳层。后续业务模块会直接在当前页面根组件下展开，
          并继续使用统一 Runtime、配置总线和状态反馈。
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  description: string;
  pageType: string;
  routeId: string;
  title: string;
}>();

void props.routeId;

const pageTypeLabel = computed(() => {
  switch (props.pageType) {
    case "workspace":
      return "工作区";
    case "editor":
      return "编辑器";
    case "queue":
      return "任务队列";
    case "settings":
      return "系统设置";
    default:
      return props.pageType;
  }
});
</script>
