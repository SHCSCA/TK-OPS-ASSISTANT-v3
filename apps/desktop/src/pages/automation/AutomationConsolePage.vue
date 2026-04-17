<template>
  <div class="automation-console" data-testid="automation-console">
    <header class="automation-console__header">
      <div class="automation-console__headline">
        <p class="automation-console__eyebrow">执行链路</p>
        <h1>自动化执行中心</h1>
        <p class="automation-console__summary">
          真实任务、运行记录和日志流都从 Runtime 读取。已关闭任务会被标记为禁用，最近一次阻断会直接暴露在日志面板里。
        </p>
      </div>

      <div class="automation-console__metrics">
        <article class="automation-console__metric">
          <span>任务总数</span>
          <strong>{{ tasks.length }}</strong>
        </article>
        <article class="automation-console__metric">
          <span>已启用</span>
          <strong>{{ enabledTaskCount }}</strong>
        </article>
        <article class="automation-console__metric">
          <span>已阻断</span>
          <strong>{{ blockedTaskCount }}</strong>
        </article>
        <article class="automation-console__metric">
          <span>最近触发</span>
          <strong>{{ triggerStateLabel }}</strong>
        </article>
      </div>
    </header>

    <div v-if="automationStore.error" class="automation-console__banner automation-console__banner--error">
      {{ automationStore.error }}
    </div>
    <div v-else-if="isLoading" class="automation-console__banner automation-console__banner--loading">
      正在读取自动化任务和运行日志。
    </div>
    <div v-else-if="automationStore.lastTriggerResult" class="automation-console__banner">
      <strong>最近一次触发：</strong>
      <span>{{ automationStore.lastTriggerResult.message }}</span>
      <span class="automation-console__banner-status">{{ automationStore.lastTriggerResult.status }}</span>
    </div>

    <main class="automation-console__body">
      <aside class="automation-console__rail">
        <div class="automation-console__rail-toolbar">
          <button class="automation-console__primary" type="button" @click="showAddTask = true">
            <span class="material-symbols-outlined">add</span>
            新建任务
          </button>

          <div class="automation-console__chips" aria-label="任务筛选">
            <button
              v-for="item in statusFilters"
              :key="item.value"
              type="button"
              class="automation-console__chip"
              :class="{ 'automation-console__chip--active': statusFilter === item.value }"
              @click="statusFilter = item.value"
            >
              {{ item.label }}
            </button>
          </div>

          <div class="automation-console__chips" aria-label="任务类型筛选">
            <button
              v-for="item in typeFilters"
              :key="item.value"
              type="button"
              class="automation-console__chip automation-console__chip--soft"
              :class="{ 'automation-console__chip--active': typeFilter === item.value }"
              @click="typeFilter = typeFilter === item.value ? '' : item.value"
            >
              {{ item.label }}
            </button>
          </div>
        </div>

        <div v-if="isEmpty" class="automation-console__empty" data-testid="automation-empty-state">
          <span class="material-symbols-outlined automation-console__empty-icon">robot_2</span>
          <h2>暂时没有自动化任务</h2>
          <p>先创建一个任务，再查看运行记录、日志和阻断原因。</p>
          <button class="automation-console__secondary" type="button" @click="showAddTask = true">
            立刻创建
          </button>
        </div>

        <div v-else class="automation-console__task-list" data-testid="automation-task-list">
          <button
            v-for="task in filteredTasks"
            :key="task.id"
            type="button"
            class="automation-console__task"
            :class="{
              'automation-console__task--active': selectedTaskId === task.id,
              'automation-console__task--disabled': !task.enabled,
              'automation-console__task--blocked': isTaskBlocked(task)
            }"
            @click="selectedTaskId = task.id"
          >
            <div class="automation-console__task-row">
              <div class="automation-console__task-title">
                <strong>{{ task.name }}</strong>
                <span>{{ task.type }}</span>
              </div>
              <span class="automation-console__status-pill" :class="taskStatusTone(task)">
                {{ taskStatusLabel(task) }}
              </span>
            </div>

            <div class="automation-console__task-meta">
              <span>Cron {{ task.cron_expr || "未配置" }}</span>
              <span>运行 {{ task.run_count }}</span>
            </div>
            <div class="automation-console__task-meta">
              <span>最近运行 {{ task.last_run_at ? formatDate(task.last_run_at) : "从未" }}</span>
              <span>最后状态 {{ task.last_run_status || "未知" }}</span>
            </div>

            <div class="automation-console__task-footer">
              <span class="automation-console__inline-flag" :class="task.enabled ? 'is-on' : 'is-off'">
                {{ task.enabled ? "已启用" : "已关闭" }}
              </span>
              <button
                class="automation-console__ghost"
                type="button"
                :disabled="isBusy"
                @click.stop="handleRunTask(task.id)"
              >
                运行
              </button>
            </div>
          </button>
        </div>
      </aside>

      <section class="automation-console__workspace" data-testid="automation-task-detail">
        <template v-if="selectedTask">
          <div class="automation-console__workspace-head">
            <div>
              <p class="automation-console__eyebrow">当前任务</p>
              <h2>{{ selectedTask.name }}</h2>
              <p class="automation-console__summary automation-console__summary--compact">
                类型 {{ selectedTask.type }}，Cron {{ selectedTask.cron_expr || "未配置" }}，运行次数
                {{ selectedTask.run_count }}。
              </p>
            </div>

            <div class="automation-console__workspace-actions">
              <span class="automation-console__status-pill" :class="taskStatusTone(selectedTask)">
                {{ taskStatusLabel(selectedTask) }}
              </span>
              <button
                class="automation-console__secondary"
                type="button"
                :disabled="isBusy"
                @click="selectedTask.enabled ? handleRunTask(selectedTask.id) : undefined"
              >
                {{ selectedTask.enabled ? "手动触发" : "任务已关闭" }}
              </button>
            </div>
          </div>

          <div class="automation-console__state-row">
            <article class="automation-console__state-tile">
              <span>执行开关</span>
              <strong>{{ selectedTask.enabled ? "已启用" : "已关闭" }}</strong>
            </article>
            <article class="automation-console__state-tile">
              <span>最近状态</span>
              <strong>{{ selectedTask.last_run_status || "未知" }}</strong>
            </article>
            <article class="automation-console__state-tile">
              <span>运行状态</span>
              <strong>{{ currentRunStateLabel }}</strong>
            </article>
            <article class="automation-console__state-tile">
              <span>阻断语义</span>
              <strong>{{ selectedTaskBlockLabel }}</strong>
            </article>
          </div>

          <section class="automation-console__lane">
            <div class="automation-console__lane-head">
              <h3>运行历史</h3>
              <span>{{ selectedRuns.length }} 条记录</span>
            </div>

            <div v-if="runsLoading" class="automation-console__empty automation-console__empty--inline">
              正在读取该任务的运行历史。
            </div>
            <div v-else-if="selectedRuns.length === 0" class="automation-console__empty automation-console__empty--inline">
              该任务暂时还没有运行记录。
            </div>
            <div v-else class="automation-console__run-list">
              <article
                v-for="run in selectedRuns"
                :key="run.id"
                class="automation-console__run"
                :class="{ 'automation-console__run--blocked': run.status === 'blocked' }"
              >
                <div class="automation-console__run-head">
                  <strong>{{ run.status }}</strong>
                  <span>{{ formatDateTime(run.started_at ?? run.created_at) }}</span>
                </div>
                <div class="automation-console__run-meta">
                  <span>开始 {{ run.started_at ? formatDateTime(run.started_at) : "未开始" }}</span>
                  <span>结束 {{ run.finished_at ? formatDateTime(run.finished_at) : "未结束" }}</span>
                </div>
              </article>
            </div>
          </section>

          <section class="automation-console__lane">
            <div class="automation-console__lane-head">
              <h3>日志流</h3>
              <span>{{ selectedLogs.length }} 行</span>
            </div>

            <div class="automation-console__terminal" data-testid="automation-log-stream">
              <div v-if="selectedLogs.length === 0" class="automation-console__terminal-line automation-console__terminal-line--muted">
                > 暂无日志。触发任务后，运行内容会在这里展开。
              </div>
              <template v-else>
                <div
                  v-for="line in selectedLogs"
                  :key="line.id"
                  class="automation-console__terminal-line"
                  :class="{ 'automation-console__terminal-line--blocked': line.status === 'blocked' }"
                >
                  > {{ line.text }}
                </div>
              </template>
            </div>
          </section>

          <section class="automation-console__lane">
            <div class="automation-console__lane-head">
              <h3>执行配置</h3>
              <span>{{ selectedTask.enabled ? "可执行" : "已关闭" }}</span>
            </div>
            <div class="automation-console__config">
              <div class="automation-console__config-row">
                <span>任务类型</span>
                <strong>{{ selectedTask.type }}</strong>
              </div>
              <div class="automation-console__config-row">
                <span>Cron</span>
                <strong>{{ selectedTask.cron_expr || "未配置" }}</strong>
              </div>
              <div class="automation-console__config-row">
                <span>配置体</span>
                <pre>{{ selectedTaskConfigPreview }}</pre>
              </div>
            </div>
          </section>
        </template>

        <div v-else class="automation-console__detail-empty">
          <span class="material-symbols-outlined automation-console__empty-icon">monitoring</span>
          <h2>选择一个任务查看执行链路</h2>
          <p>这里会显示运行历史、日志流和阻断语义。</p>
        </div>
      </section>
    </main>

    <div v-if="showAddTask" class="automation-console__drawer" @click.self="showAddTask = false">
      <section class="automation-console__drawer-panel">
        <div class="automation-console__drawer-head">
          <div>
            <p class="automation-console__eyebrow">新建任务</p>
            <h2>创建自动化任务</h2>
          </div>
          <button class="automation-console__icon-button" type="button" @click="showAddTask = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="automation-console__drawer-body">
          <label class="automation-console__field">
            <span>任务名称</span>
            <input v-model="addForm.name" type="text" placeholder="例如：每日同步账号状态" />
          </label>

          <label class="automation-console__field">
            <span>任务类型</span>
            <select v-model="addForm.type">
              <option value="collect">采集</option>
              <option value="reply">回复</option>
              <option value="sync">同步</option>
              <option value="validate">校验</option>
            </select>
          </label>

          <label class="automation-console__field">
            <span>Cron 表达式</span>
            <input v-model="addForm.cronExpr" type="text" placeholder="0 */2 * * *" />
          </label>

          <label class="automation-console__field">
            <span>执行参数 JSON</span>
            <textarea
              v-model="addForm.configJson"
              rows="6"
              placeholder='{"workspaceId":"ws-1","enabled":true}'
            />
          </label>

          <div class="automation-console__drawer-actions">
            <button class="automation-console__secondary" type="button" @click="showAddTask = false">
              取消
            </button>
            <button class="automation-console__primary" type="button" :disabled="isBusy" @click="handleCreateTask">
              保存任务
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { useAutomationStore } from "@/stores/automation";
import type { AutomationTaskCreateInput, AutomationTaskDto } from "@/types/runtime";

