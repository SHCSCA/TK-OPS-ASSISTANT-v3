<template>
  <section class="system-bus-layout">
    <div class="system-bus-layout__main">
      <section class="system-card system-card--runtime">
        <div class="system-card__header">
          <div>
            <p class="detail-panel__label">运行与默认 AI</p>
            <h3>配置总线</h3>
          </div>
          <span class="system-card__badge">统一保存</span>
        </div>

        <div class="system-field-grid">
          <label class="settings-field">
            <span>运行模式</span>
            <select
              :value="form.runtime.mode"
              class="ui-select"
              data-field="runtime.mode"
              :disabled="disabled"
              @change="e => updateForm({ runtime: { mode: (e.target as HTMLSelectElement).value } })"
            >
              <option value="development">Development (调试)</option>
              <option value="production">Production (生产)</option>
            </select>
          </label>

          <label class="settings-field">
            <span>默认 AI 提供商</span>
            <select
              :value="form.ai.provider"
              class="ui-select"
              data-field="ai.provider"
              :disabled="disabled"
              @change="e => updateForm({ ai: { provider: (e.target as HTMLSelectElement).value } })"
            >
              <option value="" disabled>选择 Provider</option>
              <option v-for="p in providerOptions" :key="p.provider" :value="p.provider">
                {{ p.label }}
              </option>
            </select>
          </label>

          <label class="settings-field">
            <span>默认生成模型</span>
            <select
              :value="form.ai.model"
              class="ui-select"
              data-field="ai.model"
              :disabled="disabled || modelOptions.length === 0"
              @change="e => updateForm({ ai: { model: (e.target as HTMLSelectElement).value } })"
            >
              <option value="" disabled>{{ modelOptions.length === 0 ? "当前 Provider 暂无模型" : "选择模型" }}</option>
              <option v-for="m in modelOptions" :key="m.modelId" :value="m.modelId">
                {{ m.modelId }}
              </option>
            </select>
          </label>

          <label class="settings-field">
            <span>默认配音</span>
            <select
              :value="form.ai.voice"
              class="ui-select"
              data-field="ai.voice"
              :disabled="disabled"
              @change="e => updateForm({ ai: { voice: (e.target as HTMLSelectElement).value } })"
            >
              <option value="nova">Nova</option>
              <option value="alloy">Alloy</option>
            </select>
          </label>

          <label class="settings-field">
            <span>字幕生成模式</span>
            <select
              :value="form.ai.subtitleMode"
              class="ui-select"
              data-field="ai.subtitleMode"
              :disabled="disabled"
              @change="e => updateForm({ ai: { subtitleMode: (e.target as HTMLSelectElement).value } })"
            >
              <option value="balanced">平衡模式</option>
              <option value="precise">精确模式</option>
              <option value="fast">极速模式</option>
            </select>
          </label>

          <label class="settings-field">
            <span>日志级别</span>
            <select
              :value="form.logging.level"
              class="ui-select"
              data-field="logging.level"
              :disabled="disabled"
              @change="e => updateForm({ logging: { level: (e.target as HTMLSelectElement).value } })"
            >
              <option value="DEBUG">DEBUG (最详细)</option>
              <option value="INFO">INFO (推荐)</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </label>
        </div>
      </section>

      <section class="system-card system-directory-table">
        <div class="system-card__header">
          <div>
            <p class="detail-panel__label">本地路径</p>
            <h3>目录由系统选择器写入</h3>
          </div>
          <span class="system-card__badge">本机路径</span>
        </div>

        <div class="system-directory-table__rows">
          <article class="system-directory-row">
            <div>
              <strong>工作区根目录</strong>
              <span>项目数据、资产记录和模型配置的根目录。</span>
            </div>
            <Input :model-value="form.runtime.workspaceRoot" readonly />
            <Button variant="secondary" data-action="pick-workspace-root" :disabled="disabled" @click="$emit('pick-directory', 'runtime.workspaceRoot')">
              选择
            </Button>
          </article>

          <article class="system-directory-row">
            <div>
              <strong>缓存目录</strong>
              <span>模型缓存、资产预览和运行期临时文件。</span>
            </div>
            <Input :model-value="form.paths.cacheDir" readonly />
            <Button variant="secondary" data-action="pick-cache-dir" :disabled="disabled" @click="$emit('pick-directory', 'paths.cacheDir')">
              选择
            </Button>
          </article>

          <article class="system-directory-row">
            <div>
              <strong>导出目录</strong>
              <span>渲染结果和交付文件的默认位置。</span>
            </div>
            <Input :model-value="form.paths.exportDir" readonly />
            <Button variant="secondary" data-action="pick-export-dir" :disabled="disabled" @click="$emit('pick-directory', 'paths.exportDir')">
              选择
            </Button>
          </article>
        </div>
      </section>
    </div>

    <aside class="system-bus-layout__inspector">
      <section class="system-card system-card--inspector">
        <p class="detail-panel__label">Inspector</p>
        <h3>日志与缓存</h3>
        <p class="system-card__summary">
          常规运行配置在主区编辑，诊断和系统边界统一放到右上角详情抽屉。
        </p>

        <Button variant="secondary" data-action="pick-log-dir" :disabled="disabled" @click="$emit('open-log-directory')">
          <template #leading><span class="material-symbols-outlined">folder_open</span></template>
          打开日志所在目录
        </Button>

        <div class="cache-list">
          <article v-for="item in cacheItems" :key="item.key" class="cache-item">
            <div>
              <strong>{{ item.label }}</strong>
              <span>{{ item.size }}</span>
            </div>
            <Button
              variant="danger"
              size="sm"
              :disabled="disabled || clearingKey === item.key"
              @click="confirmClear(item.key, item.label)"
            >
              {{ clearingKey === item.key ? "清除中..." : "清除" }}
            </Button>
          </article>
        </div>

        <Button variant="danger" block :disabled="disabled || clearingKey === 'all'" @click="confirmClearAll">
          {{ clearingKey === "all" ? "清除中..." : "全部清除缓存" }}
        </Button>
      </section>
    </aside>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import Button from "@/components/ui/Button/Button.vue";
