<template>
  <section class="voice-profile-rail">
    <header class="panel-heading">
      <span>音色候选</span>
      <small>{{ profiles.length ? "Runtime 配置" : "未加载" }}</small>
    </header>

    <div v-if="profiles.length === 0" class="empty-text">
      当前没有可用音色，请检查 AI 与系统设置。
    </div>

    <div v-else class="profile-list">
      <button
        v-for="profile in profiles"
        :key="profile.id"
        class="profile-item"
        :class="{ 'profile-item--active': selectedProfileId === profile.id }"
        :disabled="!profile.enabled"
        type="button"
        @click="$emit('select', profile.id)"
      >
        <span class="profile-name">{{ profile.displayName }}</span>
        <span class="profile-provider">{{ profile.provider }}</span>
        <span class="profile-tags">
          <span v-for="tag in profile.tags" :key="tag">{{ tag }}</span>
        </span>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { VoiceProfileDto } from "@/types/runtime";

defineProps<{
  profiles: VoiceProfileDto[];
  selectedProfileId: string | null;
}>();

defineEmits<{
  select: [profileId: string];
}>();
</script>

<style scoped>
.voice-profile-rail {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
  overflow: hidden;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 700;
}

.panel-heading small {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 500;
}

.profile-list {
  display: grid;
  gap: 8px;
  padding: 10px;
}

.profile-item {
  display: grid;
  gap: 6px;
  width: 100%;
  padding: 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  transition: border-color 160ms ease, transform 160ms ease, background 160ms ease;
}

.profile-item:hover,
.profile-item--active {
  border-color: var(--brand-primary);
  background: color-mix(in srgb, var(--brand-primary) 8%, var(--bg-card));
}

.profile-item:hover {
  transform: translateY(-1px);
}

.profile-item:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.profile-name {
  font-size: 14px;
  font-weight: 800;
}

.profile-provider {
  color: var(--text-muted);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 11px;
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

.empty-text {
  padding: 14px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
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