type TaskView = AutomationTaskDto;
type TaskFilterValue = "all" | "enabled" | "disabled";

const automationStore = useAutomationStore();
const selectedTaskId = ref<string | null>(null);
const statusFilter = ref<TaskFilterValue>("all");
const typeFilter = ref<string>("");
const showAddTask = ref(false);
const addForm = ref({
  name: "",
  type: "collect",
  cronExpr: "",
  configJson: ""
});

const tasks = computed(() => automationStore.tasks as TaskView[]);
const enabledTaskCount = computed(() => tasks.value.filter((task) => task.enabled).length);
const blockedTaskCount = computed(
  () =>
    tasks.value.filter((task) => task.last_run_status === "blocked" || !task.enabled).length
);
const isLoading = computed(() => automationStore.loading || automationStore.viewState === "loading");
const isEmpty = computed(() => automationStore.viewState === "empty" && !isLoading.value);
const isBusy = computed(() => isLoading.value || automationStore.triggerState === "running");
const triggerStateLabel = computed(() =>
  automationStore.triggerState === "running"
    ? "触发中"
    : automationStore.triggerState === "error"
      ? "触发失败"
      : automationStore.triggerState === "ready"
        ? "已触发"
        : "空闲"
);

const statusFilters: Array<{ label: string; value: TaskFilterValue }> = [
  { label: "全部", value: "all" },
  { label: "已启用", value: "enabled" },
  { label: "已关闭", value: "disabled" }
];

