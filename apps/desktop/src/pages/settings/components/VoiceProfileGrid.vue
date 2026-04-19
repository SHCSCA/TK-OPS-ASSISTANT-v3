<template>
  <div class="voice-grid-container">
    <header class="grid-header">
      <div class="provider-select">
        <label>TTS Provider</label>
        <select :value="selectedProviderId" class="ui-select" @change="e => $emit('update:selectedProviderId', (e.target as HTMLSelectElement).value)">
          <option v-for="p in providers" :key="p.provider" :value="p.provider">
            {{ p.label }}
          </option>
        </select>
      </div>
      <Button variant="secondary" size="sm" @click="showCreateForm = !showCreateForm">
        <template #leading>
          <span class="material-symbols-outlined">{{ showCreateForm ? 'close' : 'add' }}</span>
        </template>
        {{ showCreateForm ? '取消' : '添加自定义音色' }}
      </Button>
    </header>

    <!-- 自定义音色创建表单 -->
    <transition name="expand">
      <div v-if="showCreateForm" class="create-form">
        <div class="create-form__grid">
          <div class="form-group">
            <label>Voice ID</label>
            <input v-model="newVoice.voiceId" type="text" class="ui-input" placeholder="例如：custom-voice-01" />
          </div>
          <div class="form-group">
            <label>显示名称</label>
            <input v-model="newVoice.displayName" type="text" class="ui-input" placeholder="例如：温暖女声" />
          </div>
          <div class="form-group">
            <label>语言区域</label>
            <input v-model="newVoice.locale" type="text" class="ui-input" placeholder="zh-CN" />
          </div>
          <div class="form-group">
            <label>标签（逗号分隔）</label>
            <input v-model="newVoice.tags" type="text" class="ui-input" placeholder="温暖, 女声, 叙述" />
          </div>
        </div>
        <div class="create-form__actions">
          <Button variant="primary" size="sm" :disabled="!canCreateVoice" @click="handleCreateVoice">
            创建音色
          </Button>
        </div>
      </div>
    </transition>

    <div class="voice-grid">
      <div
        v-for="profile in profiles"
        :key="profile.id"
        class="voice-card"
        :class="{ 'is-selected': modelValue === profile.id }"
        @click="$emit('update:modelValue', profile.id)"
      >
        <div class="card-header">
          <div class="voice-avatar">
            <span class="material-symbols-outlined">person</span>
          </div>
          <div class="voice-info">
            <strong class="voice-name">{{ profile.displayName }}</strong>
            <span class="voice-id">{{ profile.voiceId }}</span>
          </div>
        </div>

        <div class="card-body">
          <div class="voice-tags">
            <Chip v-for="tag in profile.tags" :key="tag" size="sm">{{ tag }}</Chip>
            <Chip size="sm" variant="neutral">{{ profile.locale }}</Chip>
          </div>
          <p class="provider-tag">Provider: {{ profile.provider }}</p>
        </div>

        <footer class="card-footer">
          <Button variant="ghost" size="sm" @click.stop="$emit('preview', profile.id)">
            <template #leading><span class="material-symbols-outlined">play_arrow</span></template>
            试听
          </Button>
          <Button variant="ghost" size="sm" icon-only>
            <span class="material-symbols-outlined">edit</span>
          </Button>
        </footer>

        <!-- 播放波形动画 -->
        <div v-if="previewingId === profile.id" class="waveform-overlay">
          <div v-for="i in 5" :key="i" class="wave-bar" :style="{ animationDelay: `${i * 0.1}s` }" />
        </div>
      </div>
    </div>

    <div v-if="profiles.length === 0" class="empty-state">
      <span class="material-symbols-outlined">record_voice_over</span>
      <p>当前 Provider 暂无音色配置，请切换 Provider 或添加自定义音色。</p>
    </div>

    <div class="footer-hint">
      提示：音色来源由 Provider 决定。更换 TTS Provider 后需要重新选择或配置音色。
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import type { AIProviderCatalogItem, VoiceProfileDto } from "@/types/runtime";
import type { VoiceProfileFormState } from "../types";
import Button from "@/components/ui/Button/Button.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const props = defineProps<{
  profiles: VoiceProfileDto[];
  providers: AIProviderCatalogItem[];
  selectedProviderId: string;
  modelValue: string;
  previewingId: string | null;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
  (e: "update:selectedProviderId", value: string): void;
  (e: "preview", id: string): void;
  (e: "create", data: VoiceProfileFormState): void;
}>();

const showCreateForm = ref(false);
const newVoice = reactive<VoiceProfileFormState>({
  voiceId: "",
  displayName: "",
  locale: "zh-CN",
  tags: ""
});

const canCreateVoice = computed(() =>
  newVoice.voiceId.trim() !== "" && newVoice.displayName.trim() !== ""
);

function handleCreateVoice() {
  if (!canCreateVoice.value) return;
  emit("create", { ...newVoice });
  newVoice.voiceId = "";
  newVoice.displayName = "";
  newVoice.locale = "zh-CN";
  newVoice.tags = "";
  showCreateForm.value = false;
}
</script>

<style scoped>
.voice-grid-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.grid-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.provider-select {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 240px;
}

.provider-select label {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.ui-select {
  height: 36px;
  padding: 0 12px;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  outline: none;
}

/* 自定义音色创建表单 */
.create-form {
  padding: var(--space-5);
  background: var(--color-bg-canvas);
  border: 1px solid var(--color-brand-primary);
  border-radius: var(--radius-lg);
}

.create-form__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-group label {
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.ui-input {
  height: 36px;
  padding: 0 12px;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font: var(--font-body-sm);
  outline: none;
  transition: border-color var(--motion-fast) var(--ease-standard);
}

.ui-input:focus { border-color: var(--color-brand-primary); }

.create-form__actions {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-4);
}

/* 网格 */
.voice-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-4);
}

.voice-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  cursor: pointer;
  position: relative;
  transition: all var(--motion-fast) var(--ease-spring);
}

.voice-card:hover {
  border-color: var(--color-border-default);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.voice-card.is-selected {
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 1px var(--color-brand-primary), var(--shadow-md);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.voice-avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
}

.voice-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.voice-name {
  font: var(--font-title-sm);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.voice-id {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.voice-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.provider-tag {
  margin: 4px 0 0 0;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-subtle);
}

.waveform-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 24px;
  background: color-mix(in srgb, var(--color-brand-primary) 10%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border-bottom-left-radius: inherit;
  border-bottom-right-radius: inherit;
}

.wave-bar {
  width: 3px;
  height: 12px;
  background: var(--color-brand-primary);
  border-radius: 99px;
  animation: wave 1s ease-in-out infinite;
}

@keyframes wave {
  0%, 100% { height: 4px; }
  50% { height: 16px; }
}

.empty-state {
  text-align: center;
  padding: var(--space-10);
  color: var(--color-text-tertiary);
}

.empty-state .material-symbols-outlined {
  font-size: 48px;
  margin-bottom: var(--space-4);
  opacity: 0.4;
}

.footer-hint {
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
  text-align: center;
}

/* 展开动画 */
.expand-enter-active, .expand-leave-active {
  transition: all var(--motion-default) var(--ease-standard);
  max-height: 400px;
  overflow: hidden;
}
.expand-enter-from, .expand-leave-to {
  max-height: 0;
  opacity: 0;
  margin-top: 0;
  padding: 0;
}
</style>
