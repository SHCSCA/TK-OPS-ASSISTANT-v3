<template>
  <ProjectContextGuard>
    <div class="render-console" data-testid="render-console">
      <header class="render-console__header">
        <div class="render-console__headline">
          <p class="render-console__eyebrow">导出链路</p>
          <h1>渲染与导出中心</h1>
          <p class="render-console__summary">
            渲染任务、输出路径和取消回执都来自 Runtime。没有真实项目绑定或输出结果时，页面会直接给出受限提示。
          </p>
        </div>

        <div class="render-console__metrics">
          <article class="render-console__metric">
            <span>任务总数</span>
            <strong>{{ tasks.length }}</strong>
          </article>
          <article class="render-console__metric">
            <span>排队中</span>
            <strong>{{ queueCount }}</strong>
          </article>
          <article class="render-console__metric">
            <span>渲染中</span>
            <strong>{{ runningCount }}</strong>
          </article>
          <article class="render-console__metric">
            <span>项目绑定</span>
            <strong>{{ projectBindingLabel }}</strong>
          </article>
        </div>
      </header>

      <div v-if="rendersStore.error" class="render-console__banner render-console__banner--error">
        {{ rendersStore.error }}
      </div>
      <div v-else-if="isLoading" class="render-console__banner render-console__banner--loading">
        正在读取渲染任务。
      </div>
      <div v-else-if="projectBlockReason" class="render-console__banner render-console__banner--blocked">
        <strong>阻断提示：</strong>
        <span>{{ projectBlockReason }}</span>
      </div>

      <main class="render-console__body">
        <aside class="render-console__rail">
          <div class="render-console__rail-toolbar">
            <button class="render-console__primary" type="button" :disabled="createDisabled" @click="handleNewTask">
              <span class="material-symbols-outlined">add_task</span>
              新建渲染任务
            </button>
            <div class="render-console__chips" aria-label="渲染状态筛选">
              <button
                v-for="tab in statusTabs"
                :key="tab.value"
                type="button"
                class="render-console__chip"
                :class="{ 'render-console__chip--active': currentFilter === tab.value }"
                @click="currentFilter = tab.value"
              >
                {{ tab.label }}
              </button>
            </div>
          </div>

          <div v-if="isEmpty" class="render-console__empty" data-testid="render-empty-state">
            <span class="material-symbols-outlined render-console__empty-icon">movie_edit</span>
            <h2>还没有渲染任务</h2>
            <p>从当前项目创建真实导出任务后，这里会显示进度、状态和输出路径。</p>
          </div>

          <div v-else class="render-console__task-list" data-testid="render-task-list">
            <button
              v-for="task in filteredTasks"
              :key="task.id"
              type="button"
              class="render-console__task"
              :class="{
                'render-console__task--active': selectedTaskId === task.id,
                'render-console__task--blocked': isTaskBlocked(task)
              }"
              @click="selectedTaskId = task.id"
            >
              <div class="render-console__task-row">
                <div class="render-console__task-title">
                  <strong>{{ task.projectName }}</strong>
                  <span>{{ task.fileName }}</span>
                </div>
                <span class="render-console__status-pill" :class="taskTone(task)">
                  {{ taskStatusLabel(task) }}
                </span>
              </div>

              <div v-if="task.status === 'running' || task.status === 'pending'" class="render-console__progress">
                <div class="render-console__progress-bar">
                  <div class="render-console__progress-fill" :style="{ width: `${task.progress}%` }"></div>
                </div>
                <span>{{ task.progress }}%</span>
              </div>

              <div class="render-console__task-meta">
                <span>{{ task.preset }}</span>
                <span>{{ task.format }}</span>
                <span>{{ formatDateTime(task.createdAt) }}</span>
              </div>

              <div class="render-console__task-meta" v-if="task.outputPath">
                <span>输出 {{ task.outputPath }}</span>
              </div>
            </button>
          </div>
        </aside>

        <section class="render-console__workspace" data-testid="render-task-detail">
          <template v-if="selectedTask">
            <div class="render-console__workspace-head">
              <div>
                <p class="render-console__eyebrow">当前任务</p>
                <h2>{{ selectedTask.projectName }} / {{ selectedTask.fileName }}</h2>
                <p class="render-console__summary render-console__summary--compact">
                  预设 {{ selectedTask.preset }}，格式 {{ selectedTask.format }}，进度 {{ selectedTask.progress }}%。
                </p>
              </div>

              <div class="render-console__workspace-actions">
                <span class="render-console__status-pill" :class="taskTone(selectedTask)">
                  {{ taskStatusLabel(selectedTask) }}
                </span>
                <button
                  class="render-console__secondary"
                  type="button"
                  :disabled="cancelDisabled"
                  @click="handleCancel(selectedTask.id)"
                >
                  {{ selectedTask.status === 'running' || selectedTask.status === 'pending' ? '取消任务' : '取消不可用' }}
                </button>
                <button class="render-console__ghost" type="button" @click="handleDelete(selectedTask.id)">
                  删除记录
                </button>
              </div>
            </div>

            <div class="render-console__state-row">
              <article class="render-console__state-tile">
                <span>输出路径</span>
                <strong>{{ selectedTask.outputPath || "未生成" }}</strong>
              </article>
              <article class="render-console__state-tile">
                <span>开始时间</span>
                <strong>{{ selectedTask.startedAt ? formatDateTime(selectedTask.startedAt) : "未开始" }}</strong>
              </article>
              <article class="render-console__state-tile">
                <span>完成时间</span>
                <strong>{{ selectedTask.finishedAt ? formatDateTime(selectedTask.finishedAt) : "未完成" }}</strong>
              </article>
              <article class="render-console__state-tile">
                <span>阻断语义</span>
                <strong>{{ taskBlockLabel(selectedTask) }}</strong>
              </article>
            </div>

            <section class="render-console__lane">
              <div class="render-console__lane-head">
                <h3>任务参数</h3>
                <span>{{ selectedTask.status }}</span>
              </div>
              <div class="render-console__binding-grid">
                <div class="render-console__binding-row">
                  <span>项目 ID</span>
                  <strong>{{ selectedTask.projectId || "未绑定" }}</strong>
                </div>
                <div class="render-console__binding-row">
                  <span>项目名称</span>
                  <strong>{{ selectedTask.projectName }}</strong>
                </div>
                <div class="render-console__binding-row">
                  <span>预设</span>
                  <strong>{{ selectedTask.preset }}</strong>
                </div>
                <div class="render-console__binding-row">
                  <span>格式</span>
                  <strong>{{ selectedTask.format }}</strong>
                </div>
              </div>
            </section>

            <section class="render-console__lane">
              <div class="render-console__lane-head">
                <h3>执行说明</h3>
                <span>{{ selectedTask.errorMessage ? "错误" : "正常" }}</span>
              </div>
              <div v-if="selectedTask.errorMessage" class="render-console__note render-console__note--error">
                {{ selectedTask.errorMessage }}
              </div>
              <div v-else class="render-console__note">
                {{
                  taskBlockLabel(selectedTask) === "可执行"
                    ? "任务已经进入真实队列，进度和输出路径由 Runtime 更新。"
                    : "当前任务存在阻断或输出缺失，按钮会根据真实状态禁用。"
                }}
              </div>
            </section>

            <section class="render-console__lane">
              <div class="render-console__lane-head">
                <h3>取消回执</h3>
                <span>{{ rendersStore.lastCancelResult?.status || "未取消" }}</span>
              </div>
              <div v-if="rendersStore.lastCancelResult" class="render-console__note">
                {{ rendersStore.lastCancelResult.message }}
              </div>
              <div v-else class="render-console__empty render-console__empty--inline">
                取消任务后，这里会显示 Runtime 返回的真实回执。
              </div>
            </section>
          </template>

          <div v-else class="render-console__detail-empty">
            <span class="material-symbols-outlined render-console__empty-icon">output</span>
            <h2>选择一个渲染任务查看导出链路</h2>
            <p>这里会显示队列状态、输出路径和取消结果。</p>
          </div>
        </section>
      </main>

      <div v-if="showDrawer" class="render-console__drawer" @click.self="showDrawer = false">
        <section class="render-console__drawer-panel">
          <div class="render-console__drawer-head">
            <div>
              <p class="render-console__eyebrow">新建任务</p>
              <h2>创建渲染任务</h2>
            </div>
            <button class="render-console__icon-button" type="button" @click="showDrawer = false">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <div class="render-console__drawer-body">
            <label class="render-console__field">
              <span>项目 ID</span>
              <input v-model="createForm.projectId" type="text" :placeholder="projectIdPlaceholder" />
            </label>
            <label class="render-console__field">
              <span>项目名称</span>
              <input v-model="createForm.projectName" type="text" :placeholder="projectNamePlaceholder" />
            </label>
            <label class="render-console__field">
              <span>预设</span>
              <input v-model="createForm.preset" type="text" placeholder="1080p" />
            </label>
            <label class="render-console__field">
              <span>格式</span>
              <input v-model="createForm.format" type="text" placeholder="mp4" />
            </label>

            <div class="render-console__drawer-actions">
              <button class="render-console__secondary" type="button" @click="showDrawer = false">取消</button>
              <button class="render-console__primary" type="button" :disabled="createDisabled" @click="handleCreateFromDrawer">
                保存任务
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { useProjectStore } from "@/stores/project";
import { useRendersStore } from "@/stores/renders";
import type { RenderTaskCreateInput, RenderTaskDto } from "@/types/runtime";

