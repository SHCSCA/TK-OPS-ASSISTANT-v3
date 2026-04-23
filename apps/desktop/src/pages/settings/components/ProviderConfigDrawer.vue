<template>
  <transition name="drawer">
    <div v-if="open" class="drawer-overlay" @click="$emit('close')">
      <aside class="drawer-panel" @click.stop>
        <header class="drawer-header">
          <div class="header-content">
            <button class="back-btn" @click="$emit('close')">
              <span class="material-symbols-outlined">arrow_back</span>
              返回列表
            </button>
            <h2 class="title">配置 · {{ provider?.label }}</h2>
          </div>
          <button class="close-btn" @click="$emit('close')">
            <span class="material-symbols-outlined">close</span>
          </button>
        </header>

        <div class="drawer-body scroll-area">
          <!-- API Key -->
          <div class="form-section">
            <label class="field-label">API Key</label>
            <div class="input-with-eye">
              <input
                v-model="apiKey"
                :type="showKey ? 'text' : 'password'"
                class="ui-input-field"
                placeholder="sk-..."
              />
              <button class="eye-btn" @click="showKey = !showKey">
                <span class="material-symbols-outlined">{{ showKey ? 'visibility_off' : 'visibility' }}</span>
              </button>
            </div>
            <div class="field-hint">
              来源：{{ keySource }}
              <template v-if="provider?.secretSource === 'env'">
                · 环境变量
              </template>
            </div>
          </div>

          <!-- Base URL -->
          <div class="form-section">
            <label class="field-label">
              Base URL
              <span v-if="provider?.requiresBaseUrl" class="required-badge">必填</span>
            </label>
            <input
              v-model="baseUrl"
              type="text"
              class="ui-input-field"
              :placeholder="baseUrlPlaceholder"
            />
            <div class="field-hint">
              {{ baseUrlHint }}
            </div>
          </div>

          <!-- 连通性测试 -->
          <div class="divider">连通性测试</div>

          <div class="test-section">
            <div class="test-controls">
              <div class="test-model-select">
                <label>测试模型</label>
                <select v-model="testModel" class="ui-input-field select-field">
                  <option v-for="m in models" :key="m.modelId" :value="m.modelId">
                    {{ m.displayName || m.modelId }}
                  </option>
                </select>
              </div>
              <Button
                variant="ai"
                :running="isTesting"
                :disabled="isTesting"
                @click="handleTest"
              >
                <template #leading><span class="material-symbols-outlined">play_arrow</span></template>
                测试连通性
              </Button>
            </div>

            <ProviderHealthResult :health="health" />
          </div>

          <!-- 可用模型 -->
          <div class="divider">可用模型</div>

          <div class="models-section">
            <div class="models-header">
              <!-- 模型发现供应商：显示刷新按钮 -->
              <template v-if="provider?.supportsModelDiscovery">
                <Button variant="secondary" size="sm" :disabled="isRefreshing" @click="$emit('refresh-models')">
                  <template #leading>
                    <span class="material-symbols-outlined" :class="{ spinning: isRefreshing }">refresh</span>
                  </template>
                  刷新远程模型
                </Button>
                <Chip size="sm" variant="brand">动态发现</Chip>
              </template>
              <!-- 非发现供应商：显示静态标签 -->
              <template v-else>
                <Chip size="sm" variant="neutral">内置与自定义模型</Chip>
              </template>
              <span class="count-tag">共 {{ models.length }} 个模型</span>
            </div>

            <div class="model-list">
              <div v-for="m in models" :key="m.modelId" class="model-item">
                <span class="model-id">{{ m.displayName || m.modelId }}</span>
                <div class="model-tags">
                  <Chip v-if="m.capabilityTypes.includes('text_generation')" size="sm">文本</Chip>
                  <Chip v-if="m.capabilityTypes.includes('vision')" size="sm">视觉</Chip>
                  <Chip v-if="m.capabilityTypes.includes('video')" size="sm">视频</Chip>
                  <Chip v-if="m.capabilityTypes.includes('tts')" size="sm">TTS</Chip>
                  <Chip v-if="m.capabilityTypes.includes('asset_analysis')" size="sm">分析</Chip>
                </div>
              </div>
              <div v-if="models.length === 0" class="model-empty">
                {{ provider?.supportsModelDiscovery ? '点击上方按钮刷新远程模型列表' : '暂无模型数据' }}
              </div>
            </div>

            <!-- 非发现供应商：手动添加自定义模型 (F-06, F-07) -->
            <div v-if="!provider?.supportsModelDiscovery" class="custom-model-form">
              <div class="cm-header">
                <strong>添加自定义模型</strong>
                <span v-if="customModelError" class="cm-error">{{ customModelError }}</span>
              </div>
              
              <input
                v-model="customModelId"
                type="text"
                class="ui-input-field custom-model-input"
                placeholder="输入 model_id (如 deepseek-v3)"
                @blur="validateCustomModelId"
              />

              <div class="cm-capabilities">
                <label>能力标注 (至少选一项):</label>
                <div class="cm-checkbox-group">
                  <label><input type="checkbox" value="text_generation" v-model="customCapabilities" /> 文本</label>
                  <label><input type="checkbox" value="vision" v-model="customCapabilities" /> 视觉</label>
                  <label><input type="checkbox" value="video" v-model="customCapabilities" /> 视频</label>
                  <label><input type="checkbox" value="tts" v-model="customCapabilities" /> TTS</label>
                  <label><input type="checkbox" value="asset_analysis" v-model="customCapabilities" /> 分析</label>
                </div>
              </div>

              <div v-if="showOverwritePrompt" class="cm-overwrite">
                <label><input type="checkbox" v-model="overwriteExisting" /> 覆盖已有配置</label>
              </div>

              <Button 
                variant="secondary" 
                size="sm" 
                :disabled="!isCustomModelValid" 
                @click="addCustomModel"
              >
                保存自定义模型
              </Button>
            </div>
          </div>
        </div>

        <footer class="drawer-footer">
          <Button variant="ghost" @click="$emit('close')">取消</Button>
          <Button variant="primary" :disabled="isSaving" @click="handleSave">
            {{ isSaving ? '保存中...' : '保存凭据' }}
          </Button>
        </footer>
      </aside>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { ProviderCardState, AIProviderHealth, AIModelCatalogItem } from "../types";
