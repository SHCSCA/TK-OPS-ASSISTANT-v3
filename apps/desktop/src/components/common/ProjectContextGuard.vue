<template>
  <div class="project-context-guard">
    <template v-if="projectStore.currentProject">
      <slot />
    </template>
    <div v-else class="guard-overlay">
      <EmptyState
        icon="folder_off"
        title="需要选择项目"
        :description="`你当前正在访问「${routeTitle}」，该功能需要绑定一个具体的创作项目。请先创建新项目或从总览中打开现有项目。`"
        action-label="前往创作总览"
        @action="navigateToDashboard"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useProjectStore } from '@/stores/project';
import EmptyState from './EmptyState.vue';

const projectStore = useProjectStore();
const router = useRouter();
const route = useRoute();

const routeTitle = computed(() => (route.meta.title as string) || '当前页面');

function navigateToDashboard() {
  router.push('/dashboard');
}
</script>

<style scoped>
.project-context-guard {
  height: 100%;
  width: 100%;
}

.guard-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 500px;
}
</style>
