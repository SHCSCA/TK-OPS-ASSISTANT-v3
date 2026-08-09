<template>
  <aside
    v-if="message"
    class="legacy-route-notice"
    role="status"
    aria-live="polite"
    data-testid="legacy-route-notice"
  >
    <span class="material-symbols-outlined" aria-hidden="true">
      move_up
    </span>
    <p>{{ message }}</p>
    <button type="button" aria-label="关闭迁移提示" @click="emit('dismiss')">
      <span class="material-symbols-outlined" aria-hidden="true">
        close
      </span>
    </button>
  </aside>
</template>

<script setup lang="ts">
defineProps<{
  message: string | null;
}>();

const emit = defineEmits<{
  dismiss: [];
}>();
</script>