import ProviderHealthResult from "./ProviderHealthResult.vue";
import Button from "@/components/ui/Button/Button.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const props = defineProps<{
  open: boolean;
  provider: ProviderCardState | null;
  isTesting: boolean;
  isRefreshing: boolean;
  isSaving: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "save", data: { apiKey: string; baseUrl: string }): void;
  (e: "test", modelId: string): void;
  (e: "refresh-models"): void;
  (e: "save-model", modelId: string, capabilityKinds: string[]): void;
}>();

const apiKey = ref("");
const baseUrl = ref("");
const showKey = ref(false);
const testModel = ref("");

// Custom Model State
const customModelId = ref("");
const customCapabilities = ref<string[]>(["text_generation"]);
const customModelError = ref("");
const showOverwritePrompt = ref(false);
const overwriteExisting = ref(false);

watch(() => props.provider, (p) => {
  if (p) {
    apiKey.value = "";
    baseUrl.value = p.baseUrl || "";
    showKey.value = false;
    resetCustomModelForm();
    if (p.models && p.models.length > 0 && !testModel.value) {
      testModel.value = p.models[0].modelId;
    }
  }
}, { immediate: true });

const models = computed<AIModelCatalogItem[]>(() => props.provider?.models || []);
const health = computed<AIProviderHealth | null>(() => props.provider?.health || null);

const keySource = computed(() => {
  if (props.provider?.secretSource === "env") return "环境变量";
  if (props.provider?.configured) return "已加密存储";
  return "未设置";
});

const baseUrlPlaceholder = computed(() => {
  return props.provider?.baseUrl || "https://api.example.com/v1";
});

const baseUrlHint = computed(() => {
  if (props.provider?.requiresBaseUrl) return "此 Provider 必须配置 Base URL";
  return "默认值，留空使用官方地址";
});

const isCustomModelValid = computed(() => {
  const id = customModelId.value.trim();
  if (!id) return false;
  if (customCapabilities.value.length === 0) return false;
  if (showOverwritePrompt.value && !overwriteExisting.value) return false;
  return true;
});

function handleTest() {
  if (!testModel.value) return;
  emit("test", testModel.value);
}

function handleSave() {
  emit("save", { apiKey: apiKey.value, baseUrl: baseUrl.value });
}

function resetCustomModelForm() {
  customModelId.value = "";
  customCapabilities.value = ["text_generation"];
  customModelError.value = "";
  showOverwritePrompt.value = false;
  overwriteExisting.value = false;
}

