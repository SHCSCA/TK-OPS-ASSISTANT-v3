<template>
  <footer class="status-bar command-status-bar shell-status-bar">
    <span>{{ runtimeLabel }}</span>
    <span>{{ secondaryLabel }}</span>
    <span>{{ projectLabel }}</span>
    <span>{{ syncLabel }}</span>
  </footer>
</template>

<script setup lang="ts">
defineProps<{
  projectLabel: string;
  runtimeLabel: string;
  secondaryLabel: string;
  syncLabel: string;
}>();
</script>
