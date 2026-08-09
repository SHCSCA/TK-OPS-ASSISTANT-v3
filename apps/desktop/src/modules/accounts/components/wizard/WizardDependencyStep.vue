<template>
  <div class="account-dependency-step" :class="{ 'is-ready': ready }">
    <span class="material-symbols-outlined" aria-hidden="true">
      {{ ready ? "check_circle" : icon }}
    </span>
    <div>
      <strong>{{ ready ? readyTitle : title }}</strong>
      <p>{{ ready ? readyDescription : description }}</p>
    </div>
    <button
      v-if="!ready"
      class="account-button is-secondary"
      type="button"
      @click="$emit('openDependency')"
    >
      {{ actionLabel }}
    </button>
    <button
      v-else
      class="account-button is-primary"
      type="button"
      @click="$emit('continue')"
    >
      继续
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  actionLabel: string;
  description: string;
  icon: string;
  ready: boolean;
  readyDescription: string;
  readyTitle: string;
  title: string;
}>();

defineEmits<{ continue: []; openDependency: [] }>();
</script>