type RenderTaskView = RenderTaskDto & {
  fileName: string;
  projectId: string | null;
  projectName: string;
  status: "pending" | "running" | "completed" | "failed";
};

type FilterValue = "all" | "queued" | "running" | "completed" | "failed";

const rendersStore = useRendersStore();
const projectStore = useProjectStore();
const currentFilter = ref<FilterValue>("all");
const selectedTaskId = ref<string | null>(null);
const showDrawer = ref(false);
const createForm = ref({
  projectId: "",
  projectName: "",
  preset: "1080p",
  format: "mp4"
});

const statusTabs: Array<{ label: string; value: FilterValue }> = [
  { label: "全部", value: "all" },
  { label: "排队", value: "queued" },
  { label: "渲染中", value: "running" },
  { label: "已完成", value: "completed" },
  { label: "失败", value: "failed" }
];

const tasks = computed<RenderTaskView[]>(() =>
  rendersStore.tasks.map((task) => ({
    ...task,
    fileName: task.output_path?.split(/[\\/]/).pop() || `${task.id}.${task.format}`,
    projectId: task.project_id,
    projectName: task.project_name || "未绑定项目",
    status: normalizeRenderStatus(task.status)
  }))
);

const filteredTasks = computed(() => {
  if (currentFilter.value === "all") {
    return tasks.value;
  }
  return tasks.value.filter((task) => task.status === currentFilter.value);
});