const typeFilters = [
  { label: "采集", value: "collect" },
  { label: "回复", value: "reply" },
  { label: "同步", value: "sync" },
  { label: "校验", value: "validate" }
];

const filteredTasks = computed(() => {
  let list = tasks.value;

  if (statusFilter.value === "enabled") {
    list = list.filter((task) => task.enabled);
  } else if (statusFilter.value === "disabled") {
    list = list.filter((task) => !task.enabled);
  }

  if (typeFilter.value) {
    list = list.filter((task) => task.type === typeFilter.value);
  }

  return list;
});

const selectedTask = computed(() =>
  tasks.value.find((task) => task.id === selectedTaskId.value) ?? null
);

const selectedRuns = computed(() =>
  selectedTaskId.value ? automationStore.runsByTaskId[selectedTaskId.value] ?? [] : []
);

const runsLoading = computed(
  () =>
    (selectedTaskId.value ? automationStore.runsStatusByTaskId[selectedTaskId.value] : "idle") ===
    "loading"
);

const currentRunStateLabel = computed(() => {
  if (automationStore.triggerState === "running") {
    return "正在触发";
  }
  if (runsLoading.value) {
    return "读取运行历史";
  }
  return automationStore.triggerState === "error" ? "触发异常" : "待命";
});

const selectedTaskBlockLabel = computed(() => {
  if (!selectedTask.value) {
    return "未选中";
  }
  if (!selectedTask.value.enabled) {
    return "任务已关闭";
  }
  if (selectedTask.value.last_run_status === "blocked") {
    return "最近一次运行被阻断";
  }
  return "可手动运行";
});

