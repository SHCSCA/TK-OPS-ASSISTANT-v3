<template>
  <aside class="shell-detail-panel">
    <transition name="panel-fade" mode="out-in">
      <component
        :is="activeComponent"
        v-bind="componentProps"
      />
    </transition>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import SystemStatusDetail from '@/components/shell/details/SystemStatusDetail.vue';
import ContextualDetail from '@/components/shell/details/ContextualDetail.vue';
import AssetDetail from '@/components/shell/details/AssetDetail.vue';
import LogDetail from '@/components/shell/details/LogDetail.vue';
import BindingDetail from '@/components/shell/details/BindingDetail.vue';

const props = defineProps<{
  mode: 'hidden' | 'contextual' | 'asset' | 'logs' | 'binding' | 'settings';
  configStatusLabel: string;
  licenseLabel: string;
  maskedCode: string;
  projectName: string;
  projectStatus: string;
  runtimeLabel: string;
  runtimeVersion: string;
}>();

const activeComponent = computed(() => {
  switch (props.mode) {
    case 'settings': return SystemStatusDetail;
    case 'contextual': return ContextualDetail;
    case 'asset': return AssetDetail;
    case 'logs': return LogDetail;
    case 'binding': return BindingDetail;
    default: return ContextualDetail;
  }
});

const componentProps = computed(() => {
  if (props.mode === 'settings') {
    return {
      configStatusLabel: props.configStatusLabel,
      licenseLabel: props.licenseLabel,
      maskedCode: props.maskedCode,
      projectName: props.projectName,
      projectStatus: props.projectStatus,
      runtimeLabel: props.runtimeLabel,
      runtimeVersion: props.runtimeVersion
    };
  }
  return {};
});
</script>

<style scoped>
.shell-detail-panel {
  background: var(--glass-bg);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  width: var(--detail-panel-width);
  box-shadow: var(--shadow-md);
  height: 100%;
  overflow-y: auto;
  color: var(--text-primary);
}

.panel-fade-enter-active,
.panel-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.panel-fade-enter-from {
  opacity: 0;
  transform: translateY(4px);
}

.panel-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
