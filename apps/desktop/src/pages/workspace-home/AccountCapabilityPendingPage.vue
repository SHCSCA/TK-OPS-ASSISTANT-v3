<template>
  <main
    class="capability-pending"
    :data-state="migrationState"
    aria-live="polite"
  >
    <span class="material-symbols-outlined" aria-hidden="true">
      {{ icon }}
    </span>
    <div>
      <small>{{ stageLabel }}</small>
      <h1>{{ title }}</h1>
      <p>{{ restrictedMessage }}</p>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import type { AccountWorkspaceContextDto } from "@/types/runtime/accounts";

withDefaults(defineProps<{
  accountId?: string | null;
  workspaceContext?: AccountWorkspaceContextDto | null;
}>(), {
  accountId: null,
  workspaceContext: null,
});

const route = useRoute();
const title = computed(() =>
  typeof route.meta.title === "string" ? route.meta.title : "账号工作区"
);
const migrationState = computed(() =>
  route.meta.migrationState === "p2_pending"
    ? "p2_pending"
    : "p1_pending"
);
const stageLabel = computed(() =>
  migrationState.value === "p2_pending"
    ? "P2 交付阶段"
    : "P1 创作阶段"
);
const restrictedMessage = computed(() =>
  migrationState.value === "p2_pending"
    ? "当前账号边界已就绪，该交付能力尚未接入生产 Runtime，暂不可用。"
    : "当前账号边界已就绪，该创作能力尚未接入生产 Runtime，暂不可用。"
);
const icon = computed(() => {
  switch (route.meta.routeId) {
    case "account_script_topic":
      return "description";
    case "account_storyboard_planning":
      return "view_timeline";
    case "account_video_deconstruction":
      return "video_library";
    case "account_batch_production":
      return "deployed_code";
    case "account_content_library":
      return "inventory_2";
    case "account_media_toolbox":
      return "construction";
    case "account_publishing":
      return "send";
    case "account_review":
      return "monitoring";
    default:
      return "space_dashboard";
  }
});
</script>

<style scoped>
.capability-pending {
  align-items: center;
  background: var(--surface-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  color: var(--text-primary);
  display: flex;
  gap: var(--space-4);
  margin: min(18vh, 160px) auto 0;
  max-width: 520px;
  padding: var(--space-6);
}

.capability-pending > span {
  color: var(--brand-primary);
  font-size: 30px;
}

.capability-pending h1 {
  font: var(--font-title-md);
  margin: 0 0 var(--space-1);
}

.capability-pending small {
  color: var(--brand-primary);
  font: var(--font-caption);
  font-weight: 700;
}

.capability-pending p {
  color: var(--text-secondary);
  font: var(--font-body-sm);
  margin: 0;
}
</style>
