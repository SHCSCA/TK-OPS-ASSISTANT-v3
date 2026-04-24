<template>
  <ProjectContextGuard>
    <div class="page-container h-full">
      <header class="page-header">
        <div class="page-header__crumb">首页 / 执行与治理</div>
        <div class="page-header__row">
          <div>
            <h1 class="page-header__title">渲染与导出中心</h1>
            <div class="page-header__subtitle">渲染任务、输出路径和取消回执都来自 Runtime。没有真实项目绑定或输出结果时，页面会直接给出受限提示。</div>
          </div>
        </div>
      </header>

      <div v-if="rendersStore.error" class="dashboard-alert" data-tone="danger">
        <span class="material-symbols-outlined">error</span>
        <span>{{ rendersStore.error }}</span>
      </div>
      <div v-else-if="isLoading" class="dashboard-alert" data-tone="brand">
        <span class="material-symbols-outlined spinning">sync</span>
        <span>正在读取渲染任务...</span>
      </div>
      <div v-else-if="projectBlockReason" class="dashboard-alert" data-tone="warning">
        <span class="material-symbols-outlined">warning</span>
        <span><strong>阻断提示：</strong>{{ projectBlockReason }}</span>
      </div>

      <div class="summary-grid">
        <Card class="summary-card">
          <span class="sc-label">任务总数</span>
          <strong class="sc-val">{{ tasks.length }}</strong>
        </Card>
        <Card class="summary-card">
          <span class="sc-label">排队中</span>
          <strong class="sc-val">{{ queueCount }}</strong>
        </Card>
        <Card class="summary-card">
          <span class="sc-label">渲染中</span>
          <strong class="sc-val">{{ runningCount }}</strong>
        </Card>
        <Card class="summary-card">
          <span class="sc-label">项目绑定</span>
          <strong class="sc-val">{{ projectBindingLabel }}</strong>
        </Card>
      </div>

      <div class="workspace-grid">
        <aside class="workspace-rail">
          <Card class="rail-card h-full">
            <div class="rail-card__header flex-col align-start gap-3">
              <div style="display: flex; justify-content: space-between; width: 100%;">
                <h3>渲染任务</h3>
                <Button variant="primary" size="sm" :disabled="createDisabled" @click="showDrawer = true">
                  <template #leading><span class="material-symbols-outlined">add_task</span></template>
                  新建任务
                </Button>
              </div>

              <div class="filter-chips">
                <Chip
                  v-for="tab in statusTabs"
                  :key="tab.value"
                  :variant="currentFilter === tab.value ? 'brand' : 'default'"
                  clickable
                  @click="currentFilter = tab.value"
                >
                  {{ tab.label }}
                </Chip>
              </div>
            </div>

            <div class="rail-card__body no-padding scroll-area">
              <div v-if="isEmpty" class="empty-state">
                <span class="material-symbols-outlined">movie_edit</span>
                <strong>还没有渲染任务</strong>
                <p>从当前项目创建真实导出任务后，这里会显示进度、状态和输出路径。</p>
              </div>
              <div v-else class="task-list">
                <transition-group name="task-list-transition">
                  <button
                    v-for="task in filteredTasks"
                    :key="task.id"
                    class="task-card"
                    :class="{
                      'is-selected': selectedTaskId === task.id,
                      'is-blocked': isTaskBlocked(task)
                    }"
                    @click="selectedTaskId = task.id"
                  >
                    <div class="tc-head">
                      <div class="tc-title">
                        <strong>{{ task.projectName }}</strong>
                        <span>{{ task.fileName }}</span>
                      </div>
                      <Chip size="sm" :variant="taskTone(task)">{{ taskStatusLabel(task) }}</Chip>
                    </div>
                    
                    <div v-if="task.status === 'running' || task.status === 'pending'" class="tc-progress">
                      <div class="progress-bar">
                        <div class="progress-fill" :style="{ width: `${task.progress}%` }"></div>
                      </div>
                      <span>{{ task.progress }}%</span>
                    </div>

                    <div class="tc-meta">
                      <span>{{ task.preset }}</span>
                      <span>{{ task.format }}</span>
                      <span>{{ formatDateTime(task.createdAt) }}</span>
                    </div>
                    <div class="tc-meta" v-if="task.outputPath">
                      <span>输出 {{ task.outputPath }}</span>
                    </div>
                  </button>
                </transition-group>
              </div>
            </div>
          </Card>
        </aside>

        <main class="workspace-main">
          <Card class="detail-card h-full scroll-area" v-if="selectedTask">
            <div v-if="selectedTask.status === 'running'" class="ai-flow-bar" />
            <div class="detail-card__header">
              <div>
                <p class="eyebrow">当前任务</p>
                <h3>{{ selectedTask.projectName }} / {{ selectedTask.fileName }}</h3>
                <p class="summary">预设 {{ selectedTask.preset }}，格式 {{ selectedTask.format }}，进度 {{ selectedTask.progress }}%。</p>
              </div>
              <div class="actions">
                <Chip :variant="taskTone(selectedTask)">{{ taskStatusLabel(selectedTask) }}</Chip>
                <Button variant="secondary" :disabled="cancelDisabled" @click="handleCancel(selectedTask.id)">
                  {{ selectedTask.status === 'running' || selectedTask.status === 'pending' ? '取消任务' : '取消不可用' }}
                </Button>
                <Button variant="danger" @click="handleDelete(selectedTask.id)">删除记录</Button>
              </div>
            </div>

            <div class="detail-card__body">
              <div class="metric-grid cols-4">
                <div class="metric-card">
                  <span>输出路径</span>
                  <strong>{{ selectedTask.outputPath || "未生成" }}</strong>
                </div>
                <div class="metric-card">
                  <span>开始时间</span>
                  <strong>{{ selectedTask.startedAt ? formatDateTime(selectedTask.startedAt) : "未开始" }}</strong>
                </div>
                <div class="metric-card">
                  <span>完成时间</span>
                  <strong>{{ selectedTask.finishedAt ? formatDateTime(selectedTask.finishedAt) : "未完成" }}</strong>
                </div>
                <div class="metric-card">
                  <span>阻断语义</span>
                  <strong>{{ taskBlockLabel(selectedTask) }}</strong>
                </div>
              </div>

              <div class="lane">
                <div class="lane-head">
                  <h4>任务参数</h4>
                  <Chip size="sm">{{ selectedTask.status }}</Chip>
                </div>
                <div class="config-grid cols-2">
                  <div class="cfg-row"><span>项目 ID</span><strong>{{ selectedTask.projectId || "未绑定" }}</strong></div>
                  <div class="cfg-row"><span>项目名称</span><strong>{{ selectedTask.projectName }}</strong></div>
                  <div class="cfg-row"><span>预设</span><strong>{{ selectedTask.preset }}</strong></div>
                  <div class="cfg-row"><span>格式</span><strong>{{ selectedTask.format }}</strong></div>
                </div>
              </div>

              <div class="lane">
                <div class="lane-head">
                  <h4>执行说明</h4>
                  <Chip size="sm" :variant="selectedTask.errorMessage ? 'danger' : 'neutral'">{{ selectedTask.errorMessage ? "错误" : "正常" }}</Chip>
                </div>
                <div v-if="selectedTask.errorMessage" class="lane-note is-error">{{ selectedTask.errorMessage }}</div>
                <div v-else class="lane-note">
                  {{ taskBlockLabel(selectedTask) === "可执行" ? "任务已经进入真实队列，进度和输出路径由 Runtime 更新。" : "当前任务存在阻断或输出缺失，按钮会根据真实状态禁用。" }}
                </div>
              </div>

              <div class="lane">
                <div class="lane-head">
                  <h4>取消回执</h4>
                  <Chip size="sm">{{ rendersStore.lastCancelResult?.status || "未取消" }}</Chip>
                </div>
                <div v-if="rendersStore.lastCancelResult" class="lane-note">{{ rendersStore.lastCancelResult.message }}</div>
                <div v-else class="lane-empty">取消任务后，这里会显示 Runtime 返回的真实回执。</div>
              </div>
            </div>
          </Card>
          
          <Card class="detail-card empty-wrapper" v-else>
            <div class="empty-state">
              <span class="material-symbols-outlined">output</span>
              <strong>选择一个渲染任务查看导出链路</strong>
              <p>这里会显示队列状态、输出路径和取消结果。</p>
            </div>
          </Card>
        </main>
      </div>

      <!-- Drawer Modal -->
      <transition name="drawer">
        <div v-if="showDrawer" class="drawer-overlay" @click.self="showDrawer = false">
          <aside class="drawer-panel" @click.stop>
            <div class="drawer-panel__header">
              <div>
                <p class="drawer-panel__eyebrow">新建任务</p>
                <h2>创建渲染任务</h2>
              </div>
              <button class="drawer-panel__close" @click="showDrawer = false">
                <span class="material-symbols-outlined">close</span>
              </button>
            </div>
            <div class="drawer-panel__body">
              <form class="drawer-form" @submit.prevent="handleCreateFromDrawer">
                <div class="form-group">
                  <label>项目 ID</label>
                  <Input v-model="createForm.projectId" :placeholder="projectIdPlaceholder" required />
                </div>
                <div class="form-group">
                  <label>项目名称</label>
                  <Input v-model="createForm.projectName" :placeholder="projectNamePlaceholder" required />
                </div>
                <div class="form-group">
                  <label>预设</label>
                  <Input v-model="createForm.preset" placeholder="1080p" />
                </div>
                <div class="form-group">
                  <label>格式</label>
                  <Input v-model="createForm.format" placeholder="mp4" />
                </div>
                <div class="drawer-actions">
                  <Button variant="ghost" @click="showDrawer = false">取消</Button>
                  <Button variant="primary" type="submit" :disabled="createDisabled">保存任务</Button>
                </div>
              </form>
            </div>
          </aside>
        </div>
      </transition>
    </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { useProjectStore } from "@/stores/project";
