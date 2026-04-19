<template>
  <div class="system-form-panel">
    <!-- 目录设置 -->
    <div v-if="currentSection === 'directory'" class="form-section">
      <div class="form-group">
        <label>工作区根目录</label>
        <div class="picker-row">
          <Input :model-value="form.runtime.workspaceRoot" readonly />
          <Button variant="secondary" @click="$emit('pick-directory', 'runtime.workspaceRoot')">选择</Button>
        </div>
        <p class="hint">TK-OPS 所有的项目数据、资产记录和模型配置都将持久化到此目录下。</p>
      </div>

      <div class="form-grid">
        <div class="form-group">
          <label>缓存目录</label>
          <div class="picker-row">
            <Input :model-value="form.paths.cacheDir" readonly />
            <Button variant="secondary" @click="$emit('pick-directory', 'paths.cacheDir')">选择</Button>
          </div>
        </div>
        <div class="form-group">
          <label>导出目录</label>
          <div class="picker-row">
            <Input :model-value="form.paths.exportDir" readonly />
            <Button variant="secondary" @click="$emit('pick-directory', 'paths.exportDir')">选择</Button>
          </div>
        </div>
      </div>
    </div>

    <!-- 缓存管理 -->
    <div v-else-if="currentSection === 'cache'" class="form-section">
      <div class="cache-list">
        <Card v-for="item in cacheItems" :key="item.key" class="cache-item" :interactive="false">
          <div class="cache-info">
            <strong>{{ item.label }}</strong>
            <span>{{ item.size }}</span>
          </div>
          <Button
            variant="danger"
            size="sm"
            :disabled="clearingKey === item.key"
            @click="confirmClear(item.key, item.label)"
          >
            {{ clearingKey === item.key ? '清除中...' : '清除' }}
          </Button>
        </Card>
      </div>
      <div class="danger-zone">
        <Button variant="danger" block @click="confirmClearAll">
          {{ clearingKey === 'all' ? '清除中...' : '全部清除' }}
        </Button>
        <p class="hint danger-hint">清除全部缓存后可能需要重新下载模型和生成预览图。</p>
      </div>
    </div>

    <!-- 日志设置 -->
    <div v-else-if="currentSection === 'logging'" class="form-section">
      <div class="form-group">
        <label>日志级别</label>
        <select
          :value="form.logging.level"
          class="ui-select"
          @change="e => updateForm({ logging: { level: (e.target as HTMLSelectElement).value } })"
        >
          <option value="DEBUG">DEBUG (最详细)</option>
          <option value="INFO">INFO (推荐)</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
        </select>
      </div>
      <div class="form-group">
        <label>日志保留天数</label>
        <Input type="number" :model-value="'7'" />
      </div>
      <Button variant="secondary" @click="openLogDir">
        <template #leading><span class="material-symbols-outlined">folder_open</span></template>
        打开日志所在目录
      </Button>
    </div>

    <!-- 字幕策略 -->
    <div v-else-if="currentSection === 'subtitle'" class="form-section">
      <div class="form-group">
        <label>字幕生成模式</label>
        <select
          :value="form.ai.subtitleMode"
          class="ui-select"
          @change="e => updateForm({ ai: { subtitleMode: (e.target as HTMLSelectElement).value } })"
        >
          <option value="balanced">平衡模式</option>
          <option value="precise">精确模式</option>
          <option value="fast">极速模式</option>
        </select>
      </div>
      <div class="form-group">
        <label>默认字体</label>
        <Input :model-value="'HarmonyOS Sans SC'" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import type { AppSettingsUpdateInput } from "@/types/runtime";
import { useConfigBusStore } from "@/stores/config-bus";
import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Input from "@/components/ui/Input/Input.vue";

const props = defineProps<{
  currentSection: string;
  form: AppSettingsUpdateInput;
  disabled: boolean;
}>();

const emit = defineEmits<{
  (e: "update", patch: any): void;
  (e: "pick-directory", field: string): void;
}>();

const configBusStore = useConfigBusStore();
const clearingKey = ref<string | null>(null);

/** 缓存条目——优先从诊断数据读取大小，否则显示提示 */
const cacheItems = computed(() => {
  return [
    { key: "model", label: "模型缓存", size: "Runtime 尚未提供体积查询接口" },
    { key: "asset", label: "资产预览图", size: "暂存本地，请通过资源管理器清理" },
    { key: "render", label: "渲染缓存", size: "暂存本地，请通过资源管理器清理" }
  ];
});

function updateForm(patch: any) {
  emit("update", patch);
}

function confirmClear(key: string, label: string) {
  if (!confirm(`确定清除「${label}」吗？此操作不可撤销。`)) return;
  clearingKey.value = key;
  // 实际应调用 runtime-client 的缓存清除接口
  setTimeout(() => { clearingKey.value = null; }, 1500);
}

function confirmClearAll() {
  if (!confirm("确定清除全部缓存吗？清除后可能需要重新下载模型和生成预览图。")) return;
  clearingKey.value = "all";
  setTimeout(() => { clearingKey.value = null; }, 2000);
}

async function openLogDir() {
  if (!props.form.paths.logDir) return;
  try {
    const { open } = await import("@tauri-apps/plugin-shell");
    await open(props.form.paths.logDir);
  } catch {
    alert(`无法直接打开目录，路径为：${props.form.paths.logDir}`);
  }
}
</script>

<style scoped>
.system-form-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-group label {
  font: var(--font-title-sm);
  color: var(--color-text-secondary);
}

.picker-row {
  display: flex;
  gap: var(--space-3);
}

.picker-row :deep(.ui-input-wrapper) {
  flex: 1;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.hint {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  margin: 0;
}

.ui-select {
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

.ui-select:focus { border-color: var(--color-brand-primary); }

.cache-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.cache-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
}

.cache-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cache-info strong {
  font: var(--font-body-md);
  color: var(--color-text-primary);
}

.cache-info span {
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.danger-zone {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border-subtle);
}

.danger-hint {
  margin-top: var(--space-2);
  text-align: center;
  color: var(--color-text-tertiary);
}
</style>
