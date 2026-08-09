<template>
  <Teleport to="body">
    <div
      v-if="open && context"
      class="account-detail-overlay"
      data-testid="account-context-detail"
    >
      <button
        class="account-detail-overlay__backdrop"
        type="button"
        aria-label="关闭账号详情"
        @click="emit('close')"
      />
      <aside
        id="account-context-detail-panel"
        class="account-detail-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="account-context-detail-title"
      >
        <header class="account-detail-panel__header">
          <div>
            <p>当前工作区</p>
            <h2 id="account-context-detail-title">
              {{ context.account.name }}
            </h2>
          </div>
          <button type="button" aria-label="关闭账号详情" @click="emit('close')">
            <span class="material-symbols-outlined" aria-hidden="true">
              close
            </span>
          </button>
        </header>

        <section class="account-detail-panel__identity">
          <span aria-hidden="true">
            {{ context.account.name.slice(0, 1).toUpperCase() }}
          </span>
          <div>
            <strong>{{ identityLabel }}</strong>
            <p>{{ positioningLabel }}</p>
          </div>
        </section>

        <section aria-labelledby="account-detail-readiness-title">
          <h3 id="account-detail-readiness-title">账号就绪状态</h3>
          <dl class="account-detail-panel__readiness">
            <div>
              <dt>连接</dt>
              <dd>{{ context.readiness.connection.label }}</dd>
            </div>
            <div>
              <dt>知识库</dt>
              <dd>{{ context.readiness.knowledge.label }}</dd>
            </div>
            <div>
              <dt>AI 配方</dt>
              <dd>{{ context.readiness.ai.label }}</dd>
            </div>
          </dl>
        </section>

        <section aria-labelledby="account-detail-runtime-title">
          <h3 id="account-detail-runtime-title">当前范围</h3>
          <dl class="account-detail-panel__facts">
            <div>
              <dt>账号修订</dt>
              <dd>{{ context.account.revision }}</dd>
            </div>
            <div>
              <dt>工作区修订</dt>
              <dd>{{ context.workspaceRevision }}</dd>
            </div>
            <div>
              <dt>运行中任务</dt>
              <dd>{{ context.taskSummary.running }}</dd>
            </div>
            <div>
              <dt>失败任务</dt>
              <dd>{{ context.taskSummary.failed }}</dd>
            </div>
          </dl>
        </section>

        <section aria-labelledby="account-detail-tasks-title">
          <h3 id="account-detail-tasks-title">最近任务</h3>
          <p v-if="taskState === 'loading'" class="account-detail-panel__task-state">
            正在读取持久任务…
          </p>
          <p v-else-if="taskState === 'error'" class="account-detail-panel__task-state is-error">
            任务状态暂不可用，Runtime 恢复后会自动重试。
          </p>
          <p v-else-if="visibleTasks.length === 0" class="account-detail-panel__task-state">
            当前账号还没有任务记录。
          </p>
          <ul v-else class="account-detail-panel__tasks">
            <li v-for="task in visibleTasks" :key="task.taskId">
              <div>
                <strong>{{ taskLabel(task.taskType) }}</strong>
                <small>{{ task.taskId }}</small>
              </div>
              <span :class="`is-${taskTone(task)}`">{{ taskStatus(task) }}</span>
            </li>
          </ul>
        </section>
      </aside>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { AccountWorkspaceContextDto } from "@/types/runtime/accounts";
import type { RuntimeTaskDto } from "@/types/runtime/tasks";

const props = defineProps<{
  context: AccountWorkspaceContextDto | null;
  open: boolean;
  taskState?: "idle" | "loading" | "ready" | "empty" | "error";
  tasks?: readonly RuntimeTaskDto[];
}>();

const emit = defineEmits<{
  close: [];
}>();

const identityLabel = computed(() => {
  const username = props.context?.account.username;
  return username ? `@${username}` : "尚未绑定 TikTok handle";
});

const positioningLabel = computed(
  () =>
    props.context?.account.positioningSummary
    || "尚未设置账号定位摘要"
);

const visibleTasks = computed(() => (props.tasks ?? []).slice(0, 5));

function taskLabel(taskType: string): string {
  const labels: Record<string, string> = {
    "account.archive_cleanup": "账号归档清理",
    "account.health_check": "账号健康检查",
    "account.login.prepare": "打开登录浏览器",
    "account.login.probe": "确认登录身份",
    "account.logout": "安全登出",
    "execution_environment.provision": "创建执行环境"
  };
  return labels[taskType] ?? taskType;
}

function taskStatus(task: RuntimeTaskDto): string {
  if (task.status === "completed") {
    return task.completionKind === "cancelled" ? "已取消" : "已完成";
  }
  if (task.status === "failed") {
    if (task.failureKind === "timed_out") return "已超时";
    if (task.failureKind === "restart_interrupted") return "重启中断";
    return "失败";
  }
  return {
    queued: "等待中",
    running: `${Math.round(task.progress * 100)}%`,
    cancelling: "取消中"
  }[task.status];
}

function taskTone(task: RuntimeTaskDto): "working" | "success" | "danger" | "muted" {
  if (task.status === "failed") return "danger";
  if (task.status === "completed") {
    return task.completionKind === "succeeded" ? "success" : "muted";
  }
  return "working";
}
</script>
