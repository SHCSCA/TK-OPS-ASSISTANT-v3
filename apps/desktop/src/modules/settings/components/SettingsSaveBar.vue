<template>
  <transition name="save-bar">
    <section v-if="visible" class="settings-save-bar">
      <div class="settings-save-bar__copy">
        <p class="detail-panel__label">待保存变更</p>
        <strong>{{ summary }}</strong>
      </div>
      <div class="settings-save-bar__actions">
        <button
          v-if="systemDirty"
          class="settings-save-bar__button"
          type="button"
          data-action="save-settings"
          :disabled="isSystemSaving"
          @click="$emit('save-system')"
        >
          {{ isSystemSaving ? "正在保存系统设置" : "保存系统设置" }}
        </button>
        <button
          v-if="capabilityDirty"
          class="settings-save-bar__button settings-save-bar__button--secondary"
          type="button"
          data-action="save-capabilities"
          :disabled="isCapabilitySaving"
          @click="$emit('save-capabilities')"
        >
          {{ isCapabilitySaving ? "正在保存能力矩阵" : "保存能力矩阵" }}
        </button>
      </div>
    </section>
  </transition>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  capabilityDirty: boolean;
  isCapabilitySaving: boolean;
  isSystemSaving: boolean;
  systemDirty: boolean;
  visible: boolean;
}>();

defineEmits<{
  (e: "save-capabilities"): void;
  (e: "save-system"): void;
}>();

const summary = computed(() => {
  if (props.systemDirty && props.capabilityDirty) {
    return "系统设置和能力矩阵都有未保存修改。";
  }
  if (props.systemDirty) {
    return "系统设置存在未保存修改。";
  }
  return "能力矩阵存在未保存修改。";
});
</script>

<style scoped>
.settings-save-bar {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border: 1px solid color-mix(in srgb, var(--brand-primary) 22%, var(--border-default));
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 96%, transparent);
}

.settings-save-bar__copy {
  display: grid;
  gap: 4px;
}

.settings-save-bar__copy strong {
  font-size: 14px;
}

.settings-save-bar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.settings-save-bar__button {
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid var(--brand-primary);
  border-radius: 8px;
  background: var(--brand-primary);
  color: #000;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.settings-save-bar__button--secondary {
  border-color: var(--border-default);
  background: transparent;
  color: var(--text-primary);
  font-weight: 600;
}

.settings-save-bar__button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.save-bar-enter-active,
.save-bar-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.save-bar-enter-from,
.save-bar-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 720px) {
  .settings-save-bar {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
