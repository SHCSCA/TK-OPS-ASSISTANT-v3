<template>
  <div class="empty-state-container" :class="`empty-state--${type}`">
    <div class="empty-state__visual">
      <div class="floating-orb">
        <span class="material-symbols-outlined">{{ icon }}</span>
      </div>
      <div class="glow-shadow"></div>
    </div>
    
    <div class="empty-state__content">
      <h2 class="empty-state__title">{{ title }}</h2>
      <p class="empty-state__description">{{ description }}</p>
      
      <div class="empty-state__actions">
        <slot name="actions">
          <button 
            v-if="actionLabel" 
            class="settings-page__button"
            @click="$emit('action')"
          >
            {{ actionLabel }}
          </button>
        </slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  icon?: string;
  title: string;
  description: string;
  actionLabel?: string;
  type?: 'info' | 'warning' | 'error';
}

withDefaults(defineProps<Props>(), {
  icon: 'database',
  type: 'info'
});

defineEmits(['action']);
</script>

<style scoped>
.empty-state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  text-align: center;
  min-height: 400px;
  width: 100%;
}

.empty-state__visual {
  position: relative;
  margin-bottom: 32px;
  perspective: 1000px;
}

.floating-orb {
  width: 100px;
  height: 100px;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  color: var(--brand-primary);
  box-shadow: var(--shadow-md);
  animation: float 6s ease-in-out infinite;
  transform-style: preserve-3d;
}

.floating-orb .material-symbols-outlined {
  font-size: 56px;
  filter: drop-shadow(0 0 10px rgba(0, 242, 234, 0.3));
}

.glow-shadow {
  position: absolute;
  bottom: -20px;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 10px;
  background: rgba(0, 0, 0, 0.1);
  filter: blur(8px);
  border-radius: 50%;
  animation: shadow-scale 6s ease-in-out infinite;
}

.empty-state__content {
  max-width: 480px;
}

.empty-state__title {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0 0 12px;
  letter-spacing: -0.02em;
}

.empty-state__description {
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin: 0 0 32px;
}

.empty-state__actions {
  display: flex;
  justify-content: center;
  gap: 16px;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) rotateX(5deg) rotateY(5deg);
  }
  50% {
    transform: translateY(-20px) rotateX(-5deg) rotateY(-10deg);
  }
}

@keyframes shadow-scale {
  0%, 100% {
    transform: translateX(-50%) scale(1);
    opacity: 0.2;
  }
  50% {
    transform: translateX(-50%) scale(0.7);
    opacity: 0.1;
  }
}

/* Theme specifics */
:root[data-theme="dark"] .floating-orb {
  background: var(--surface-secondary);
  border-color: var(--border-strong);
}

:root[data-theme="dark"] .glow-shadow {
  background: rgba(0, 242, 234, 0.15);
}
</style>
