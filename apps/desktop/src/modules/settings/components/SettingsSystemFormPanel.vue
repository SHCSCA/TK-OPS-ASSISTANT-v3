<template>
  <section class="settings-workspace-panel" data-testid="settings-system-panel">
    <div class="settings-workspace-panel__header">
      <div>
        <p class="detail-panel__label">系统总线</p>
        <h2>Runtime 与默认项</h2>
        <p class="workspace-page__summary">
          运行模式、路径和默认 AI 项都从配置总线读写，不再拆成散落的本地表单。
        </p>
      </div>
      <span v-if="disabled" class="settings-workspace-panel__state">当前只读</span>
    </div>

    <div v-if="disabled" class="settings-workspace-panel__notice">
      当前系统配置暂不可编辑，请等待配置加载或保存结束后再操作。
    </div>

    <div class="settings-system-grid">
      <section class="settings-card">
        <h3>Runtime</h3>

        <label class="settings-field">
          <span>运行模式</span>
          <select v-model="form.runtime.mode" data-field="runtime.mode" :disabled="disabled">
            <option v-for="option in runtimeModeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <label class="settings-field">
          <span>工作区根目录</span>
          <div class="settings-picker-field">
            <input
              :value="form.runtime.workspaceRoot"
              data-field="runtime.workspaceRoot"
              :disabled="disabled"
              readonly
              :title="form.runtime.workspaceRoot"
            />
            <button
              class="settings-workspace-panel__button"
              type="button"
              data-action="pick-workspace-root"
              :disabled="disabled"
              @click="$emit('pick-directory', 'runtime.workspaceRoot')"
            >
              选择目录
            </button>
          </div>
        </label>
      </section>

      <section class="settings-card">
        <h3>路径</h3>

        <label class="settings-field">
          <span>缓存目录</span>
          <div class="settings-picker-field">
            <input
              :value="form.paths.cacheDir"
              data-field="paths.cacheDir"
              :disabled="disabled"
              readonly
              :title="form.paths.cacheDir"
            />
            <button
              class="settings-workspace-panel__button"
              type="button"
              data-action="pick-cache-dir"
              :disabled="disabled"
              @click="$emit('pick-directory', 'paths.cacheDir')"
            >
              选择目录
            </button>
          </div>
        </label>

        <label class="settings-field">
          <span>导出目录</span>
          <div class="settings-picker-field">
            <input
              :value="form.paths.exportDir"
              data-field="paths.exportDir"
              :disabled="disabled"
              readonly
              :title="form.paths.exportDir"
            />
            <button
              class="settings-workspace-panel__button"
              type="button"
              data-action="pick-export-dir"
              :disabled="disabled"
              @click="$emit('pick-directory', 'paths.exportDir')"
            >
              选择目录
            </button>
          </div>
        </label>

        <label class="settings-field">
          <span>日志目录</span>
          <div class="settings-picker-field">
            <input
              :value="form.paths.logDir"
              data-field="paths.logDir"
              :disabled="disabled"
              readonly
              :title="form.paths.logDir"
            />
            <button
              class="settings-workspace-panel__button"
              type="button"
              data-action="pick-log-dir"
              :disabled="disabled"
              @click="$emit('pick-directory', 'paths.logDir')"
            >
              选择目录
            </button>
          </div>
        </label>
      </section>

      <section class="settings-card">
        <h3>日志</h3>
        <label class="settings-field">
          <span>日志级别</span>
          <select v-model="form.logging.level" data-field="logging.level" :disabled="disabled">
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>
        </label>
      </section>

      <section class="settings-card">
        <h3>AI 默认项</h3>

        <label class="settings-field">
          <span>默认 Provider</span>
          <select v-model="form.ai.provider" data-field="ai.provider" :disabled="disabled">
            <option value="">请选择 Provider</option>
            <option v-for="provider in providerOptions" :key="provider.provider" :value="provider.provider">
              {{ provider.label }}
            </option>
          </select>
        </label>

        <label class="settings-field">
          <span>默认模型</span>
          <select v-model="form.ai.model" data-field="ai.model" :disabled="disabled || modelOptions.length === 0">
            <option value="">{{ modelOptions.length === 0 ? "先选择 Provider" : "请选择模型" }}</option>
            <option v-for="model in modelOptions" :key="model.modelId" :value="model.modelId">
              {{ model.displayName }}
            </option>
          </select>
        </label>

        <label class="settings-field">
          <span>默认音色</span>
          <select v-model="form.ai.voice" data-field="ai.voice" :disabled="disabled">
            <option v-for="option in voiceOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <label class="settings-field">
          <span>字幕模式</span>
          <select v-model="form.ai.subtitleMode" data-field="ai.subtitleMode" :disabled="disabled">
            <option v-for="option in subtitleModeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { AIModelCatalogItem, AIProviderCatalogItem, AppSettingsUpdateInput } from "@/types/runtime";

defineProps<{
  disabled: boolean;
  form: AppSettingsUpdateInput;
  modelOptions: AIModelCatalogItem[];
  providerOptions: AIProviderCatalogItem[];
}>();

defineEmits<{
  (e: "pick-directory", field: "runtime.workspaceRoot" | "paths.cacheDir" | "paths.exportDir" | "paths.logDir"): void;
}>();

const runtimeModeOptions = [
  { value: "development", label: "开发模式" },
  { value: "production", label: "生产模式" },
  { value: "test", label: "测试模式" }
];

const voiceOptions = [
  { value: "alloy", label: "Alloy" },
  { value: "nova", label: "Nova" },
  { value: "shimmer", label: "Shimmer" },
  { value: "echo", label: "Echo" }
];

const subtitleModeOptions = [
  { value: "balanced", label: "平衡模式" },
  { value: "precise", label: "精确模式" },
  { value: "fast", label: "极速模式" }
];
</script>

<style scoped>
.settings-workspace-panel {
  display: grid;
  gap: 16px;
}

.settings-workspace-panel__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.settings-workspace-panel__header h2,
.settings-card h3 {
  margin: 0;
}

.settings-workspace-panel__state {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid var(--border-default);
  border-radius: 999px;
  color: var(--text-secondary);
  font-size: 12px;
}

.settings-workspace-panel__notice {
  padding: 12px 14px;
  border: 1px solid color-mix(in srgb, var(--status-warning) 30%, var(--border-default));
  border-radius: 8px;
  background: color-mix(in srgb, var(--status-warning) 8%, var(--surface-secondary));
  color: var(--text-primary);
}

.settings-system-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.settings-card {
  display: grid;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.settings-field {
  display: grid;
  gap: 8px;
}

.settings-field span {
  color: var(--text-secondary);
  font-size: 12px;
}

.settings-field input,
.settings-field select {
  width: 100%;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 96%, transparent);
  color: var(--text-primary);
  font: inherit;
}

.settings-picker-field {
  display: grid;
  gap: 10px;
  grid-template-columns: minmax(0, 1fr) auto;
  min-width: 0;
}

.settings-picker-field input {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.settings-workspace-panel__button {
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  cursor: pointer;
}

.settings-workspace-panel__button:disabled,
.settings-field input:disabled,
.settings-field select:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

@media (max-width: 920px) {
  .settings-system-grid {
    grid-template-columns: 1fr;
  }

  .settings-picker-field {
    grid-template-columns: 1fr;
  }

  .settings-workspace-panel__header {
    flex-direction: column;
  }
}
</style>
