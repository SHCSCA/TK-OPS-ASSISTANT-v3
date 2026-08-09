<template>
  <div class="account-readiness-row">
    <span class="account-readiness-row__dot" :class="`is-${readinessTone(item)}`"></span>
    <span>
      <strong>{{ label }} · {{ readinessShortLabel(item) }}</strong>
      <small>{{ item.label }}</small>
    </span>
    <button
      v-if="item.logId"
      class="account-text-action"
      type="button"
      @click="openLog"
    >
      查看日志
    </button>
  </div>
</template>

<script setup lang="ts">
import type { AccountReadinessItemDto } from "@/types/runtime/accounts";

import { readinessShortLabel, readinessTone } from "../account-formatters";

const props = defineProps<{ item: AccountReadinessItemDto; label: string }>();
const emit = defineEmits<{ openLog: [logId: string] }>();

function openLog(): void {
  if (props.item.logId) emit("openLog", props.item.logId);
}
</script>
