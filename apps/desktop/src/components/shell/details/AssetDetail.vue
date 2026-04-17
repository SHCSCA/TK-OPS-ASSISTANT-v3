<template>
  <DetailContextRenderer :closable="closable" :context="context" @close="$emit('close')" />
</template>

<script setup lang="ts">
import DetailContextRenderer from "@/components/shell/details/DetailContextRenderer.vue";
import type { DetailContext } from "@/stores/shell-ui";

defineProps<{
  closable?: boolean;
  context: DetailContext;
}>();

defineEmits<{
  close: [];
}>();
</script>