import { useRendersStore } from "@/stores/renders";
import { useTaskBusStore } from "@/stores/task-bus";
import type { RenderTaskCreateInput, RenderTaskDto } from "@/types/runtime";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import Input from "@/components/ui/Input/Input.vue";

type RenderTaskView = RenderTaskDto & { fileName: string; projectId: string | null; projectName: string; status: "pending" | "running" | "completed" | "failed"; errorMessage?: string | null };
type FilterValue = "all" | "queued" | "running" | "completed" | "failed";

const rendersStore = useRendersStore();
const projectStore = useProjectStore();
const taskBusStore = useTaskBusStore();
const currentFilter = ref<FilterValue>("all");
const selectedTaskId = ref<string | null>(null);
const showDrawer = ref(false);
const createForm = ref({ projectId: "", projectName: "", preset: "1080p", format: "mp4" });

const statusTabs: Array<{ label: string; value: FilterValue }> = [
  { label: "全部", value: "all" }, { label: "排队", value: "queued" }, { label: "渲染中", value: "running" },
  { label: "已完成", value: "completed" }, { label: "失败", value: "failed" }
];

const tasks = computed<RenderTaskView[]>(() =>
  rendersStore.tasks.map((task) => {
    const liveTask = taskBusStore.tasks.get(task.id);
    const status = normalizeRenderStatus(liveTask?.status ?? task.status);
    const progress = liveTask?.progressPct ?? task.progress ?? 0;
    
    return {
      ...task,
      fileName: task.output_path?.split(/[\\/]/).pop() || `${task.id}.${task.format}`,
      projectId: task.project_id, 
      projectName: task.project_name || "未绑定项目", 
      status,
      progress,
      errorMessage: liveTask?.errorMessage ?? task.error_message
    };
  })
);

