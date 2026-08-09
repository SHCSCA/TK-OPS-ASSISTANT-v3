<template>
  <div class="account-readiness-cell">
    <span
      v-for="item in items"
      :key="item.key"
      class="account-readiness-dot"
      :class="`is-${readinessTone(item.value)}`"
      :title="`${item.label}：${readinessShortLabel(item.value)}`"
    >
      <span aria-hidden="true"></span>
      {{ item.label }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { AccountReadinessDto } from "@/types/runtime/accounts";

import { readinessShortLabel, readinessTone } from "../account-formatters";

const props = defineProps<{ readiness: AccountReadinessDto }>();

const items = computed(() => [
  { key: "connection", label: "连接", value: props.readiness.connection },
  { key: "knowledge", label: "知识", value: props.readiness.knowledge },
  { key: "ai", label: "AI", value: props.readiness.ai }
]);
</script>

