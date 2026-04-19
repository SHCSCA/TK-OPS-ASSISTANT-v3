<template>
  <div class="page-container h-full">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 执行与治理</div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">自动化执行中心</h1>
          <div class="page-header__subtitle">真实任务、运行记录和日志流都从 Runtime 读取。</div>
        </div>
      </div>
    </header>

    <div v-if="automationStore.error" class="dashboard-alert" data-tone="danger">
      <span class="material-symbols-outlined">error</span>
      <span>{{ automationStore.error }}</span>
    </div>
    <div v-else-if="isLoading" class="dashboard-alert" data-tone="brand">
      <span class="material-symbols-outlined spinning">sync</span>
      <span>正在读取自动化任务和运行日志...</span>
    </div>
    <div v-else-if="automationStore.lastTriggerResult" class="dashboard-alert" data-tone="success">
      <span class="material-symbols-outlined">check_circle</span>
      <span><strong>最近一次触发：</strong>{{ automationStore.lastTriggerResult.message }} ({{ automationStore.lastTriggerResult.status }})</span>
    </div>

    <div class="summary-grid">
      <Card class="summary-card">
        <span class="sc-label">任务总数</span>
        <strong class="sc-val">{{ tasks.length }}</strong>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">已启用</span>
        <strong class="sc-val">{{ enabledTaskCount }}</strong>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">已阻断</span>
        <strong class="sc-val">{{ blockedTaskCount }}</strong>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">最近触发</span>
        <strong class="sc-val">{{ triggerStateLabel }}</strong>
      </Card>
    </div>

    <div class="workspace-grid">
      <aside class="workspace-rail">
        <Card class="rail-card h-full">
          <div class="rail-card__header flex-col align-start gap-3">
            <div style="display: flex; justify-content: space-between; width: 100%;">
              <h3>任务列表</h3>
              <Button variant="primary" size="sm" @click="showAddTask = true">
                <template #leading><span class="material-symbols-outlined">add</span></template>
                新建任务
              </Button>
            </div>
            
            <div class="filter-chips">
              <Chip
                v-for="item in statusFilters"
                :key="item.value"
                :variant="statusFilter === item.value ? 'brand' : 'default'"
                clickable
                @click="statusFilter = item.value"
              >
                {{ item.label }}
              </Chip>
            </div>
            <div class="filter-chips">
              <Chip
                v-for="item in typeFilters"
                :key="item.value"
                :variant="typeFilter === item.value ? 'brand' : 'default'"
                clickable
                @click="typeFilter = typeFilter === item.value ? '' : item.value"
              >
                {{ item.label }}
              </Chip>
            </div>
          </div>

          <div class="rail-card__body no-padding scroll-area">
            <div v-if="isEmpty" class="empty-state">
              <span class="material-symbols-outlined">robot_2</span>
              <strong>暂时没有自动化任务</strong>
              <p>先创建一个任务，再查看运行记录、日志和阻断原因。</p>
            </div>
            <div v-else class="task-list">
              <button
                v-for="task in filteredTasks"
                :key="task.id"
                class="task-card"
                :class="{
                  'is-selected': selectedTaskId === task.id,
                  'is-disabled': !task.enabled,
                  'is-blocked': isTaskBlocked(task)
                }"
                @click="selectedTaskId = task.id"
              >
                <div class="tc-head">
                  <div class="tc-title">
                    <strong>{{ task.name }}</strong>
                    <span>{{ task.type }}</span>
                  </div>
                  <Chip size="sm" :variant="taskStatusTone(task)">{{ taskStatusLabel(task) }}</Chip>
                </div>
                <div class="tc-meta">
                  <span>Cron: {{ task.cron_expr || "未配置" }}</span>
                  <span>运行: {{ task.run_count }}</span>
                </div>
                <div class="tc-meta">
                  <span>最近: {{ task.last_run_at ? formatDate(task.last_run_at) : "从未" }}</span>
                  <span>状态: {{ task.last_run_status || "未知" }}</span>
                </div>
                <div class="tc-footer">
                  <span class="tc-flag" :class="task.enabled ? 'text-success' : 'text-muted'">
                    {{ task.enabled ? "已启用" : "已关闭" }}
                  </span>
                  <Button variant="ghost" size="sm" :disabled="isBusy" @click.stop="handleRunTask(task.id)">运行</Button>
                </div>
              </button>
            </div>
          </div>
        </Card>
      </aside>

      <main class="workspace-main">
        <Card class="detail-card h-full scroll-area" v-if="selectedTask">
          <div class="detail-card__header">
            <div>
              <p class="eyebrow">当前任务</p>
              <h3>{{ selectedTask.name }}</h3>
              <p class="summary">类型 {{ selectedTask.type }}，Cron {{ selectedTask.cron_expr || "未配置" }}，运行次数 {{ selectedTask.run_count }}。</p>
            </div>
            <div class="actions">
              <Chip :variant="taskStatusTone(selectedTask)">{{ taskStatusLabel(selectedTask) }}</Chip>
              <Button variant="secondary" :disabled="isBusy" @click="selectedTask.enabled ? handleRunTask(selectedTask.id) : undefined">
                {{ selectedTask.enabled ? "手动触发" : "任务已关闭" }}
              </Button>
            </div>
          </div>

          <div class="detail-card__body">
            <div class="metric-grid cols-4">
              <div class="metric-card">
                <span>执行开关</span>
                <strong>{{ selectedTask.enabled ? "已启用" : "已关闭" }}</strong>
              </div>
              <div class="metric-card">
                <span>最近状态</span>
                <strong>{{ selectedTask.last_run_status || "未知" }}</strong>
              </div>
              <div class="metric-card">
                <span>运行状态</span>
                <strong>{{ currentRunStateLabel }}</strong>
              </div>
              <div class="metric-card">
                <span>阻断语义</span>
                <strong>{{ selectedTaskBlockLabel }}</strong>
              </div>
            </div>

            <div class="lane">
              <div class="lane-head">
                <h4>运行历史</h4>
                <Chip size="sm">{{ selectedRuns.length }} 条</Chip>
              </div>
              <div v-if="runsLoading" class="lane-empty">正在读取该任务的运行历史。</div>
              <div v-else-if="selectedRuns.length === 0" class="lane-empty">该任务暂时还没有运行记录。</div>
              <div v-else class="run-list">
                <div v-for="run in selectedRuns" :key="run.id" class="run-item" :class="{ 'is-blocked': run.status === 'blocked' }">
                  <div class="run-head">
                    <strong>{{ run.status }}</strong>
                    <span>{{ formatDateTime(run.started_at ?? run.created_at) }}</span>
                  </div>
                  <div class="run-meta">
                    <span>开始: {{ run.started_at ? formatDateTime(run.started_at) : "未开始" }}</span>
                    <span>结束: {{ run.finished_at ? formatDateTime(run.finished_at) : "未结束" }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="lane">
              <div class="lane-head">
                <h4>日志流</h4>
                <Chip size="sm">{{ selectedLogs.length }} 行</Chip>
              </div>
              <div class="terminal">
                <div v-if="selectedLogs.length === 0" class="term-line muted">> 暂无日志。触发任务后，运行内容会在这里展开。</div>
                <template v-else>
                  <div v-for="line in selectedLogs" :key="line.id" class="term-line" :class="{ 'blocked': line.status === 'blocked' }">
                    > {{ line.text }}
                  </div>
                </template>
              </div>
            </div>

            <div class="lane">
              <div class="lane-head">
                <h4>执行配置</h4>
                <Chip size="sm" :variant="selectedTask.enabled ? 'success' : 'neutral'">{{ selectedTask.enabled ? "可执行" : "已关闭" }}</Chip>
              </div>
              <div class="config-grid">
                <div class="cfg-row"><span>任务类型</span><strong>{{ selectedTask.type }}</strong></div>
                <div class="cfg-row"><span>Cron</span><strong>{{ selectedTask.cron_expr || "未配置" }}</strong></div>
                <div class="cfg-row"><span>配置体</span><pre>{{ selectedTaskConfigPreview }}</pre></div>
              </div>
            </div>
          </div>
        </Card>
        
        <Card class="detail-card empty-wrapper" v-else>
          <div class="empty-state">
            <span class="material-symbols-outlined">monitoring</span>
            <strong>选择一个任务查看执行链路</strong>
            <p>这里会显示运行历史、日志流和阻断语义。</p>
          </div>
        </Card>
      </main>
    </div>

    <!-- Drawer Modal -->
    <transition name="drawer">
      <div v-if="showAddTask" class="drawer-overlay" @click="showAddTask = false">
        <aside class="drawer-panel" @click.stop>
          <div class="drawer-panel__header">
            <div>
              <p class="drawer-panel__eyebrow">新建任务</p>
              <h2>创建自动化任务</h2>
            </div>
            <button class="drawer-panel__close" @click="showAddTask = false">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <div class="drawer-panel__body">
            <form class="drawer-form" @submit.prevent="handleCreateTask">
              <div class="form-group">
                <label>任务名称</label>
                <input v-model="addForm.name" type="text" placeholder="例如：每日同步账号状态" class="ui-input-field" required />
              </div>
              <div class="form-group">
                <label>任务类型</label>
                <select v-model="addForm.type" class="ui-input-field">
                  <option value="collect">采集</option>
                  <option value="reply">回复</option>
                  <option value="sync">同步</option>
                  <option value="validate">校验</option>
                </select>
              </div>
              <div class="form-group">
                <label>Cron 表达式</label>
                <input v-model="addForm.cronExpr" type="text" placeholder="0 */2 * * *" class="ui-input-field" />
              </div>
              <div class="form-group">
                <label>执行参数 JSON</label>
                <textarea v-model="addForm.configJson" rows="6" placeholder='{"workspaceId":"ws-1","enabled":true}' class="ui-input-field textarea"></textarea>
              </div>
              <div class="drawer-actions">
                <Button variant="ghost" @click="showAddTask = false">取消</Button>
                <Button variant="primary" type="submit" :disabled="isBusy">保存任务</Button>
              </div>
            </form>
          </div>
        </aside>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useAutomationStore } from "@/stores/automation";
