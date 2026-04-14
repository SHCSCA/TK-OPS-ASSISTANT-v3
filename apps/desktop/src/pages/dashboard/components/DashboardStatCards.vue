<template>
  <div class="stat-cards">
    <div class="stat-card">
      <p class="stat-card__label">总项目数</p>
      <h3 class="stat-card__value">{{ projectCount }}</h3>
      <div class="stat-card__trend stat-card__trend--neutral">
        <span>真实数据</span>
      </div>
    </div>
    <div class="stat-card">
      <p class="stat-card__label">今日 AI 任务</p>
      <h3 class="stat-card__value stat-card__value--muted">&mdash;</h3>
      <div class="stat-card__trend stat-card__trend--neutral">
        <span>待接入</span>
      </div>
    </div>
    <div class="stat-card">
      <p class="stat-card__label">视频处理量</p>
      <h3 class="stat-card__value stat-card__value--muted">&mdash;</h3>
      <div class="stat-card__trend stat-card__trend--neutral">
        <span>待接入</span>
      </div>
    </div>
    <div class="stat-card">
      <p class="stat-card__label">系统健康度</p>
      <h3 class="stat-card__value stat-card__value--muted">&mdash;</h3>
      <div class="stat-card__trend stat-card__trend--neutral">
        <span>待接入</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  projectCount: number;
}>();
</script>
