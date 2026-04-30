<template>
  <section class="panel-shell flex flex-col h-full">
    <header class="panel-heading">
      <div class="panel-heading__title">
        <span class="panel-heading__kicker">voice profiles</span>
        <strong>{{ filteredProfiles.length }} 个音色</strong>
      </div>
      <div class="panel-heading__actions">
        <button
          class="sync-button"
          type="button"
          :disabled="refreshing || status === 'loading'"
          @click="$emit('refresh')"
        >
          <span class="material-symbols-outlined" :class="{ spinning: refreshing }">sync</span>
          {{ refreshing ? "同步中" : "同步" }}
        </button>
        <span class="panel-heading__chip" :data-state="status">{{ statusLabel }}</span>
      </div>
    </header>

    <div class="filter-bar">
      <div class="search-box">
        <span class="material-symbols-outlined">search</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索音色名称或 ID..."
          class="search-input"
        />
      </div>
      <div class="language-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="tab-item"
          :class="{ 'tab-item--active': activeTab === tab.value }"
          @click="activeTab = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div class="list-viewport custom-scrollbar">
      <div v-if="status === 'loading'" class="state-surface">
        <div class="loading-spinner"></div>
        <strong>正在读取音色列表</strong>
        <p>{{ stateMessage }}</p>
      </div>
      <div v-else-if="status === 'error'" class="state-surface state-surface--error">
        <span class="material-symbols-outlined text-danger">error</span>
        <strong>读取失败</strong>
        <p>{{ errorMessage || stateMessage }}</p>
      </div>
      <div v-else-if="filteredProfiles.length === 0" class="state-surface state-surface--empty">
        <span class="material-symbols-outlined text-tertiary">inbox</span>
        <strong>未找到匹配音色</strong>
        <p>{{ searchQuery ? "尝试更换搜索词或切换语言分类" : stateMessage }}</p>
      </div>

      <div v-else class="profile-list">
        <button
          v-for="profile in filteredProfiles"
          :key="profile.id"
          class="profile-item"
          :class="{
            'profile-item--active': selectedProfileId === profile.id,
            'profile-item--disabled': !profile.enabled
          }"
          :disabled="!profile.enabled"
          type="button"
          @click="$emit('select', profile.id)"
        >
          <div class="profile-item__main">
            <div class="profile-info">
              <div class="profile-info__top">
                <span class="profile-name">{{ profile.displayName }}</span>
                <span class="profile-locale-badge">{{ formatLocale(profile.locale) }}</span>
              </div>
              <div class="profile-info__meta">
                <span class="profile-id">{{ profile.voiceId }}</span>
              </div>
            </div>
            <div class="profile-indicator">
              <span class="material-symbols-outlined">check_circle</span>
            </div>
          </div>
          <div class="profile-tags">
            <span v-for="tag in profile.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import type { VoiceProfileDto } from "@/types/runtime";
import type { VoiceStudioStatus } from "@/stores/voice-studio";

const props = defineProps<{
  errorMessage: string | null;
  profiles: VoiceProfileDto[];
  selectedProfileId: string | null;
  stateMessage: string;
  status: VoiceStudioStatus;
  refreshing: boolean;
}>();

defineEmits<{
  select: [profileId: string];
  refresh: [];
}>();

const searchQuery = ref("");
const activeTab = ref("all");

const tabs = [
  { label: "全部", value: "all" },
  { label: "中文", value: "zh" },
  { label: "英语", value: "en" },
];

const filteredProfiles = computed(() => {
  return props.profiles.filter((profile) => {
    // Language filter
    if (activeTab.value === "zh" && !profile.locale.startsWith("zh")) return false;
    if (activeTab.value === "en" && !profile.locale.startsWith("en")) return false;

    // Search filter
    if (!searchQuery.value) return true;
    const q = searchQuery.value.toLowerCase();
    return (
      profile.displayName.toLowerCase().includes(q) ||
      profile.voiceId.toLowerCase().includes(q) ||
      profile.tags.some((t) => t.toLowerCase().includes(q))
    );
  });
});

const statusLabel = computed(() => {
  if (props.status === "loading") return "同步中";
  if (props.status === "error") return "故障";
  if (props.profiles.length === 0) return "无数据";
  return "就绪";
});

function formatLocale(locale: string) {
  if (locale.startsWith("zh")) return "中";
  if (locale.startsWith("en")) return "英";
  return locale.split("-")[0].toUpperCase();
}
</script>