import type { AutomationTaskCreateInput, AutomationTaskDto } from "@/types/runtime";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import Input from "@/components/ui/Input/Input.vue";

type TaskView = AutomationTaskDto;
type TaskFilterValue = "all" | "enabled" | "disabled";

const automationStore = useAutomationStore();
const selectedTaskId = ref<string | null>(null);
const statusFilter = ref<TaskFilterValue>("all");
const typeFilter = ref<string>("");
const showAddTask = ref(false);
const addForm = ref({ name: "", type: "collect", cronExpr: "", configJson: "" });

const tasks = computed(() => automationStore.tasks as TaskView[]);
const enabledTaskCount = computed(() => tasks.value.filter((task) => task.enabled).length);
const blockedTaskCount = computed(() => tasks.value.filter((task) => task.last_run_status === "blocked" || !task.enabled).length);
const isLoading = computed(() => automationStore.loading || automationStore.viewState === "loading");
const isEmpty = computed(() => automationStore.viewState === "empty" && !isLoading.value);
const isBusy = computed(() => isLoading.value || automationStore.triggerState === "running");

const triggerStateLabel = computed(() => {
  if (automationStore.triggerState === "running") return "触发中";
  if (automationStore.triggerState === "error") return "触发失败";
  if (automationStore.triggerState === "ready") return "已触发";
  return "空闲";
});

