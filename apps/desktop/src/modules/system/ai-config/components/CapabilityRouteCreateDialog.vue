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
          <span class="ai-eyebrow">首次 Route</span>
          <h2>新建能力 Route</h2>
          <p>首条写入使用修订 0；模型、回退和 Prompt 在同一次请求中保存。</p>
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
        <span>产品能力</span>
        <select v-model="capabilityKey">
          <option
            v-for="option in options"
            :key="option.capabilityKey"
            :value="option.capabilityKey"
          >
            {{ option.label }}
          </option>
        </select>
      </label>
      <div
        v-if="selectedOption && selectedOption.models.length === 0"
        class="ai-inline-feedback is-warning"
      >
        <span class="material-symbols-outlined">link_off</span>
        <span>此能力暂无通过三重验证的模型，可先创建禁用 Route。</span>
      </div>
      <label>
        <span>主模型</span>
        <select v-model="primaryModelProfileId">
          <option value="">暂不绑定</option>
          <option
            v-for="model in selectedOption?.models ?? []"
            :key="model.id"
            :value="model.id"
          >
            {{ model.displayName }} · {{ model.modelId }}
          </option>
        </select>
      </label>
      <label>
        <span>回退模型</span>
        <select v-model="fallbackModelProfileId">
          <option value="">不使用回退</option>
          <option
            v-for="model in fallbackModels"
            :key="model.id"
            :value="model.id"
          >
            {{ model.displayName }} · {{ model.modelId }}
          </option>
        </select>
      </label>
      <label>
        <span>Prompt</span>
        <select v-model="promptProfileId">
          <option value="">暂不绑定</option>
          <option
            v-for="prompt in selectedOption?.prompts ?? []"
            :key="prompt.profileKey"
            :value="prompt.activeVersionId ?? ''"
          >
            {{ prompt.name }} · v{{ prompt.activeVersion }}
          </option>
        </select>
      </label>
      <label class="ai-toggle-row">
        <span>
          <strong>立即启用</strong>
          <small>仅当主模型依赖完整时才允许启用。</small>
        </span>
        <input
          v-model="enabled"
          type="checkbox"
          :disabled="!primaryModelProfileId"
        />
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
          :disabled="busy || !selectedOption"
        >
          {{ busy ? "正在创建…" : "创建 Route" }}
        </button>
      </footer>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type {
  AICapabilityKey,
  CapabilityRouteInput,
  ModelProfileDto,
  PromptProfileDto
} from "@/types/runtime/ai-system";

type CapabilityRouteCreateOption = {
  capabilityKey: AICapabilityKey;
  label: string;
  models: ModelProfileDto[];
  prompts: PromptProfileDto[];
};

const props = withDefaults(defineProps<{
  busy?: boolean;
  errorLogId?: string | null;
  errorMessage?: string | null;
  open: boolean;
  options: CapabilityRouteCreateOption[];
}>(), {
  busy: false,
  errorLogId: null,
  errorMessage: null
});
const emit = defineEmits<{
  close: [];
  openLog: [logId: string];
  submit: [
    capabilityKey: AICapabilityKey,
    input: CapabilityRouteInput
  ];
}>();

const capabilityKey = ref<AICapabilityKey | "">("");
const primaryModelProfileId = ref("");
const fallbackModelProfileId = ref("");
const promptProfileId = ref("");
const enabled = ref(false);
const selectedOption = computed(
  () =>
    props.options.find(
      (option) => option.capabilityKey === capabilityKey.value
    )
    ?? null
);
const fallbackModels = computed(
  () =>
    selectedOption.value?.models.filter(
      (model) => model.id !== primaryModelProfileId.value
    )
    ?? []
);

watch(
  () => [props.open, props.options] as const,
  ([open]) => {
    if (!open) return;
    capabilityKey.value = props.options[0]?.capabilityKey ?? "";
    resetReferences();
  }
);

watch(capabilityKey, resetReferences);

function resetReferences(): void {
  primaryModelProfileId.value = "";
  fallbackModelProfileId.value = "";
  promptProfileId.value = "";
  enabled.value = false;
}

function submit(): void {
  if (!capabilityKey.value) return;
  emit("submit", capabilityKey.value, {
    primaryModelProfileId: primaryModelProfileId.value || null,
    fallbackModelProfileId: fallbackModelProfileId.value || null,
    promptProfileId: promptProfileId.value || null,
    enabled: enabled.value
  });
}
</script>
