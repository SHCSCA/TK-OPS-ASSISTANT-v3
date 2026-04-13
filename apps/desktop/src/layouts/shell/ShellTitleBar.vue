<template>
  <header class="title-bar command-title-bar shell-title-bar">
    <div class="title-bar__brand command-brand">
      <div class="brand-mark command-brand__mark">TK</div>
      <div>
        <p class="brand-label">TK-OPS 本地 AI 视频创作中枢</p>
        <h1>{{ title }}</h1>
        <p class="title-bar__meta">{{ summary }}</p>
      </div>
    </div>

    <div class="title-bar__status command-title-bar__status">
      <span class="status-pill" :class="`status-pill--${runtimeTone}`">{{ runtimeLabel }}</span>
      <span class="status-pill" :class="`status-pill--${configTone}`">{{ configLabel }}</span>
      <span class="status-pill" :class="`status-pill--${licenseTone}`">{{ licenseLabel }}</span>
      <span class="status-pill status-pill--idle" data-current-project>{{ projectLabel }}</span>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  configLabel: string;
  configTone: string;
  licenseLabel: string;
  licenseTone: string;
  projectLabel: string;
  runtimeLabel: string;
  runtimeTone: string;
  summary: string;
  title: string;
}>();
</script>
