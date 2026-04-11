<template>
  <section class="placeholder-page">
    <div class="placeholder-page__header">
      <div>
        <p class="placeholder-page__eyebrow">M0 可运行基线</p>
        <h1>{{ title }}</h1>
      </div>
      <div class="placeholder-page__meta">
        <span class="page-chip">{{ routeId }}</span>
        <span class="page-chip page-chip--muted">{{ pageType }}</span>
      </div>
    </div>

    <div class="placeholder-page__body">
      <div class="placeholder-card">
        <h2>当前状态</h2>
        <p>{{ description }}</p>
      </div>
      <div class="placeholder-card">
        <h2>后续落点</h2>
        <p>本页已接入正式路由和壳层位置，后续业务模块将直接在当前页面根组件下展开。</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  description: string;
  pageType: string;
  routeId: string;
  title: string;
}>();
</script>