const selectedLogs = computed(() =>
  selectedRuns.value.flatMap((run) =>
    (run.log_text ?? "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => ({
        id: `${run.id}-${line}`,
        status: run.status,
        text: line
      }))
  )
);

const selectedTaskConfigPreview = computed(() => prettyJson(selectedTask.value?.config_json));

onMounted(() => {
  void automationStore.loadTasks();
});

watch(
  () => tasks.value.map((task) => task.id).join("|"),
  () => {
    if (!selectedTaskId.value && tasks.value.length > 0) {
      selectedTaskId.value = tasks.value[0].id;
    }
  },
  { immediate: true }
);

watch(
  () => selectedTaskId.value,
  (taskId) => {
    if (taskId) {
      void automationStore.loadRuns(taskId);
    }
  },
  { immediate: true }
);

function isTaskBlocked(task: TaskView): boolean {
  return !task.enabled || task.last_run_status === "blocked";
}

function taskStatusTone(task: TaskView): string {
  if (!task.enabled) {
    return "is-off";
  }
  if (task.last_run_status === "blocked") {
    return "is-blocked";
  }
  if (task.last_run_status === "failed") {
    return "is-error";
  }
  if (task.last_run_status === "running" || automationStore.triggerState === "running") {
    return "is-running";
  }
  return "is-on";
}

function taskStatusLabel(task: TaskView): string {
  if (!task.enabled) {
    return "已关闭";
  }
  if (!task.last_run_status) {
    return "待运行";
  }
  return task.last_run_status;
}

async function handleRunTask(id: string): Promise<void> {
  selectedTaskId.value = id;
  await automationStore.triggerTask(id);
}

async function handleCreateTask(): Promise<void> {
  if (!addForm.value.name.trim()) {
    return;
  }

  const input: AutomationTaskCreateInput = {
    name: addForm.value.name.trim(),
    type: addForm.value.type,
    cron_expr: addForm.value.cronExpr.trim() || null,
    config_json: addForm.value.configJson.trim() || null
  };

  const task = await automationStore.addTask(input);
  if (!task) {
    return;
  }

  selectedTaskId.value = task.id;
  addForm.value = {
    name: "",
    type: "collect",
    cronExpr: "",
    configJson: ""
  };
  showAddTask.value = false;
}

function prettyJson(value: string | null): string {
  if (!value) {
    return "未配置";
  }

  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}

function formatDate(value: string | null): string {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString("zh-CN");
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return `${date.toLocaleDateString("zh-CN")} ${date.toLocaleTimeString("zh-CN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit"
  })}`;
}
</script>

<style scoped>
.automation-console {
  display: grid;
  gap: 16px;
  min-height: 100%;
  padding: 20px 24px 24px;
}

