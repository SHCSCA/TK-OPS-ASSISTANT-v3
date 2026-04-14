<template>
  <section class="command-panel recent-project-card" data-dashboard-section="recent-projects">
    <div class="command-panel__title-row">
      <div>
        <p class="detail-panel__label">最近项目</p>
        <h2>继续已有创作</h2>
      </div>
      <span class="page-chip page-chip--muted">{{ label }}</span>
    </div>

    <div v-if="projects.length === 0" class="empty-state empty-state--guide">
      <strong>还没有项目。</strong>
      <p>创建第一个项目后，脚本、分镜和媒体链路会按项目上下文解锁。</p>
    </div>
    <div v-else class="dashboard-list">
      <article
        v-for="project in projects"
        :key="project.id"
        class="dashboard-list__item"
        :data-project-id="project.id"
      >
        <div>
          <h3>{{ project.name }}</h3>
          <p>{{ project.description || "暂无描述" }}</p>
          <p class="dashboard-list__meta">{{ formatProjectMeta(project) }}</p>
        </div>
        <button
          class="dashboard-list__action"
          type="button"
          :disabled="isBusy"
          @click="$emit('select', project.id)"
        >
          打开
        </button>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ProjectSummary } from "@/types/runtime";

defineEmits<{
  select: [projectId: string];
}>();

defineProps<{
  isBusy: boolean;
  label: string;
  projects: ProjectSummary[];
}>();

function formatProjectMeta(project: ProjectSummary): string {
  return `脚本 v${project.currentScriptVersion} / 分镜 v${project.currentStoryboardVersion} / ${project.status}`;
}
</script>
