<template>
  <form
    class="sk-form"
    data-testid="positioning-editor"
    @submit.prevent="emit('create')"
  >
    <div class="sk-editor-heading">
      <div>
        <strong>{{ editorTitle }}</strong>
        <p>{{ editorDescription }}</p>
      </div>
      <span v-if="sourceVersion" class="sk-pill sk-pill--draft">
        来源 v{{ sourceVersion }}
      </span>
    </div>

    <div class="sk-field-grid">
      <label class="sk-field">
        <span>目标受众</span>
        <input
          :value="cache.positioningDraft.audience"
          placeholder="例：准备出海的独立开发者"
          @input="update('audience', $event)"
        />
      </label>
      <label class="sk-field">
        <span>表达风格</span>
        <input
          :value="cache.positioningDraft.tone"
          placeholder="例：直接、克制、有证据"
          @input="update('tone', $event)"
        />
      </label>
    </div>
    <label class="sk-field">
      <span>内容支柱 <small>每行一个</small></span>
      <textarea
        :value="cache.positioningDraft.contentPillars"
        rows="3"
        placeholder="产品拆解&#10;增长实验"
        @input="update('contentPillars', $event)"
      />
    </label>
    <details class="sk-details">
      <summary>补充边界</summary>
      <div class="sk-field-grid">
        <label class="sk-field">
          <span>禁用主题</span>
          <textarea
            :value="cache.positioningDraft.prohibitedTopics"
            rows="3"
            placeholder="每行一个"
            @input="update('prohibitedTopics', $event)"
          />
        </label>
        <label class="sk-field">
          <span>发布约束</span>
          <textarea
            :value="cache.positioningDraft.publishingConstraints"
            rows="3"
            placeholder="需要遵守的发布边界"
            @input="update('publishingConstraints', $event)"
          />
        </label>
      </div>
    </details>
    <div class="sk-actions">
      <button
        class="sk-button sk-button--ghost"
        type="button"
        :disabled="saving"
        @click="emit('cancel')"
      >
        取消
      </button>
      <button
        class="sk-button sk-button--primary"
        type="submit"
        :disabled="Boolean(cache.busyKey)"
      >
        {{ saving ? "正在保存…" : submitLabel }}
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type {
  AccountKnowledgeCache,
  PositioningDraft
} from "./account-knowledge-types";

const props = defineProps<{ cache: AccountKnowledgeCache }>();
const emit = defineEmits<{
  cancel: [];
  create: [];
  update: [field: keyof PositioningDraft, value: string];
}>();

const sourceVersion = computed(() =>
  props.cache.positioningEditorMode.kind === "fork"
    ? props.cache.positioningEditorMode.sourceVersion
    : null
);
const editorTitle = computed(() =>
  sourceVersion.value
    ? `基于 v${sourceVersion.value} 修改`
    : "新建定位版本"
);
const editorDescription = computed(() =>
  sourceVersion.value
    ? "原版本保持不变，保存后生成新的草稿版本。"
    : "保存后生成新的草稿版本，不会自动启用。"
);
const submitLabel = computed(() =>
  sourceVersion.value ? "保存为新版本" : "保存草稿版本"
);
const saving = computed(() =>
  props.cache.busyKey === "positioning-create"
);

function update(field: keyof PositioningDraft, event: Event): void {
  emit("update", field, (event.target as HTMLInputElement).value);
}
</script>
