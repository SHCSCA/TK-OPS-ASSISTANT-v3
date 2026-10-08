<template>
  <section class="ai-matrix">
    <header>
      <div>
        <span class="ai-eyebrow">能力契约 · 真实验证</span>
        <h3>{{ model.displayName }}</h3>
        <p>{{ model.modelId }} · {{ providerName }}</p>
      </div>
      <button
        class="ai-button is-primary"
        type="button"
        :disabled="busy"
        @click="$emit('check')"
      >
        运行真实小调用
      </button>
    </header>
    <table class="ai-data-table is-compact">
      <thead>
        <tr>
          <th>产品能力</th>
          <th>Provider 声明</th>
          <th>适配器接入</th>
          <th>真实小调用</th>
          <th>可用性</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="capability in capabilities" :key="capability.capabilityKey">
          <td>{{ capabilityLabel(capability.capabilityKey) }}</td>
          <td>{{ yesNo(capability.declaredSupported) }}</td>
          <td>{{ yesNo(capability.adapterSupported) }}</td>
          <td>{{ yesNo(capability.contractVerified) }}</td>
          <td>
            <span class="ai-status-chip" :class="`is-${capability.availability}`">
              {{ availabilityLabel(capability.availability) }}
            </span>
          </td>
        </tr>
        <tr v-if="capabilities.length === 0">
          <td colspan="5">尚未取得真实能力证据，请运行真实小调用。</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import type {
  ModelCapabilityListItemDto,
  ModelProfileDto
} from "@/types/runtime/ai-system";

import { capabilityLabel } from "../ai-config-helpers";

defineProps<{
  busy: boolean;
  capabilities: ModelCapabilityListItemDto[];
  model: ModelProfileDto;
  providerName: string;
}>();

defineEmits<{ check: [] }>();

function yesNo(value: boolean): string {
  return value ? "是" : "否";
}

function availabilityLabel(value: ModelCapabilityListItemDto["availability"]): string {
  return {
    available: "可用",
    unverified: "待验证",
    unavailable: "不可用"
  }[value];
}
</script>
