<template>
  <aside v-if="task" class="ai-task-banner" :class="`is-${task.status}`">
    <span class="material-symbols-outlined" aria-hidden="true">
      {{ task.status === "failed" ? "error" : "pending_actions" }}
    </span>
    <div>
      <strong>{{ taskLabel }}</strong>
      <small>任务 {{ task.taskId }} · {{ task.status }}</small>
      <small v-if="'progress' in task">
        进度 {{ Math.round(task.progress * 100) }}%
      </small>
      <small v-if="'logId' in task && task.logId">日志 {{ task.logId }}</small>
    </div>
    <button
      v-if="'logId' in task && task.logId"
      class="ai-button is-quiet"
      type="button"
      @click="openTaskLog"
    >
      查看日志
    </button>
    <button
      class="ai-button is-quiet"
      type="button"
      @click="$emit('refresh')"
    >
      刷新
    </button>
    <button
      v-if="task.cancellable"
      class="ai-button is-secondary"
      type="button"
      @click="$emit('cancel')"
    >
      取消
    </button>
  </aside>
</template>

<script setup lang="ts">
import type { RuntimeTaskDto, TaskAcceptedDto } from "@/types/runtime/tasks";

const props = withDefaults(defineProps<{
  task: RuntimeTaskDto | TaskAcceptedDto | null;
  taskLabel?: string;
}>(), {
  taskLabel: "Runtime 正在处理外部任务"
});

const emit = defineEmits<{
  cancel: [];
  openLog: [logId: string];
  refresh: [];
}>();

function openTaskLog(): void {
  const task = props.task;
  if (task && "logId" in task && task.logId) {
    emit("openLog", task.logId);
  }
}
</script>