const selectedTask = computed(
  () => tasks.value.find((task) => task.id === selectedTaskId.value) ?? null
);
const queueCount = computed(() => tasks.value.filter((task) => task.status === "pending").length);
const runningCount = computed(() => tasks.value.filter((task) => task.status === "running").length);
const isLoading = computed(() => rendersStore.loading || rendersStore.viewState === "loading");
const isEmpty = computed(() => rendersStore.viewState === "empty" && !isLoading.value);
const hasProjectContext = computed(() => Boolean(projectStore.currentProject));
const createDisabled = computed(() => !hasProjectContext.value || isLoading.value);
const cancelDisabled = computed(
  () =>
    !selectedTask.value ||
    isLoading.value ||
    (selectedTask.value.status !== "running" && selectedTask.value.status !== "pending")
);
const projectBindingLabel = computed(() =>
  hasProjectContext.value ? projectStore.currentProject?.projectName || "已绑定" : "未绑定"
);
const projectIdPlaceholder = computed(() => projectStore.currentProject?.projectId || "project-1");
const projectNamePlaceholder = computed(() => projectStore.currentProject?.projectName || "当前项目名称");
const projectBlockReason = computed(() => {
  if (!hasProjectContext.value) {
    return "当前没有项目上下文，无法创建新的渲染任务。";
  }
  return "";
});