const statusFilters: Array<{ label: string; value: TaskFilterValue }> = [
  { label: "全部", value: "all" }, { label: "已启用", value: "enabled" }, { label: "已关闭", value: "disabled" }
];
const typeFilters = [
  { label: "采集", value: "collect" }, { label: "回复", value: "reply" }, { label: "同步", value: "sync" }, { label: "校验", value: "validate" }
];

const filteredTasks = computed(() => {
  let list = tasks.value;
  if (statusFilter.value === "enabled") list = list.filter((task) => task.enabled);
  else if (statusFilter.value === "disabled") list = list.filter((task) => !task.enabled);
  if (typeFilter.value) list = list.filter((task) => task.type === typeFilter.value);
  return list;
});

const selectedTask = computed(() => tasks.value.find((task) => task.id === selectedTaskId.value) ?? null);
const selectedRuns = computed(() => selectedTaskId.value ? automationStore.runsByTaskId[selectedTaskId.value] ?? [] : []);
const runsLoading = computed(() => (selectedTaskId.value ? automationStore.runsStatusByTaskId[selectedTaskId.value] : "idle") === "loading");

const currentRunStateLabel = computed(() => {
  if (automationStore.triggerState === "running") return "正在触发";
  if (runsLoading.value) return "读取历史";
  return automationStore.triggerState === "error" ? "触发异常" : "待命";
});

