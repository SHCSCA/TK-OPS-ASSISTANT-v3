<template>
  <Card class="project-recent-card" :interactive="true" :selected="selected" @click="emit('select', project.id)">
    <div class="project-recent-card__header">
      <div class="project-recent-card__title" :title="project.name">{{ project.name }}</div>
      <div class="header-actions">
        <Chip :variant="statusTone">{{ statusLabel }}</Chip>
        <button class="delete-btn" @click.stop="emit('delete', project.id)" title="删除项目">
          <span class="material-symbols-outlined">delete</span>
        </button>
      </div>
    </div>
    
    <div class="project-recent-card__body">
      <p class="project-recent-card__desc" :title="project.description || '暂无说明'">
        {{ project.description || "暂无说明" }}
      </p>
    </div>
    
    <div class="project-recent-card__footer">
      <span class="project-recent-card__meta">
        <span class="material-symbols-outlined">history</span>
        {{ formattedTime }}
      </span>
      <span class="project-recent-card__meta">
        v{{ project.currentScriptVersion }} / v{{ project.currentStoryboardVersion }}
      </span>
    </div>
  </Card>
</template>

<script setup lang="ts">
import { computed } from "vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const props = defineProps<{
  project: {
    id: string;
    name: string;
    description: string;
    status: string;
    currentScriptVersion: number;
    currentStoryboardVersion: number;
    lastAccessedAt: string;
  };
  selected?: boolean;
}>();

const emit = defineEmits<{
  (e: "select", id: string): void;
  (e: "delete", id: string): void;
}>();

const statusLabel = computed(() => {
  switch (props.project.status) {
    case "active": return "活跃";
    case "blocked": return "阻塞";
    case "archived": return "归档";
    default: return props.project.status;
  }
});

const statusTone = computed(() => {
  switch (props.project.status) {
    case "active": return "success";
    case "blocked": return "warning";
    case "error": return "danger";
    default: return "default";
  }
});

const formattedTime = computed(() => {
  if (!props.project.lastAccessedAt) return "未知时间";
  const date = new Date(props.project.lastAccessedAt);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 60) return `${diffMins || 1} 分钟前`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} 小时前`;
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric" }).format(date);
});
</script>

<style scoped>
.project-recent-card {
  display: flex;
  flex-direction: column;
  height: 160px;
  min-width: 280px;
  max-width: 320px;
  scroll-snap-align: start;
}

.project-recent-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
  transition: all var(--motion-fast) var(--ease-standard);
}

.delete-btn:hover {
  background: var(--color-danger);
  color: #FFF;
  border-color: var(--color-danger);
}

.delete-btn .material-symbols-outlined {
  font-size: 16px;
}

.project-recent-card__title {
  font: var(--font-title-md);
  letter-spacing: var(--ls-title-md);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.3;
}

.project-recent-card__body {
  flex: 1;
  min-height: 0;
}

.project-recent-card__desc {
  font: var(--font-body-sm);
  letter-spacing: var(--ls-body-sm);
  color: var(--color-text-secondary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.project-recent-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-subtle);
}

.project-recent-card__meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-tertiary);
}

.project-recent-card__meta .material-symbols-outlined {
  font-size: 14px;
}
</style>
