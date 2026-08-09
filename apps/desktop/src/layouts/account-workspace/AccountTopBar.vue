<template>
  <header class="account-top-bar">
    <div>
      <h1>{{ title }}</h1>
      <p v-if="accountName">{{ accountName }}</p>
    </div>
    <div class="account-top-bar__status">
      <span :data-tone="runtimeTone">
        <i aria-hidden="true" />
        {{ runtimeLabel }}
      </span>
      <button
        type="button"
        aria-controls="account-context-detail-panel"
        :aria-expanded="detailsOpen"
        aria-label="查看当前账号详情"
        :disabled="!detailsAvailable"
        @click="emit('openDetails')"
      >
        <span class="material-symbols-outlined">dock_to_right</span>
      </button>
      <button type="button" :aria-label="themeActionLabel" @click="emit('toggleTheme')">
        <span class="material-symbols-outlined">{{ themeIcon }}</span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  accountName: string | null;
  detailsAvailable: boolean;
  detailsOpen: boolean;
  runtimeLabel: string;
  runtimeTone: "online" | "loading" | "offline" | "idle";
  themeActionLabel: string;
  themeIcon: string;
  title: string;
}>();

const emit = defineEmits<{
  openDetails: [];
  toggleTheme: [];
}>();
</script>