const filteredTasks = computed(() => {
  if (currentFilter.value === "all") return tasks.value;
  return tasks.value.filter((task) => task.status === currentFilter.value);
});

const selectedTask = computed(() => tasks.value.find((task) => task.id === selectedTaskId.value) ?? null);
const queueCount = computed(() => tasks.value.filter((task) => task.status === "pending").length);
const runningCount = computed(() => tasks.value.filter((task) => task.status === "running").length);
const isLoading = computed(() => rendersStore.loading || rendersStore.viewState === "loading");
const isEmpty = computed(() => rendersStore.viewState === "empty" && !isLoading.value);
const hasProjectContext = computed(() => Boolean(projectStore.currentProject));
const createDisabled = computed(() => !hasProjectContext.value || isLoading.value);
const cancelDisabled = computed(() => !selectedTask.value || isLoading.value || (selectedTask.value.status !== "running" && selectedTask.value.status !== "pending"));
const projectBindingLabel = computed(() => hasProjectContext.value ? projectStore.currentProject?.projectName || "已绑定" : "未绑定");
const projectIdPlaceholder = computed(() => projectStore.currentProject?.projectId || "project-1");
const projectNamePlaceholder = computed(() => projectStore.currentProject?.projectName || "当前项目名称");
const projectBlockReason = computed(() => !hasProjectContext.value ? "当前没有项目上下文，无法创建新的渲染任务。" : "");

