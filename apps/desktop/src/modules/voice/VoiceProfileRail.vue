<template>
  <section class="panel-shell">
    <header class="panel-heading">
      <div>
        <span class="panel-heading__kicker">voice profiles</span>
        <strong>{{ profiles.length }} 个音色</strong>
      </div>
      <span class="panel-heading__chip" :data-state="status">{{ statusLabel }}</span>
    </header>

    <div v-if="status === 'loading'" class="state-surface">
      <strong>正在读取音色列表。</strong>
      <p>{{ stateMessage }}</p>
    </div>
    <div v-else-if="status === 'error'" class="state-surface state-surface--error">
      <strong>音色列表读取失败。</strong>
      <p>{{ errorMessage || stateMessage }}</p>
    </div>
    <div v-else-if="profiles.length === 0" class="state-surface state-surface--empty">
      <strong>当前没有可用音色。</strong>
      <p>{{ stateMessage }}</p>
    </div>

    <div v-else class="profile-list">
      <button
        v-for="profile in profiles"
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
        <div class="profile-item__head">
          <span class="profile-name">{{ profile.displayName }}</span>
          <span class="profile-state" :data-state="profile.enabled ? 'ready' : 'disabled'">
            {{ profile.enabled ? "可用" : "禁用" }}
          </span>
        </div>
        <span class="profile-provider">{{ profile.provider }} · {{ profile.voiceId }}</span>
        <span class="profile-locale">{{ profile.locale }}</span>
        <div class="profile-tags">
          <span v-for="tag in profile.tags" :key="tag">{{ tag }}</span>
        </div>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { VoiceProfileDto } from "@/types/runtime";
import type { VoiceStudioStatus } from "@/stores/voice-studio";

const props = defineProps<{
  errorMessage: string | null;
  profiles: VoiceProfileDto[];
  selectedProfileId: string | null;
  stateMessage: string;
  status: VoiceStudioStatus;
}>();

defineEmits<{
  select: [profileId: string];
}>();

const statusLabel = computed(() => {
  if (props.status === "loading") return "读取中";
  if (props.status === "error") return "错误";
  if (props.profiles.length === 0) return "空态";
  return "可用";
});
</script>

<style scoped>
.panel-shell {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
  overflow: hidden;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-heading > div {
  display: grid;
  gap: 4px;
}

.panel-heading__kicker {
  color: var(--text-tertiary);
  font-size: 12px;
}

.panel-heading strong {
  color: var(--text-primary);
  font-size: 14px;
}

.panel-heading__chip,
.profile-state {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.panel-heading__chip[data-state="loading"] {
  border-color: color-mix(in srgb, var(--info) 28%, transparent);
  color: var(--info);
}

.panel-heading__chip[data-state="error"] {
  border-color: color-mix(in srgb, var(--danger) 28%, transparent);
  color: var(--danger);
}

.profile-state[data-state="ready"] {
  border-color: color-mix(in srgb, var(--brand-primary) 28%, transparent);
  color: var(--brand-primary);
}

.profile-state[data-state="disabled"] {
  border-color: color-mix(in srgb, var(--warning) 28%, transparent);
  color: var(--warning);
}

.profile-list {
  display: grid;
  gap: 8px;
  padding: 12px;
}

.profile-item {
  display: grid;
  gap: 6px;
  width: 100%;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    transform 160ms ease,
    background-color 160ms ease;
}

.profile-item:hover,
.profile-item--active {
  border-color: color-mix(in srgb, var(--brand-primary) 40%, transparent);
  background: color-mix(in srgb, var(--brand-primary) 8%, var(--bg-card));
}

.profile-item:hover {
  transform: translateY(-1px);
}

.profile-item--disabled {
  opacity: 0.72;
}

.profile-item:disabled {
  cursor: not-allowed;
}

.profile-item__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.profile-name {
  font-size: 14px;
  font-weight: 800;
}

.profile-provider,
.profile-locale {
  color: var(--text-secondary);
  font-size: 12px;
}

.profile-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.profile-tags span {
  padding: 2px 7px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--brand-primary) 12%, transparent);
  color: var(--text-secondary);
  font-size: 11px;
}

.state-surface {
  display: grid;
  gap: 6px;
  padding: 16px;
  margin: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
}

.state-surface--error {
  border-color: color-mix(in srgb, var(--danger) 24%, transparent);
}

.state-surface--empty {
  border-color: color-mix(in srgb, var(--warning) 24%, transparent);
}

.state-surface strong {
  font-size: 14px;
}

.state-surface p {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

@media (prefers-reduced-motion: reduce) {
  .profile-item {
    transition: none;
  }

  .profile-item:hover {
    transform: none;
  }
}
</style>
