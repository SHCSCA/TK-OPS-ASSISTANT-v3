<template>
  <section class="sk-card" data-testid="knowledge-rules-panel">
    <header class="sk-card__header">
      <div>
        <p class="sk-eyebrow">独立知识库</p>
        <h2>使用规则</h2>
      </div>
      <span class="sk-revision">
        规则 v{{ cache.knowledge?.rulesVersion ?? 0 }}
      </span>
    </header>

    <p class="sk-card__hint">
      规则只作用于当前账号。对象结构会原样保存，不会跨账号复用。
    </p>

    <details class="sk-details sk-details--rules" :open="cache.rulesDirty">
      <summary>
        编辑规则
        <span v-if="cache.rulesDirty" class="sk-unsaved">未保存</span>
      </summary>
      <div class="sk-rules-grid">
        <label class="sk-field">
          <span>纳入规则 <small>JSON 对象</small></span>
          <textarea
            class="sk-code-input"
            :value="cache.rulesDraft.inclusionRules"
            rows="6"
            @input="update('inclusionRules', $event)"
          />
        </label>
        <label class="sk-field">
          <span>排除规则 <small>JSON 对象</small></span>
          <textarea
            class="sk-code-input"
            :value="cache.rulesDraft.exclusionRules"
            rows="6"
            @input="update('exclusionRules', $event)"
          />
        </label>
        <label class="sk-field">
          <span>引用策略 <small>JSON 对象</small></span>
          <textarea
            class="sk-code-input"
            :value="cache.rulesDraft.citationPolicy"
            rows="6"
            @input="update('citationPolicy', $event)"
          />
        </label>
      </div>
      <div class="sk-actions">
        <button
          class="sk-button sk-button--primary"
          type="button"
          :disabled="!cache.rulesDirty || Boolean(cache.busyKey)"
          @click="$emit('save')"
        >
          {{ cache.busyKey === "rules-save" ? "保存中…" : "保存规则" }}
        </button>
      </div>
    </details>
  </section>
</template>

<script setup lang="ts">
import type {
  AccountKnowledgeCache,
  KnowledgeRulesDraft
} from "./account-knowledge-types";

defineProps<{ cache: AccountKnowledgeCache }>();
const emit = defineEmits<{
  save: [];
  update: [field: keyof KnowledgeRulesDraft, value: string];
}>();

function update(field: keyof KnowledgeRulesDraft, event: Event): void {
  emit("update", field, (event.target as HTMLTextAreaElement).value);
}
</script>