import Input from "@/components/ui/Input/Input.vue";
import type { AIModelCatalogItem, AIProviderCatalogItem, AppSettingsUpdateInput } from "@/types/runtime";

defineProps<{
  currentSection: string;
  form: AppSettingsUpdateInput;
  disabled: boolean;
  modelOptions: AIModelCatalogItem[];
  providerOptions: AIProviderCatalogItem[];
}>();

const emit = defineEmits<{
  (e: "update", patch: Partial<AppSettingsUpdateInput>): void;
  (e: "pick-directory", field: "runtime.workspaceRoot" | "paths.cacheDir" | "paths.exportDir" | "paths.logDir"): void;
  (e: "open-log-directory"): void;
}>();

const clearingKey = ref<string | null>(null);

const cacheItems = computed(() => [
  { key: "model", label: "模型缓存", size: "Runtime 尚未提供体积查询接口" },
  { key: "asset", label: "资产预览图", size: "暂存本地，请通过资源管理器清理" },
  { key: "render", label: "渲染缓存", size: "暂存本地，请通过资源管理器清理" }
]);

function updateForm(patch: Partial<AppSettingsUpdateInput>) {
  emit("update", patch);
}

function confirmClear(key: string, label: string) {
  if (!confirm(`确定清除「${label}」吗？此操作不可撤销。`)) {
    return;
  }
  clearingKey.value = key;
  window.setTimeout(() => {
    clearingKey.value = null;
  }, 1500);
}

function confirmClearAll() {
  if (!confirm("确定清除全部缓存吗？清除后可能需要重新下载模型和生成预览图。")) {
    return;
  }
  clearingKey.value = "all";
  window.setTimeout(() => {
    clearingKey.value = null;
  }, 2000);
}
</script>

<style scoped>
.system-bus-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 0.34fr);
  gap: var(--density-panel-gap);
  min-width: 0;
  align-items: start;
}

.system-bus-layout__main,
.system-bus-layout__inspector {
  display: grid;
  gap: var(--density-panel-gap);
  min-width: 0;
}

.system-card {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.system-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.system-card__header h3,
.system-card--inspector h3,
.system-card__summary {
  margin: 0;
}

.system-card__header h3,
.system-card--inspector h3 {
  font: var(--font-title-md);
  letter-spacing: 0;
}

.system-card__badge {
  flex: 0 0 auto;
  padding: 4px 8px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--surface-primary);
  color: var(--text-secondary);
  font: var(--font-caption);
}

.system-card__summary,
.cache-item span,
.system-directory-row span {
  color: var(--text-secondary);
  font: var(--font-body-sm);
  letter-spacing: 0;
}

.system-field-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}

.settings-field {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.settings-field span {
  color: var(--text-secondary);
  font: var(--font-caption);
}

.settings-field select {
  width: 100%;
  min-height: 38px;
  padding: 0 var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 96%, transparent);
  color: var(--text-primary);
  font: var(--font-body-md);
}

.system-directory-table__rows,
.cache-list {
  display: grid;
  gap: var(--space-2);
}

.system-directory-row {
  display: grid;
  grid-template-columns: minmax(150px, 0.42fr) minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
}

.system-directory-row > div,
.cache-item > div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.system-directory-row strong,
.cache-item strong {
  font: var(--font-title-sm);
  letter-spacing: 0;
}

.system-directory-row :deep(.ui-input-wrapper) {
  min-width: 0;
}

.system-directory-row :deep(input) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cache-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
}

@container settings-console (max-width: 1180px) {
  .system-bus-layout {
    grid-template-columns: 1fr;
  }

  .system-field-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@container settings-console (max-width: 720px) {
  .system-field-grid,
  .system-directory-row,
  .cache-item {
    grid-template-columns: 1fr;
  }
}
</style>
