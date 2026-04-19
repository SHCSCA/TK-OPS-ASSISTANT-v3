<template>
  <div class="template-editor">
    <div class="editor-section">
      <label class="section-label">角色设定（Agent Role）</label>
      <input 
        :value="item.agentRole"
        type="text"
        class="ui-input-field"
        placeholder="例如：资深短视频脚本策划"
        @input="e => update('agentRole', (e.target as HTMLInputElement).value)"
      />
    </div>

    <div class="editor-section">
      <label class="section-label">系统 Prompt</label>
      <textarea 
        :value="item.systemPrompt"
        class="ui-input-field textarea"
        rows="4"
        placeholder="输入给 AI 的系统级指令..."
        @input="e => update('systemPrompt', (e.target as HTMLTextAreaElement).value)"
      />
    </div>

    <div class="editor-section">
      <label class="section-label">用户 Prompt 模板</label>
      <div class="template-wrapper">
        <textarea 
          :value="item.userPromptTemplate"
          class="ui-input-field textarea"
          rows="6"
          placeholder="使用 {{variable}} 定义可替换变量..."
          @input="e => update('userPromptTemplate', (e.target as HTMLTextAreaElement).value)"
        />
        <div class="variables-hint">
          <span>可用变量：</span>
          <div class="variable-tags">
            <Chip 
              v-for="v in item.variables" 
              :key="v" 
              size="sm" 
              variant="brand"
              class="var-chip"
              clickable
              @click="insertVariable(v)"
              v-text="'{{' + v + '}}'"
            />
          </div>
        </div>
      </div>
    </div>

    <footer class="editor-actions">
      <Button variant="ghost" size="sm" @click="$emit('reset')">恢复默认</Button>
      <Button variant="primary" size="sm" @click="$emit('save')">保存模板</Button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import type { PromptEditorState } from "../types";
import Button from "@/components/ui/Button/Button.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const props = defineProps<{
  item: PromptEditorState;
}>();

const emit = defineEmits<{
  (e: "update", patch: Partial<PromptEditorState> & { capabilityId: string }): void;
  (e: "reset"): void;
  (e: "save"): void;
}>();

function update(field: keyof PromptEditorState, value: string) {
  emit("update", { capabilityId: props.item.capabilityId, [field]: value });
}

function insertVariable(v: string) {
  const tag = `{{${v}}}`;
  const newTemplate = props.item.userPromptTemplate + tag;
  update("userPromptTemplate", newTemplate);
}
</script>

<style scoped>
.template-editor {
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  background: var(--color-bg-surface);
}

.editor-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.section-label {
  font: var(--font-title-sm);
  color: var(--color-text-secondary);
}

.ui-input-field {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font: var(--font-body-md);
  outline: none;
}

.ui-input-field.textarea {
  height: auto;
  padding: 12px;
  resize: vertical;
  font-family: var(--font-family-mono);
  font-size: 13px;
  line-height: 1.6;
}

.template-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.variables-hint {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.variable-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.var-chip {
  font-family: var(--font-family-mono);
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-2);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border-subtle);
}
</style>
