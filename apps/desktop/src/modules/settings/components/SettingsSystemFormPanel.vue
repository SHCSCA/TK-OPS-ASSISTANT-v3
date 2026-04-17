<template>
  <section class="settings-workspace-panel">
    <div class="editor-card__header">
      <div>
        <p class="detail-panel__label">系统总线</p>
        <h2>Runtime 与默认项</h2>
        <p class="workspace-page__summary">
          运行模式、目录和 AI 默认项统一收敛到配置总线，不再让用户逐项手填。
        </p>
      </div>
    </div>

    <div class="settings-system-grid">
      <section class="command-panel settings-card">
        <h2>Runtime</h2>
        <label class="settings-field">
          <span>运行模式</span>
          <select v-model="form.runtime.mode" data-field="runtime.mode" :disabled="disabled">
            <option v-for="option in runtimeModeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <label class="settings-field">
          <span>工作区目录</span>
          <div class="settings-picker-field">
            <input
              :value="form.runtime.workspaceRoot"
              data-field="runtime.workspaceRoot"
              :disabled="disabled"
              readonly
              :title="form.runtime.workspaceRoot"
            />
            <button
              class="settings-page__button settings-page__button--ghost"
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

      <section class="command-panel settings-card">
        <h2>路径配置</h2>
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
              class="settings-page__button settings-page__button--ghost"
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
              class="settings-page__button settings-page__button--ghost"
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
              class="settings-page__button settings-page__button--ghost"
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

      <section class="command-panel settings-card">
        <h2>日志</h2>
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

      <section class="command-panel settings-card">
        <h2>AI 默认项</h2>
        <label class="settings-field">
          <span>默认 Provider</span>
          <select v-model="form.ai.provider" data-field="ai.provider" :disabled="disabled">
            <option value="">请选择 Provider</option>
            <option
              v-for="provider in providerOptions"
              :key="provider.provider"
              :value="provider.provider"
            >
              {{ provider.label }}
            </option>
          </select>
        </label>
        <label class="settings-field">
          <span>默认模型</span>
          <select v-model="form.ai.model" data-field="ai.model" :disabled="disabled || modelOptions.length === 0">
            <option value="">{{ modelOptions.length === 0 ? "请先选择 Provider" : "请选择模型" }}</option>
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

.settings-system-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
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

@media (max-width: 920px) {
  .settings-system-grid {
    grid-template-columns: 1fr;
  }

  .settings-picker-field {
    grid-template-columns: 1fr;
  }
}
</style>