const selectedTaskBlockLabel = computed(() => {
  if (!selectedTask.value) return "未选中";
  if (!selectedTask.value.enabled) return "任务已关闭";
  if (selectedTask.value.last_run_status === "blocked") return "最近运行被阻断";
  return "可手动运行";
});

const selectedLogs = computed(() =>
  selectedRuns.value.flatMap((run) =>
    (run.log_text ?? "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean).map((line) => ({
      id: `${run.id}-${line}`, status: run.status, text: line
    }))
  )
);

const selectedTaskConfigPreview = computed(() => prettyJson(selectedTask.value?.config_json));

onMounted(() => { void automationStore.loadTasks(); });

watch(() => tasks.value.map((task) => task.id).join("|"), () => {
  if (!selectedTaskId.value && tasks.value.length > 0) selectedTaskId.value = tasks.value[0].id;
}, { immediate: true });

watch(selectedTaskId, (taskId) => { if (taskId) void automationStore.loadRuns(taskId); }, { immediate: true });

function isTaskBlocked(task: TaskView) { return !task.enabled || task.last_run_status === "blocked"; }
function taskStatusTone(task: TaskView) {
  if (!task.enabled) return "neutral";
  if (task.last_run_status === "blocked") return "warning";
  if (task.last_run_status === "failed") return "danger";
  if (task.last_run_status === "running" || automationStore.triggerState === "running") return "brand";
  return "success";
}

function taskStatusLabel(task: TaskView) {
  if (!task.enabled) return "已关闭";
  if (!task.last_run_status) return "待运行";
  return task.last_run_status;
}

async function handleRunTask(id: string) {
  selectedTaskId.value = id;
  await automationStore.triggerTask(id);
}

async function handleCreateTask() {
  if (!addForm.value.name.trim()) return;
  const task = await automationStore.addTask({
    name: addForm.value.name.trim(), type: addForm.value.type, cron_expr: addForm.value.cronExpr.trim() || null, config_json: addForm.value.configJson.trim() || null
  });
  if (!task) return;
  selectedTaskId.value = task.id;
  addForm.value = { name: "", type: "collect", cronExpr: "", configJson: "" };
  showAddTask.value = false;
}

function prettyJson(value: string | null) {
  if (!value) return "未配置";
  try { return JSON.stringify(JSON.parse(value), null, 2); } catch { return value; }
}

function formatDate(value: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("zh-CN");
}

function formatDateTime(value: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : `${date.toLocaleDateString("zh-CN")} ${date.toLocaleTimeString("zh-CN", { hour12: false, hour: "2-digit", minute: "2-digit" })}`;
}
</script>