function validateCustomModelId() {
  const id = customModelId.value.trim();
  customModelError.value = "";
  showOverwritePrompt.value = false;
  
  if (!id) return;

  const exists = models.value.some(m => m.modelId === id);
  if (exists) {
    customModelError.value = "该模型 ID 已存在";
    showOverwritePrompt.value = true;
  }
}

function addCustomModel() {
  if (!isCustomModelValid.value) return;
  
  const id = customModelId.value.trim();
  emit("save-model", id, [...customCapabilities.value]);
  
  // Update test model to the newly added one for convenience
  testModel.value = id;
  
  // Clear the form after submission
  resetCustomModelForm();
}
</script>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-bg-overlay);
  z-index: var(--z-modal-backdrop, 1000);
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: 480px;
  max-width: 100vw;
  background: var(--color-bg-surface);
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.drawer-header {
  padding: 0 var(--space-5);
  height: 64px;
  border-bottom: 1px solid var(--color-border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.header-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.back-btn {
  background: transparent;
  border: none;
  color: var(--color-brand-primary);
  font: var(--font-caption);
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 0;
}

.back-btn:hover { text-decoration: underline; }

.title {
  margin: 0;
  font: var(--font-title-lg);
  color: var(--color-text-primary);
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--color-text-tertiary);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
  transition: color var(--motion-fast) var(--ease-standard);
}

.close-btn:hover { color: var(--color-text-primary); }

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.field-label {
  font: var(--font-title-sm);
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.required-badge {
  font: var(--font-caption);
  color: var(--color-danger);
  background: color-mix(in srgb, var(--color-danger) 10%, transparent);
  padding: 0 6px;
  border-radius: var(--radius-xs);
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
  transition: border-color var(--motion-fast) var(--ease-standard);
}

.ui-input-field:focus { border-color: var(--color-brand-primary); }

.select-field {
  appearance: auto;
}

.input-with-eye {
  position: relative;
}

.eye-btn {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  color: var(--color-text-tertiary);
  cursor: pointer;
  padding: 2px;
}

.eye-btn:hover { color: var(--color-text-primary); }

.field-hint {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.divider {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--color-border-subtle);
}

.test-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.test-controls {
  display: flex;
  align-items: flex-end;
  gap: var(--space-4);
}

.test-model-select {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.test-model-select label {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.models-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.models-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.count-tag {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  margin-left: auto;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--color-border-subtle);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: var(--color-bg-surface);
}

.model-id {
  font: var(--font-mono-md);
  color: var(--color-text-primary);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-tags {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.model-empty {
  padding: var(--space-6);
  background: var(--color-bg-surface);
  text-align: center;
  color: var(--color-text-tertiary);
  font: var(--font-body-sm);
}

.custom-model-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  margin-top: var(--space-2);
}

.cm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cm-header strong {
  font: var(--font-title-sm);
  color: var(--color-text-primary);
}

.cm-error {
  font: var(--font-caption);
  color: var(--color-danger);
}

.custom-model-input {
  font: var(--font-mono-md);
}

.cm-capabilities {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.cm-capabilities label {
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.cm-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.cm-checkbox-group label {
  display: flex;
  align-items: center;
  gap: 4px;
  font: var(--font-body-sm);
  color: var(--color-text-primary);
  cursor: pointer;
}

.cm-overwrite {
  padding: var(--space-2);
  background: rgba(245, 183, 64, 0.1);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(245, 183, 64, 0.3);
}

.cm-overwrite label {
  display: flex;
  align-items: center;
  gap: 6px;
  font: var(--font-body-sm);
  color: var(--color-warning);
  cursor: pointer;
}

.drawer-footer {
  padding: var(--space-5);
  border-top: 1px solid var(--color-border-subtle);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  flex-shrink: 0;
}

.spinning { animation: spin 1.5s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* 抽屉过渡动画 */
.drawer-enter-active, .drawer-leave-active { transition: opacity var(--motion-default) var(--ease-standard); }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
.drawer-enter-active .drawer-panel, .drawer-leave-active .drawer-panel {
  transition: transform var(--motion-default) var(--ease-spring);
}
.drawer-enter-from .drawer-panel { transform: translateX(100%); }
.drawer-leave-to .drawer-panel { transform: translateX(100%); }
</style>