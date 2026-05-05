<template>
  <Teleport to="body">
    <TransitionGroup
      name="toast-slide"
      tag="div"
      class="toast-container"
      v-if="toast.items.length"
    >
      <div
        v-for="item in toast.items"
        :key="item.id"
        class="toast-wrapper"
        @click="toast.dismiss(item.id)"
      >
        <Toast :title="item.title" :tone="item.tone">{{ item.message }}</Toast>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import Toast from "./Toast.vue";
import { useToast } from "@/composables/useToast";

const toast = useToast();
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: var(--space-4);
  right: var(--space-4);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: 400px;
  pointer-events: none;
}

.toast-wrapper {
  pointer-events: auto;
  cursor: pointer;
}

.toast-slide-enter-active {
  transition: all var(--motion-default) var(--ease-spring);
}

.toast-slide-leave-active {
  transition: all 200ms ease;
}

.toast-slide-enter-from {
  opacity: 0;
  transform: translateX(60px);
}

.toast-slide-leave-to {
  opacity: 0;
  transform: translateX(60px) scale(0.95);
}

.toast-slide-move {
  transition: transform 200ms ease;
}
</style>