onMounted(() => {
  void rendersStore.loadTasks();
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
  () => projectStore.currentProject,
  (project) => {
    if (!project) {
      return;
    }

    if (!createForm.value.projectId) {
      createForm.value.projectId = project.projectId;
    }
    if (!createForm.value.projectName) {
      createForm.value.projectName = project.projectName;
    }
  },
  { immediate: true }
);

function normalizeRenderStatus(status: string): RenderTaskView["status"] {
  if (status === "queued") return "pending";
  if (status === "running") return "running";
  if (status === "succeeded") return "completed";
  return "failed";
}

function isTaskBlocked(task: RenderTaskView): boolean {
  return (!task.projectId && task.status !== "completed") || (!task.output_path && task.status === "pending");
}

function taskTone(task: RenderTaskView): string {
  if (task.status === "running") {
    return "is-running";
  }
  if (task.status === "completed") {
    return "is-success";
  }
  if (task.status === "failed") {
    return "is-error";
  }
  if (isTaskBlocked(task)) {
    return "is-blocked";
  }
  return "is-muted";
}

function taskStatusLabel(task: RenderTaskView): string {
  if (task.status === "pending") return "排队中";
  if (task.status === "running") return "渲染中";
  if (task.status === "completed") return "已完成";
  return "失败";
}

function taskBlockLabel(task: RenderTaskView): string {
  if (!task.projectId) {
    return "未绑定项目";
  }
  if (!task.output_path && task.status === "pending") {
    return "等待生成输出路径";
  }
  if (task.status === "failed") {
    return "任务失败";
  }
  return "可执行";
}

async function handleNewTask(): Promise<void> {
  if (!projectStore.currentProject) {
    return;
  }

  const task = await rendersStore.addTask({
    format: createForm.value.format.trim() || "mp4",
    preset: createForm.value.preset.trim() || "1080p",
    project_id: createForm.value.projectId.trim() || projectStore.currentProject.projectId,
    project_name: createForm.value.projectName.trim() || projectStore.currentProject.projectName
  });

  if (task) {
    selectedTaskId.value = task.id;
    showDrawer.value = false;
  }
}

async function handleCreateFromDrawer(): Promise<void> {
  await handleNewTask();
}

async function handleDelete(id: string): Promise<void> {
  await rendersStore.removeTask(id);
  if (selectedTaskId.value === id) {
    selectedTaskId.value = null;
  }
}

async function handleCancel(id: string): Promise<void> {
  await rendersStore.cancel(id);
}

function formatDateTime(value: string): string {
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
.render-console {
  display: grid;
  gap: 16px;
  min-height: 100%;
  padding: 20px 24px 24px;
}

.render-console__header,
.render-console__workspace-head,
.render-console__lane,
.render-console__rail-toolbar {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.render-console__header {
  display: grid;
  gap: 16px;
  padding: 18px 20px;
}

.render-console__headline {
  display: grid;
  gap: 8px;
  max-width: 860px;
}

.render-console__eyebrow {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.render-console__headline h1,
.render-console__workspace-head h2,
.render-console__drawer-head h2,
.render-console__detail-empty h2,
.render-console__empty h2 {
  margin: 0;
}

.render-console__summary {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.render-console__summary--compact {
  max-width: 780px;
}

.render-console__metrics {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.render-console__metric,
.render-console__state-tile {
  display: grid;
  gap: 4px;
  padding: 14px 16px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
}

.render-console__metric span,
.render-console__state-tile span,
.render-console__task-meta,
.render-console__lane-head span {
  color: var(--text-secondary);
  font-size: 12px;
}

.render-console__metric strong,
.render-console__state-tile strong {
  font-size: 18px;
  line-height: 1.2;
}

.render-console__banner {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  align-items: center;
  padding: 12px 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
}

.render-console__banner--error {
  color: var(--status-error);
  border-color: color-mix(in srgb, var(--status-error) 30%, var(--border-default));
}

.render-console__banner--loading {
  border-color: color-mix(in srgb, var(--brand-primary) 24%, var(--border-default));
}

.render-console__banner--blocked {
  border-color: color-mix(in srgb, var(--status-warning) 30%, var(--border-default));
  color: var(--status-warning);
}

.render-console__status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.5;
}

.render-console__status-pill.is-success {
  background: color-mix(in srgb, var(--status-success) 16%, transparent);
  color: var(--status-success);
}

.render-console__status-pill.is-error {
  background: color-mix(in srgb, var(--status-error) 18%, transparent);
  color: var(--status-error);
}

.render-console__status-pill.is-blocked {
  background: color-mix(in srgb, var(--status-warning) 18%, transparent);
  color: var(--status-warning);
}

.render-console__status-pill.is-running {
  background: color-mix(in srgb, var(--brand-primary) 18%, transparent);
  color: var(--brand-primary);
}

.render-console__status-pill.is-muted {
  background: color-mix(in srgb, var(--text-muted) 18%, transparent);
  color: var(--text-muted);
}

.render-console__body {
  display: grid;
  grid-template-columns: minmax(320px, 380px) minmax(0, 1fr);
  gap: 16px;
  min-height: 0;
}

.render-console__rail {
  display: grid;
  gap: 12px;
  align-content: start;
}

.render-console__rail-toolbar {
  display: grid;
  gap: 12px;
  padding: 16px;
}

.render-console__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.render-console__chip,
.render-console__primary,
.render-console__secondary,
.render-console__ghost,
.render-console__icon-button {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  cursor: pointer;
  font: inherit;
  transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease, transform 80ms ease;
}

.render-console__chip {
  padding: 6px 10px;
  background: transparent;
  color: var(--text-secondary);
}

.render-console__chip--active {
  background: color-mix(in srgb, var(--brand-primary) 12%, transparent);
  border-color: color-mix(in srgb, var(--brand-primary) 28%, var(--border-default));
  color: var(--brand-primary);
}

.render-console__primary {
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

.render-console__secondary,
.render-console__ghost {
  min-height: 32px;
  padding: 0 12px;
  background: transparent;
  color: var(--text-primary);
}

.render-console__secondary:disabled,
.render-console__ghost:disabled,
.render-console__primary:disabled,
.render-console__icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.render-console__task-list {
  display: grid;
  gap: 10px;
}

.render-console__task {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
  text-align: left;
  color: var(--text-primary);
}

.render-console__task--active {
  border-color: color-mix(in srgb, var(--brand-primary) 34%, var(--border-default));
  background: color-mix(in srgb, var(--brand-primary) 8%, var(--surface-secondary));
}

.render-console__task--blocked {
  border-color: color-mix(in srgb, var(--status-warning) 30%, var(--border-default));
}

.render-console__task-row,
.render-console__workspace-head,
.render-console__lane-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.render-console__task-title {
  display: grid;
  gap: 4px;
}

.render-console__task-title strong {
  font-size: 14px;
}

.render-console__task-title span {
  color: var(--text-secondary);
  font-size: 12px;
}

.render-console__progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.render-console__progress-bar {
  flex: 1;
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--text-muted) 22%, transparent);
}

.render-console__progress-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--brand-primary);
}

.render-console__task-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.render-console__workspace {
  display: grid;
  gap: 14px;
  align-content: start;
}

.render-console__workspace-head {
  padding: 16px 18px;
}

.render-console__workspace-actions {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.render-console__state-row {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.render-console__lane {
  display: grid;
  gap: 12px;
  padding: 16px 18px;
}

.render-console__lane-head h3 {
  margin: 0;
  font-size: 14px;
}

.render-console__binding-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.render-console__binding-row,
.render-console__note {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
}

.render-console__binding-row span {
  color: var(--text-secondary);
  font-size: 12px;
}

.render-console__note {
  color: var(--text-secondary);
  line-height: 1.7;
}

.render-console__note--error {
  color: var(--status-error);
  border-color: color-mix(in srgb, var(--status-error) 24%, var(--border-default));
}

.render-console__empty,
.render-console__detail-empty {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 36px 24px;
  border: 1px dashed var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  text-align: center;
}

.render-console__empty--inline {
  padding: 24px 18px;
}

.render-console__empty-icon {
  font-size: 40px;
  color: var(--brand-primary);
}

.render-console__drawer {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  justify-content: flex-end;
  background: rgba(0, 0, 0, 0.52);
}

.render-console__drawer-panel {
  display: grid;
  grid-template-rows: auto 1fr;
  width: min(440px, 100%);
  height: 100%;
  background: var(--bg-elevated);
  border-left: 1px solid var(--border-default);
}

.render-console__drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 18px 14px;
  border-bottom: 1px solid var(--border-default);
}

.render-console__drawer-body {
  display: grid;
  gap: 14px;
  padding: 16px 18px 18px;
  overflow-y: auto;
}

.render-console__field {
  display: grid;
  gap: 8px;
}

.render-console__field span {
  color: var(--text-secondary);
  font-size: 12px;
}

.render-console__field input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-primary);
  font: inherit;
}

.render-console__drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 6px;
}

.render-console__icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  color: var(--text-secondary);
}

@media (max-width: 1180px) {
  .render-console__body {
    grid-template-columns: 1fr;
  }

  .render-console__metrics,
  .render-console__state-row,
  .render-console__binding-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .render-console {
    padding-inline: 16px;
  }

  .render-console__metrics,
  .render-console__state-row,
  .render-console__binding-grid {
    grid-template-columns: 1fr;
  }

  .render-console__task-row,
  .render-console__workspace-head,
  .render-console__lane-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
