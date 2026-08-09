<template>
  <form
    v-if="store.draft"
    class="ai-editor-form"
    @submit.prevent="store.saveDraft"
  >
    <header>
      <div>
        <span class="ai-eyebrow">
          {{ store.draft.mode === "create_profile" ? "新逻辑模板" : "不可变新版本" }}
        </span>
        <h3>{{ store.draft.name || "未命名 Prompt" }}</h3>
      </div>
      <button
        class="ai-icon-button"
        type="button"
        aria-label="关闭 Prompt 编辑器"
        @click="$emit('close')"
      >
        <span class="material-symbols-outlined">close</span>
      </button>
    </header>

    <div class="ai-form-grid">
      <label v-if="store.draft.mode === 'create_profile'">
        <span>稳定键</span>
        <input
          :value="store.draft.profileKey"
          maxlength="128"
          @input="updateText('profileKey', $event)"
        />
      </label>
      <label v-if="store.draft.mode === 'create_profile'">
        <span>产品能力</span>
        <select
          :value="store.draft.capabilityKey"
          @change="updateCapability($event)"
        >
          <option v-for="key in AI_CAPABILITY_KEYS" :key="key" :value="key">
            {{ capabilityLabel(key) }}
          </option>
        </select>
      </label>
      <label>
        <span>名称</span>
        <input
          :value="store.draft.name"
          maxlength="100"
          @input="updateText('name', $event)"
        />
      </label>
    </div>

    <label>
      <span>系统提示</span>
      <textarea
        :value="store.draft.systemPrompt"
        rows="7"
        @input="updateText('systemPrompt', $event)"
      />
    </label>
    <label>
      <span>任务模板</span>
      <textarea
        :value="store.draft.taskTemplate"
        rows="7"
        @input="updateText('taskTemplate', $event)"
      />
    </label>
    <div class="ai-form-grid">
      <label>
        <span>变量 Schema</span>
        <textarea
          class="is-code"
          :value="store.draft.variablesSchema"
          rows="8"
          @input="updateText('variablesSchema', $event)"
        />
      </label>
      <label>
        <span>输出 Schema</span>
        <textarea
          class="is-code"
          :value="store.draft.outputSchema"
          rows="8"
          @input="updateText('outputSchema', $event)"
        />
      </label>
    </div>
    <label>
      <span>视觉风格前缀</span>
      <textarea
        :value="store.draft.visualStylePrefix"
        rows="3"
        @input="updateText('visualStylePrefix', $event)"
      />
    </label>
    <label>
      <span>安全约束</span>
      <textarea
        class="is-code"
        :value="store.draft.safetyConstraints"
        rows="6"
        @input="updateText('safetyConstraints', $event)"
      />
    </label>

    <footer class="ai-detail-actions">
      <span>保存会创建新版本，不会覆盖已激活正文。</span>
      <button
        class="ai-button is-primary"
        type="submit"
        :disabled="Boolean(store.busyKey)"
      >
        {{ store.busyKey ? "保存中…" : "创建版本" }}
      </button>
    </footer>
  </form>
</template>

<script setup lang="ts">
import {
  AI_CAPABILITY_KEYS,
  type AICapabilityKey
} from "@/types/runtime/ai-system";

import { capabilityLabel } from "../ai-config-helpers";
import type { PromptEditorDraft } from "../ai-config-types";
import { usePromptConfigStore } from "../prompt-config-store";

defineEmits<{ close: [] }>();

const store = usePromptConfigStore();

function updateText(
  field: Exclude<keyof PromptEditorDraft, "capabilityKey" | "createdFromVersion" | "mode">,
  event: Event
): void {
  store.updateDraft(field, (event.target as HTMLInputElement).value);
}

function updateCapability(event: Event): void {
  store.updateDraft(
    "capabilityKey",
    (event.target as HTMLSelectElement).value as AICapabilityKey
  );
}
</script>