.automation-console__header {
  display: grid;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.automation-console__headline {
  display: grid;
  gap: 8px;
  max-width: 860px;
}

.automation-console__eyebrow {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.automation-console__headline h1,
.automation-console__workspace-head h2,
.automation-console__drawer-head h2,
.automation-console__detail-empty h2,
.automation-console__empty h2 {
  margin: 0;
}

.automation-console__summary {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.automation-console__summary--compact {
  max-width: 780px;
}

.automation-console__metrics {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.automation-console__metric,
.automation-console__state-tile {
  display: grid;
  gap: 4px;
  padding: 14px 16px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
}

.automation-console__metric span,
.automation-console__state-tile span,
.automation-console__task-meta,
.automation-console__lane-head span,
.automation-console__run-meta {
  color: var(--text-secondary);
  font-size: 12px;
}

.automation-console__metric strong,
.automation-console__state-tile strong {
  font-size: 18px;
  line-height: 1.2;
}

.automation-console__banner {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  align-items: center;
  padding: 12px 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 90%, transparent);
}

.automation-console__banner--error {
  border-color: color-mix(in srgb, var(--status-error) 30%, var(--border-default));
  color: var(--status-error);
}

.automation-console__banner--loading {
  border-color: color-mix(in srgb, var(--brand-primary) 24%, var(--border-default));
}

.automation-console__banner-status,
.automation-console__inline-flag,
.automation-console__status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.5;
}

.automation-console__banner-status,
.automation-console__status-pill.is-on {
  background: color-mix(in srgb, var(--status-success) 16%, transparent);
  color: var(--status-success);
}

.automation-console__status-pill.is-off,
.automation-console__inline-flag.is-off {
  background: color-mix(in srgb, var(--text-muted) 18%, transparent);
  color: var(--text-muted);
}

.automation-console__status-pill.is-blocked,
.automation-console__inline-flag.is-blocked {
  background: color-mix(in srgb, var(--status-warning) 18%, transparent);
  color: var(--status-warning);
}

.automation-console__status-pill.is-error {
  background: color-mix(in srgb, var(--status-error) 18%, transparent);
  color: var(--status-error);
}

.automation-console__status-pill.is-running {
  background: color-mix(in srgb, var(--brand-primary) 18%, transparent);
  color: var(--brand-primary);
}

.automation-console__body {
  display: grid;
  grid-template-columns: minmax(320px, 360px) minmax(0, 1fr);
  gap: 16px;
  min-height: 0;
}

.automation-console__rail,
.automation-console__workspace {
  min-width: 0;
}

.automation-console__rail {
  display: grid;
  align-content: start;
  gap: 12px;
}

.automation-console__rail-toolbar {
  display: grid;
  gap: 10px;
  padding: 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.automation-console__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.automation-console__chip,
.automation-console__primary,
.automation-console__secondary,
.automation-console__ghost,
.automation-console__icon-button {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  cursor: pointer;
  font: inherit;
  transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease, transform 80ms ease;
}

.automation-console__chip {
  padding: 6px 10px;
  background: transparent;
  color: var(--text-secondary);
}

.automation-console__chip--soft {
  border-color: transparent;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
}

.automation-console__chip--active {
  background: color-mix(in srgb, var(--brand-primary) 12%, transparent);
  border-color: color-mix(in srgb, var(--brand-primary) 26%, var(--border-default));
  color: var(--brand-primary);
}

.automation-console__primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 14px;
  background: var(--brand-primary);
  color: #000;
  font-weight: 700;
}

.automation-console__secondary,
.automation-console__ghost {
  min-height: 32px;
  padding: 0 12px;
  background: transparent;
  color: var(--text-primary);
}

.automation-console__ghost {
  padding-inline: 10px;
}

.automation-console__secondary:disabled,
.automation-console__ghost:disabled,
.automation-console__primary:disabled,
.automation-console__icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.automation-console__primary:hover,
.automation-console__secondary:hover,
.automation-console__ghost:hover,
.automation-console__icon-button:hover,
.automation-console__task:hover {
  border-color: color-mix(in srgb, var(--brand-primary) 26%, var(--border-default));
}

.automation-console__task-list {
  display: grid;
  gap: 10px;
  min-height: 0;
}

.automation-console__task {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
  text-align: left;
  color: var(--text-primary);
}

.automation-console__task--active {
  border-color: color-mix(in srgb, var(--brand-primary) 34%, var(--border-default));
  background: color-mix(in srgb, var(--brand-primary) 8%, var(--surface-secondary));
}

.automation-console__task--disabled {
  opacity: 0.88;
}

.automation-console__task--blocked {
  border-color: color-mix(in srgb, var(--status-warning) 30%, var(--border-default));
}

.automation-console__task-row,
.automation-console__task-footer,
.automation-console__workspace-head,
.automation-console__lane-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.automation-console__task-title {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.automation-console__task-title strong {
  font-size: 14px;
}

.automation-console__task-title span {
  color: var(--text-secondary);
  font-size: 12px;
}

.automation-console__task-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.automation-console__inline-flag {
  font-size: 11px;
}

.automation-console__workspace {
  display: grid;
  gap: 14px;
  align-content: start;
  min-height: 0;
}

.automation-console__workspace-head {
  padding: 16px 18px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.automation-console__workspace-head h2 {
  font-size: 20px;
}

.automation-console__workspace-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.automation-console__state-row {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.automation-console__lane {
  display: grid;
  gap: 12px;
  padding: 16px 18px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.automation-console__lane-head h3 {
  margin: 0;
  font-size: 14px;
}

.automation-console__run-list {
  display: grid;
  gap: 10px;
}

.automation-console__run {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
}

.automation-console__run--blocked {
  border-color: color-mix(in srgb, var(--status-warning) 30%, var(--border-default));
}

.automation-console__run-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
}

.automation-console__run-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.automation-console__terminal {
  min-height: 180px;
  padding: 14px;
  border-radius: 8px;
  background: #0c1016;
  border: 1px solid rgba(255, 255, 255, 0.06);
  font-family: var(--font-family-mono);
  font-size: 12px;
  line-height: 1.8;
}

.automation-console__terminal-line {
  color: var(--brand-primary);
  white-space: pre-wrap;
}

.automation-console__terminal-line--muted {
  color: var(--text-muted);
}

.automation-console__terminal-line--blocked {
  color: var(--status-warning);
}

.automation-console__config {
  display: grid;
  gap: 10px;
}

.automation-console__config-row {
  display: grid;
  gap: 6px;
}

.automation-console__config-row span {
  color: var(--text-secondary);
  font-size: 12px;
}

.automation-console__config-row strong,
.automation-console__config-row pre {
  margin: 0;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.automation-console__detail-empty,
.automation-console__empty {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 36px 24px;
  border: 1px dashed var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  text-align: center;
}

.automation-console__empty--inline {
  padding: 24px 18px;
}

.automation-console__empty-icon {
  font-size: 40px;
  color: var(--brand-primary);
}

.automation-console__empty h2,
.automation-console__detail-empty h2 {
  font-size: 16px;
}

.automation-console__drawer {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  justify-content: flex-end;
  background: rgba(0, 0, 0, 0.52);
}

.automation-console__drawer-panel {
  display: grid;
  grid-template-rows: auto 1fr;
  width: min(440px, 100%);
  height: 100%;
  background: var(--bg-elevated);
  border-left: 1px solid var(--border-default);
}

.automation-console__drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 18px 14px;
  border-bottom: 1px solid var(--border-default);
}

.automation-console__drawer-body {
  display: grid;
  gap: 14px;
  padding: 16px 18px 18px;
  overflow-y: auto;
}

.automation-console__field {
  display: grid;
  gap: 8px;
}

.automation-console__field span {
  color: var(--text-secondary);
  font-size: 12px;
}

.automation-console__field input,
.automation-console__field select,
.automation-console__field textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-primary);
  font: inherit;
}

.automation-console__field textarea {
  resize: vertical;
}

.automation-console__drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 6px;
}

.automation-console__icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  color: var(--text-secondary);
}

@media (max-width: 1180px) {
  .automation-console__body {
    grid-template-columns: 1fr;
  }

  .automation-console__metrics,
  .automation-console__state-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .automation-console {
    padding-inline: 16px;
  }

  .automation-console__metrics,
  .automation-console__state-row {
    grid-template-columns: 1fr;
  }

  .automation-console__task-row,
  .automation-console__task-footer,
  .automation-console__workspace-head,
  .automation-console__lane-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
