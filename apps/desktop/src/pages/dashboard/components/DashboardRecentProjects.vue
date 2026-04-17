<template>
  <section class="recent-projects-panel" data-dashboard-section="recent-projects">
    <div class="recent-projects-panel__header">
      <h4 class="recent-projects-panel__title">最近项目活动</h4>
      <button
        v-if="projects.length > 0"
        class="recent-projects-panel__action"
        type="button"
        :disabled="isBusy"
      >
        查看全部
      </button>
    </div>

    <div v-if="projects.length === 0" class="recent-projects-empty">
      <strong>还没有项目。</strong>
      <p>创建第一个项目后，脚本、分镜和媒体链路会按项目上下文解锁。</p>
    </div>

    <div v-else class="recent-projects-table-wrap">
      <table class="recent-projects-table">
        <thead>
          <tr>
            <th>项目名称</th>
            <th>描述</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="project in projects"
            :key="project.id"
            :data-project-card="project.id"
            :data-project-id="project.id"
          >
            <td class="recent-projects-table__name">{{ project.name }}</td>
            <td class="recent-projects-table__desc">{{ project.description || '暂无描述' }}</td>
            <td>
              <span class="project-status-badge">{{ project.status }}</span>
            </td>
            <td>
              <button
                class="recent-projects-table__btn"
                type="button"
                :disabled="isBusy"
                @click="$emit('select', project.id)"
              >
                打开
              </button>
            </td>
          </tr>
        </tbody>
      </table>
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
</script>