<style scoped>
.panel-shell {
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  overflow: hidden;
  height: 520px; /* Give it a fixed height or max-height */
  box-shadow: var(--shadow-sm);
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-muted);
}

.panel-heading__title {
  display: grid;
  gap: 2px;
}

.panel-heading__kicker {
  color: var(--color-text-tertiary);
  font: var(--font-caption);
  text-transform: uppercase;
  letter-spacing: var(--ls-caption);
}

.panel-heading strong {
  color: var(--color-text-primary);
  font: var(--font-title-sm);
}

.panel-heading__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.panel-heading__chip {
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font: var(--font-caption);
  background: var(--color-bg-canvas);
  border: 1px solid var(--color-border-default);
}

.panel-heading__chip[data-state="loading"] {
  color: var(--color-brand-primary);
  border-color: var(--color-brand-secondary);
}

.sync-button {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-md);
  background: var(--color-bg-canvas);
  border: 1px solid var(--color-border-default);
  font: var(--font-caption);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--motion-fast);
}

.sync-button:hover:not(:disabled) {
  background: var(--color-bg-muted);
  border-color: var(--color-brand-primary);
  color: var(--color-brand-primary);
}

.sync-button .material-symbols-outlined {
  font-size: 16px;
}

.filter-bar {
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border-subtle);
  display: grid;
  gap: var(--space-3);
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-box .material-symbols-outlined {
  position: absolute;
  left: 10px;
  font-size: 18px;
  color: var(--color-text-tertiary);
}

.search-input {
  width: 100%;
  padding: 6px 12px 6px 36px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-canvas);
  font: var(--font-body-sm);
  color: var(--color-text-primary);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 2px rgba(0, 188, 212, 0.1);
}

.language-tabs {
  display: flex;
  gap: 4px;
  background: var(--color-bg-muted);
  padding: 2px;
  border-radius: var(--radius-md);
}

.tab-item {
  flex: 1;
  padding: 4px 0;
  border: none;
  background: transparent;
  font: var(--font-caption);
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--motion-fast);
}

.tab-item--active {
  background: var(--color-bg-elevated);
  color: var(--color-brand-primary);
  box-shadow: var(--shadow-sm);
}

.list-viewport {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: var(--color-border-default);
  border-radius: 3px;
}

.profile-list {
  padding: var(--space-3);
  display: grid;
  gap: var(--space-2);
}

.profile-item {
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-canvas);
  text-align: left;
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
  display: grid;
  gap: 8px;
}

.profile-item:hover {
  border-color: var(--color-brand-secondary);
  transform: translateX(2px);
  background: var(--color-bg-muted);
}

.profile-item--active {
  border-color: var(--color-brand-primary);
  background: rgba(0, 188, 212, 0.04);
  box-shadow: 0 0 0 1px var(--color-brand-primary);
}

.profile-item__main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.profile-info {
  display: grid;
  gap: 2px;
}

.profile-info__top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.profile-name {
  font: var(--font-title-sm);
  color: var(--color-text-primary);
}

.profile-locale-badge {
  font-size: 10px;
  padding: 0 4px;
  border-radius: 4px;
  background: var(--color-bg-muted);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-border-subtle);
}

.profile-info__meta {
  font-size: 11px;
  color: var(--color-text-tertiary);
  font-family: var(--font-code);
}

.profile-indicator {
  color: var(--color-brand-primary);
  opacity: 0;
  transition: opacity var(--motion-fast);
}

.profile-item--active .profile-indicator {
  opacity: 1;
}

.profile-indicator .material-symbols-outlined {
  font-size: 18px;
}

.profile-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border-subtle);
}

.profile-item--active .tag {
  background: rgba(0, 188, 212, 0.08);
  border-color: rgba(0, 188, 212, 0.2);
  color: var(--color-brand-primary);
}

.state-surface {
  padding: var(--space-8) var(--space-4);
  text-align: center;
  display: grid;
  gap: var(--space-2);
}

.state-surface strong {
  font: var(--font-title-sm);
  color: var(--color-text-primary);
}

.state-surface p {
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--color-border-default);
  border-top-color: var(--color-brand-primary);
  border-radius: 50%;
  margin: 0 auto var(--space-2);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinning {
  animation: spin 1s linear infinite;
}
</style>
