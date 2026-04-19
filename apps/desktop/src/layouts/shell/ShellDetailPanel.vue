<template>
  <div class="shell-detail-panel" :data-open="String(open)">
    <transition name="panel-fade" mode="out-in">
      <component :is="activeComponent" :closable="true" :context="context" @close="$emit('close')" />
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import AssetDetail from "@/components/shell/details/AssetDetail.vue";
import BindingDetail from "@/components/shell/details/BindingDetail.vue";
import ContextualDetail from "@/components/shell/details/ContextualDetail.vue";
import DetailContextRenderer from "@/components/shell/details/DetailContextRenderer.vue";
import LogDetail from "@/components/shell/details/LogDetail.vue";
import SystemStatusDetail from "@/components/shell/details/SystemStatusDetail.vue";
import type { DetailContext } from "@/stores/shell-ui";

const props = defineProps<{
  context: DetailContext;
  open: boolean;
}>();

defineEmits<{
  close: [];
}>();

const activeComponent = computed(() => {
  if (props.context.source === "route") {
    return DetailContextRenderer;
  }
  switch (props.context.mode) {
    case "settings":
      return SystemStatusDetail;
    case "asset":
      return AssetDetail;
    case "logs":
      return LogDetail;
    case "binding":
      return BindingDetail;
    case "hidden":
    case "contextual":
    default:
      return ContextualDetail;
  }
});
</script>

<style scoped>
.shell-detail-panel {
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.panel-fade-enter-active,
.panel-fade-leave-active {
  transition:
    opacity var(--motion-fast) var(--ease-standard),
    transform var(--motion-fast) var(--ease-standard);
}

.panel-fade-enter-from,
.panel-fade-leave-to {
  opacity: 0;
  transform: translateX(8px);
}
</style>