<style scoped>
.page-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-8) var(--space-8);
  display: flex;
  flex-direction: column;
}

.page-header {
  display: grid;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.page-header__crumb {
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.page-header__row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.page-header__title {
  font: var(--font-display-md);
  letter-spacing: var(--ls-display-md);
  color: var(--color-text-primary);
  margin: 0 0 4px 0;
}

.page-header__subtitle {
  font: var(--font-body-md);
  letter-spacing: var(--ls-body-md);
  color: var(--color-text-secondary);
}

.dashboard-alert {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-muted);
  line-height: 1.6;
  margin-bottom: var(--space-4);
  font: var(--font-body-sm);
  display: flex;
  align-items: center;
  gap: 8px;
}

.dashboard-alert[data-tone="danger"] { border-color: rgba(255, 90, 99, 0.20); background: rgba(255, 90, 99, 0.08); color: var(--color-danger); }
.dashboard-alert[data-tone="success"] { border-color: rgba(34, 211, 154, 0.20); background: rgba(34, 211, 154, 0.08); color: var(--color-success); }
.dashboard-alert[data-tone="brand"] { border-color: rgba(0, 188, 212, 0.20); background: rgba(0, 188, 212, 0.08); color: var(--color-brand-primary); }

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.summary-card {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sc-label {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.sc-val {
  font: var(--font-title-md);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(320px, 360px) minmax(0, 1fr);
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
}

.workspace-rail {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-height: 0;
}

.rail-card {
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.h-full { height: 100%; }

.rail-card__header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
}

.rail-card__header h3 {
  margin: 0;
  font: var(--font-title-md);
  color: var(--color-text-primary);
}

.flex-col { display: flex; flex-direction: column; }
.align-start { align-items: flex-start; }
.gap-3 { gap: var(--space-3); }

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.rail-card__body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  background: var(--color-bg-canvas);
}

.rail-card__body.no-padding { padding: 0; }
.scroll-area { overflow-y: auto; }

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-10) var(--space-4);
  color: var(--color-text-tertiary);
  gap: 8px;
}

.empty-state .material-symbols-outlined {
  font-size: 32px;
  color: var(--color-text-secondary);
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.task-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: var(--space-4);
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--color-border-subtle);
  cursor: pointer;
  text-align: left;
  transition: all var(--motion-fast) var(--ease-standard);
}

.task-card:hover { background: var(--color-bg-hover); }
.task-card:active { transform: scale(0.98); transition-duration: var(--motion-instant); }

.task-list-transition-move,
.task-list-transition-enter-active,
.task-list-transition-leave-active {
  transition: all var(--motion-default) var(--ease-spring);
}
.task-list-transition-enter-from,
.task-list-transition-leave-to {
  opacity: 0;
  transform: translateX(-16px);
}
.task-list-transition-leave-active {
  position: absolute;
  width: 100%;
}

.task-card.is-selected {
  background: color-mix(in srgb, var(--color-brand-primary) 8%, var(--color-bg-surface));
  border-left: 3px solid var(--color-brand-primary);
  padding-left: calc(var(--space-4) - 3px);
}

.task-card.is-disabled { opacity: 0.8; }

.tc-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.tc-title {
  display: flex;
  flex-direction: column;
}

.tc-title strong { font: var(--font-title-sm); color: var(--color-text-primary); }
.tc-title span { font: var(--font-caption); color: var(--color-text-secondary); }

.tc-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.tc-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.tc-flag { font: var(--font-caption); }
.text-success { color: var(--color-success); }
.text-muted { color: var(--color-text-tertiary); }

