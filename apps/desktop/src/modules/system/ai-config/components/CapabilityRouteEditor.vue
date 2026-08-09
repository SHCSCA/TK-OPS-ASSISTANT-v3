<template>
  <aside class="ai-detail-panel ai-route-editor">
    <header>
      <div>
        <span class="ai-eyebrow">原子 Route</span>
        <h3>{{ capabilityLabel(route.capabilityKey) }}</h3>
      </div>
      <span class="ai-status-chip" :class="`is-${route.validationStatus}`">
        {{ route.validationStatus }}
      </span>
    </header>

    <div
      v-if="eligibleModels.length === 0"
      class="ai-inline-feedback is-warning"
    >
      <span class="material-symbols-outlined">link_off</span>
      <span>没有通过 Provider、适配器和契约三重验证的模型。</span>
    </div>

    <div class="ai-form-section">
      <label>
        <span>主模型</span>
        <select v-model="draft.primaryModelProfileId">
          <option value="">未配置</option>
          <option v-for="model in eligibleModels" :key="model.id" :value="model.id">
            {{ model.displayName }} · {{ model.modelId }}
          </option>
        </select>
      </label>
      <label>
        <span>回退模型</span>
        <select v-model="draft.fallbackModelProfileId">
          <option value="">不使用回退</option>
          <option v-for="model in fallbackModels" :key="model.id" :value="model.id">
            {{ model.displayName }} · {{ model.modelId }}
          </option>
        </select>
      </label>
      <label>
        <span>Prompt</span>
        <select v-model="draft.promptProfileId">
          <option value="">不绑定 Prompt</option>
          <option
            v-for="prompt in prompts"
            :key="prompt.profileKey"
            :value="prompt.activeVersionId ?? ''"
          >
            {{ prompt.name }} · v{{ prompt.activeVersion }}
          </option>
        </select>
      </label>
      <label class="ai-toggle-row">
        <span>
          <strong>启用此 Route</strong>
          <small>不完整或无效配置仍会被 Runtime 拒绝。</small>
        </span>
        <input v-model="draft.enabled" type="checkbox" />
      </label>
    </div>

    <ul v-if="route.validationIssues.length" class="ai-issue-list">
      <li v-for="(issue, index) in route.validationIssues" :key="`${issue.code}-${index}`">
        <strong>{{ issue.code }}</strong>
        <span>{{ issue.message || "请根据字段提示修复。" }}</span>
      </li>
    </ul>

    <footer class="ai-detail-actions">
      <button
        class="ai-button is-secondary"
        type="button"
        :disabled="busy"
        @click="$emit('validate')"
      >
        重新验证
      </button>
      <button
        class="ai-button is-primary"
        type="button"
        :disabled="busy || (draft.enabled && eligibleModels.length === 0)"
        @click="save"
      >
        原子保存 Route
      </button>
    </footer>
  </aside>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from "vue";

import type {
  CapabilityRouteDto,
  CapabilityRouteInput,
  ModelProfileDto,
  PromptProfileDto
} from "@/types/runtime/ai-system";

import { capabilityLabel } from "../ai-config-helpers";
import type { RouteEditorDraft } from "../ai-config-types";

const props = defineProps<{
  busy: boolean;
  eligibleModels: ModelProfileDto[];
  prompts: PromptProfileDto[];
  route: CapabilityRouteDto;
}>();
const emit = defineEmits<{
  save: [input: CapabilityRouteInput];
  validate: [];
}>();

const draft = reactive<RouteEditorDraft>(fromRoute(props.route));
watch(
  () => props.route,
  (route) => Object.assign(draft, fromRoute(route)),
  { deep: true }
);

const fallbackModels = computed(() =>
  props.eligibleModels.filter(
    (model) => model.id !== draft.primaryModelProfileId
  )
);

function save(): void {
  emit("save", {
    primaryModelProfileId: draft.primaryModelProfileId || null,
    fallbackModelProfileId: draft.fallbackModelProfileId || null,
    promptProfileId: draft.promptProfileId || null,
    enabled: draft.enabled
  });
}

function fromRoute(route: CapabilityRouteDto): RouteEditorDraft {
  return {
    primaryModelProfileId: route.primaryModelProfileId ?? "",
    fallbackModelProfileId: route.fallbackModelProfileId ?? "",
    promptProfileId: route.promptProfileId ?? "",
    enabled: route.enabled
  };
}
</script>
