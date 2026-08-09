<template>
  <div class="account-detail-item">
    <span>{{ label }}</span>
    <strong>{{ value }}</strong>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string; value: string }>();
</script>