.workspace-main {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.detail-card {
  padding: 0;
  display: flex;
  flex-direction: column;
}

.detail-card__header {
  padding: var(--space-5);
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.eyebrow {
  margin: 0 0 4px 0;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.detail-card__header h3 {
  margin: 0 0 4px 0;
  font: var(--font-title-lg);
  color: var(--color-text-primary);
}

.summary {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail-card__body {
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.metric-grid {
  display: grid;
  gap: 10px;
}

.cols-4 { grid-template-columns: repeat(4, 1fr); }

.metric-card {
  padding: var(--space-4);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-card span { font: var(--font-caption); color: var(--color-text-tertiary); }
.metric-card strong { font: var(--font-title-md); color: var(--color-text-primary); }

.lane {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.lane-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.lane-head h4 {
  margin: 0;
  font: var(--font-title-sm);
  color: var(--color-text-primary);
}

.lane-empty {
  padding: var(--space-4);
  text-align: center;
  color: var(--color-text-tertiary);
  font: var(--font-body-sm);
  background: var(--color-bg-muted);
  border-radius: var(--radius-sm);
}

.run-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.run-item {
  padding: var(--space-3);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  background: var(--color-bg-canvas);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.run-item.is-blocked { border-color: rgba(245, 183, 64, 0.4); }

.run-head {
  display: flex;
  justify-content: space-between;
  font: var(--font-body-sm);
  color: var(--color-text-primary);
}

.run-meta {
  display: flex;
  gap: 12px;
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.terminal {
  min-height: 180px;
  padding: var(--space-4);
  border-radius: var(--radius-sm);
  background: #0c1016;
  border: 1px solid rgba(255, 255, 255, 0.06);
  font-family: var(--font-family-mono);
  font-size: 12px;
  line-height: 1.8;
  max-height: 320px;
  overflow-y: auto;
}

.term-line { color: var(--color-brand-primary); white-space: pre-wrap; }
.term-line.muted { color: var(--color-text-tertiary); }
.term-line.blocked { color: var(--color-warning); }

.config-grid { display: flex; flex-direction: column; gap: 8px; }
.cfg-row { display: flex; flex-direction: column; gap: 4px; }
.cfg-row span { font: var(--font-caption); color: var(--color-text-tertiary); }
.cfg-row strong { font: var(--font-body-md); color: var(--color-text-primary); }
.cfg-row pre {
  margin: 0;
  padding: var(--space-3);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
  font: var(--font-mono-md);
  white-space: pre-wrap;
  word-break: break-all;
}

.empty-wrapper { flex: 1; justify-content: center; }

.drawer-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-bg-overlay);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: 420px;
  background: var(--color-bg-surface);
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.drawer-panel__header {
  padding: var(--space-5);
  border-bottom: 1px solid var(--color-border-subtle);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.drawer-panel__eyebrow {
  margin: 0 0 4px 0;
  font: var(--font-caption);
  color: var(--color-brand-primary);
  text-transform: uppercase;
}

.drawer-panel__header h2 { margin: 0; font: var(--font-title-lg); color: var(--color-text-primary); }

.drawer-panel__close {
  background: transparent;
  border: none;
  color: var(--color-text-tertiary);
  cursor: pointer;
  padding: 4px;
}

.drawer-panel__body {
  padding: var(--space-6);
  flex: 1;
  overflow-y: auto;
}

.drawer-form { display: flex; flex-direction: column; gap: var(--space-4); }
.form-group { display: flex; flex-direction: column; gap: 8px; }
.form-group label { font: var(--font-caption); color: var(--color-text-secondary); }

.ui-input-field {
  height: 38px;
  padding: 0 12px;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
  font: var(--font-body-md);
  outline: none;
}
.ui-input-field.textarea { height: auto; padding: 12px; resize: vertical; }

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.drawer-enter-active, .drawer-leave-active { transition: opacity 160ms ease; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }

@media (max-width: 1200px) {
  .workspace-grid { grid-template-columns: 1fr; }
  .metric-grid.cols-4 { grid-template-columns: repeat(2, 1fr); }
}
</style>