onMounted(() => { 
  rendersStore.initializeWebSocket();
  void rendersStore.loadTasks(); 
});

watch(() => tasks.value.map((task) => task.id).join("|"), () => {
  if (!selectedTaskId.value && tasks.value.length > 0) selectedTaskId.value = tasks.value[0].id;
}, { immediate: true });

watch(() => projectStore.currentProject, (project) => {
  if (!project) return;
  if (!createForm.value.projectId) createForm.value.projectId = project.projectId;
  if (!createForm.value.projectName) createForm.value.projectName = project.projectName;
}, { immediate: true });

function normalizeRenderStatus(status: string): RenderTaskView["status"] {
  if (status === "queued") return "pending";
  if (status === "running") return "running";
  if (status === "succeeded") return "completed";
  return "failed";
}

function isTaskBlocked(task: RenderTaskView) {
  return (!task.projectId && task.status !== "completed") || (!task.output_path && task.status === "pending");
}

function taskTone(task: RenderTaskView) {
  if (task.status === "running") return "brand";
  if (task.status === "completed") return "success";
  if (task.status === "failed") return "danger";
  if (isTaskBlocked(task)) return "warning";
  return "neutral";
}

function taskStatusLabel(task: RenderTaskView) {
  if (task.status === "pending") return "排队中";
  if (task.status === "running") return "渲染中";
  if (task.status === "completed") return "已完成";
  return "失败";
}

function taskBlockLabel(task: RenderTaskView) {
  if (!task.projectId) return "未绑定项目";
  if (!task.output_path && task.status === "pending") return "等待生成输出路径";
  if (task.status === "failed") return "任务失败";
  return "可执行";
}

async function handleNewTask() {
  if (!projectStore.currentProject) return;
  const task = await rendersStore.addTask({
    format: createForm.value.format.trim() || "mp4", preset: createForm.value.preset.trim() || "1080p",
    project_id: createForm.value.projectId.trim() || projectStore.currentProject.projectId, project_name: createForm.value.projectName.trim() || projectStore.currentProject.projectName
  });
  if (task) { selectedTaskId.value = task.id; showDrawer.value = false; }
}

async function handleCreateFromDrawer() { await handleNewTask(); }
async function handleDelete(id: string) {
  await rendersStore.removeTask(id);
  if (selectedTaskId.value === id) selectedTaskId.value = null;
}
async function handleCancel(id: string) { await rendersStore.cancel(id); }
function formatDateTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : `${date.toLocaleDateString("zh-CN")} ${date.toLocaleTimeString("zh-CN", { hour12: false, hour: "2-digit", minute: "2-digit" })}`;
}
</script>

<style scoped src="./RenderExportCenterPage.css"></style>
