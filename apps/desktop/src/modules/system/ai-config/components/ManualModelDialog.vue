<template>
  <div v-if="open" class="ai-modal-backdrop" @click.self="$emit('close')">
    <form
      class="ai-dialog ai-form-section"
      role="dialog"
      aria-modal="true"
      @submit.prevent="submit"
    >
      <header>
        <div>
          <span class="ai-eyebrow">真实模型登记</span>
          <h2>手动添加模型</h2>
          <p>只登记 Provider 实际提供的模型 ID；能力仍需独立验证。</p>
        </div>
      </header>
      <div v-if="errorMessage" class="ai-inline-feedback is-error">
        <span class="material-symbols-outlined">error</span>
        <span>{{ errorMessage }}</span>
        <button
          v-if="errorLogId"
          class="ai-button is-quiet"
          type="button"
          @click="$emit('openLog', errorLogId)"
        >
          查看日志
        </button>
      </div>
      <label>
        <span>Provider</span>
        <select v-model="providerProfileId">
          <option value="">选择 Provider</option>
          <option
            v-for="provider in providers"
            :key="provider.id"
            :value="provider.id"
          >
            {{ provider.name }}
          </option>
        </select>
      </label>
      <label>
        <span>模型 ID</span>
        <input v-model="modelId" maxlength="128" autocomplete="off" />
      </label>
      <label>
        <span>显示名称</span>
        <input v-model="displayName" maxlength="80" autocomplete="off" />
      </label>
      <label class="ai-toggle-row">
        <span>
          <strong>登记后启用模型</strong>
          <small>未通过能力验证前仍不能进入有效 Route。</small>
        </span>
        <input v-model="enabled" type="checkbox" />
      </label>
      <footer class="ai-detail-actions">
        <button
          class="ai-button is-secondary"
          type="button"
          :disabled="busy"
          @click="$emit('close')"
        >
          取消
        </button>
        <button
          class="ai-button is-primary"
          type="submit"
          :disabled="busy || !canSubmit"
        >
          {{ busy ? "正在登记…" : "登记真实模型" }}
        </button>
      </footer>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type {
  ModelCreateInput,
  ProviderDto
} from "@/types/runtime/ai-system";

const props = withDefaults(defineProps<{
  busy?: boolean;
  errorLogId?: string | null;
  errorMessage?: string | null;
  initialProviderId?: string | null;
  open: boolean;
  providers: ProviderDto[];
}>(), {
  busy: false,
  errorLogId: null,
  errorMessage: null,
  initialProviderId: null
});
const emit = defineEmits<{
  close: [];
  openLog: [logId: string];
  submit: [input: ModelCreateInput];
}>();

const providerProfileId = ref("");
const modelId = ref("");
const displayName = ref("");
const enabled = ref(true);
const canSubmit = computed(
  () =>
    Boolean(providerProfileId.value)
    && Boolean(modelId.value.trim())
    && Boolean(displayName.value.trim())
);

watch(
  () => [props.open, props.initialProviderId, props.providers] as const,
  ([open, initialProviderId]) => {
    if (!open) return;
    providerProfileId.value =
      initialProviderId
      ?? props.providers[0]?.id
      ?? "";
    modelId.value = "";
    displayName.value = "";
    enabled.value = true;
  }
);

function submit(): void {
  if (!canSubmit.value) return;
  emit("submit", {
    providerProfileId: providerProfileId.value,
    modelId: modelId.value.trim(),
    displayName: displayName.value.trim(),
    enabled: enabled.value
  });
}
</script>
