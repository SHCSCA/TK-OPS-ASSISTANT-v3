<template>
  <form class="recipe-editor" @submit.prevent="$emit('save')">
    <header>
      <div>
        <span class="recipe-eyebrow">账号不可变版本</span>
        <h3>{{ cache.draft.name || "新 AI Recipe" }}</h3>
      </div>
      <button
        class="recipe-icon-button"
        type="button"
        aria-label="关闭 AI Recipe 编辑器"
        @click="$emit('close')"
      >
        <span class="material-symbols-outlined">close</span>
      </button>
    </header>

    <label>
      <span>名称</span>
      <input
        :value="cache.draft.name"
        maxlength="100"
        @input="update('name', $event)"
      />
    </label>
    <div class="recipe-form-grid">
      <label>
        <span>合成模板 <small>可选</small></span>
        <select
          :value="cache.draft.compositionTemplateRef"
          @change="update('compositionTemplateRef', $event)"
        >
          <option value="">继承系统默认</option>
          <option
            v-for="template in cache.templates"
            :key="template.templateKey"
            :value="template.activeVersionId ?? ''"
          >
            {{ template.name }} · v{{ template.activeVersion }}
          </option>
        </select>
      </label>
      <label>
        <span>音色引用 <small>可选</small></span>
        <input
          :value="cache.draft.voiceProfileRef"
          @input="update('voiceProfileRef', $event)"
        />
      </label>
    </div>
    <div class="recipe-form-grid">
      <label>
        <span>Route 覆盖</span>
        <textarea
          :value="cache.draft.routeOverrides"
          rows="7"
          @input="update('routeOverrides', $event)"
        />
      </label>
      <label>
        <span>视觉风格</span>
        <textarea
          :value="cache.draft.visualStyle"
          rows="7"
          @input="update('visualStyle', $event)"
        />
      </label>
      <label>
        <span>成本策略</span>
        <textarea
          :value="cache.draft.costPolicy"
          rows="7"
          @input="update('costPolicy', $event)"
        />
      </label>
      <label>
        <span>回退策略</span>
        <textarea
          :value="cache.draft.fallbackPolicy"
          rows="7"
          @input="update('fallbackPolicy', $event)"
        />
      </label>
    </div>
    <p>
      Recipe 只保存系统对象引用与账号覆盖，不保存密钥、Base URL 或完整 Prompt。
    </p>
    <footer>
      <button
        class="recipe-button is-primary"
        type="submit"
        :disabled="Boolean(cache.busyKey)"
      >
        {{ cache.busyKey ? "保存中…" : "创建 Recipe 版本" }}
      </button>
    </footer>
  </form>
</template>

<script setup lang="ts">
import type {
  AccountAIRecipeCache,
  AccountAIRecipeDraft
} from "../account-ai-recipe-types";
import { useAccountAIRecipeStore } from "../account-ai-recipe-store";

const props = defineProps<{
  accountId: string;
  cache: AccountAIRecipeCache;
}>();

defineEmits<{ close: []; save: [] }>();
const store = useAccountAIRecipeStore();

function update(field: keyof AccountAIRecipeDraft, event: Event): void {
  const value = (event.target as HTMLInputElement).value;
  store.updateDraft(props.accountId, field, value);
}
</script>
