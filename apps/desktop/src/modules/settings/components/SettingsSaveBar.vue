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
          class="settings-page__button"
          type="button"
          data-action="save-settings"
          :disabled="isSystemSaving"
          @click="$emit('save-system')"
        >
          {{ isSystemSaving ? "保存系统配置中" : "保存系统配置" }}
        </button>
        <button
          v-if="capabilityDirty"
          class="dashboard-list__action"
          type="button"
          data-action="save-capabilities"
          :disabled="isCapabilitySaving"
          @click="$emit('save-capabilities')"
        >
          {{ isCapabilitySaving ? "保存能力策略中" : "保存能力策略" }}
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
    return "系统总线和能力策略都有未保存修改。";
  }
  if (props.systemDirty) {
    return "系统总线存在未保存修改。";
  }
  return "能力策略存在未保存修改。";
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
  border: 1px solid color-mix(in srgb, var(--brand-primary) 28%, var(--border-default));
  border-radius: 18px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--surface-secondary) 94%, transparent), color-mix(in srgb, var(--surface-tertiary) 92%, transparent)),
    radial-gradient(circle at top left, color-mix(in srgb, var(--brand-primary) 16%, transparent), transparent 28%);
  box-shadow: 0 18px 40px rgba(12, 18, 18, 0.16);
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
