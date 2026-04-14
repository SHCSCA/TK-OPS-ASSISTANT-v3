<template>
  <footer class="shell-status-bar">
    <span>{{ runtimeLabel }}</span>
    <span>{{ projectLabel }}</span>
    <span>{{ syncLabel }}</span>
  </footer>
</template>

<script setup lang="ts">
defineProps<{
  projectLabel: string;
  runtimeLabel: string;
  syncLabel: string;
}>();
</script>
