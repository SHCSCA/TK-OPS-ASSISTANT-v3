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

    <div class="queue-view-container h-full">
      <Card class="rail-card h-full">
        <div class="rail-card__header flex-col align-start gap-3">
          <div style="display: flex; justify-content: space-between; width: 100%;">
            <h3>任务队列</h3>
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
          <div v-else class="task-grid">
            <button
              v-for="task in filteredTasks"
              :key="task.id"
              class="task-card"
              :class="{
                'is-selected': selectedTaskId === task.id,
                'is-disabled': !task.enabled,
                'is-blocked': isTaskBlocked(task)
              }"
              @click="selectTask(task.id)"
            >
              <div class="tc-head">
                <div class="tc-title">
                  <strong>{{ task.name }}</strong>
                  <span class="task-source-label">来源: {{ task.type }}</span>
                </div>
                <Chip size="sm" :variant="taskStatusTone(task)">{{ taskStatusLabel(task) }}</Chip>
              </div>
              <div class="tc-meta tc-meta-results">
                <span>运行次数: {{ task.run_count }}</span>
                <span>最近结果: <strong>{{ task.last_run_status === 'success' ? '成功' : (task.last_run_status === 'failed' ? '失败' : (task.last_run_status || '未知')) }}</strong></span>
              </div>
              <div class="tc-meta">
                <span>Cron: {{ task.cron_expr || "未配置" }}</span>
                <span>最近运行: {{ task.last_run_at ? formatDate(task.last_run_at) : "从未" }}</span>
              </div>
              <div class="tc-footer">
                <span class="tc-flag" :class="task.enabled ? 'text-success' : 'text-muted'">
                  {{ task.enabled ? "已启用" : "已关闭" }}
                </span>
                <Button variant="ghost" size="sm" :disabled="isBusy" @click.stop="handleRunTask(task.id)">
                  {{ ['failed', 'blocked', 'error'].includes(taskRealtimeStatus(task)) ? '重试' : '运行' }}
                </Button>
              </div>
            </button>
          </div>
        </div>
      </Card>
    </div>

    <!-- Details Drawer Modal -->
    <transition name="drawer">
      <div v-if="showDetailsDrawer && selectedTask" class="drawer-overlay" @click="closeDetailsDrawer">
        <aside class="drawer-panel drawer-panel--large" @click.stop>
          <div class="drawer-panel__header">
            <div>
              <p class="drawer-panel__eyebrow">当前任务</p>
              <h2>{{ selectedTask.name }}</h2>
              <p class="summary">来源 {{ selectedTask.type }}，Cron {{ selectedTask.cron_expr || "未配置" }}，运行次数 {{ selectedTask.run_count }}。</p>
            </div>
            <div class="actions">
              <Chip :variant="taskStatusTone(selectedTask)">{{ taskStatusLabel(selectedTask) }}</Chip>
              <Button variant="secondary" :disabled="isBusy" @click="selectedTask.enabled ? handleRunTask(selectedTask.id) : undefined">
                {{ selectedTask.enabled ? (['failed', 'blocked'].includes(taskRealtimeStatus(selectedTask)) ? '手动重试' : '手动触发') : "任务已关闭" }}
              </Button>
              <button class="drawer-panel__close" @click="closeDetailsDrawer" style="margin-left: 16px;">
                <span class="material-symbols-outlined">close</span>
              </button>
            </div>
          </div>

          <div class="drawer-panel__body">
            <div class="metric-grid cols-2">
              <div class="metric-card">
                <span>执行开关</span>
                <strong>{{ selectedTask.enabled ? "已启用" : "已关闭" }}</strong>
              </div>
              <div class="metric-card">
                <span>运行状态</span>
                <strong>{{ currentRunStateLabel }}</strong>
              </div>
              <div class="metric-card" style="grid-column: span 2;">
                <span>阻断语义</span>
                <strong>{{ selectedTaskBlockLabel }}</strong>
              </div>
            </div>

            <div class="lane" style="margin-top: 16px;">
              <div class="lane-head">
                <h4>日志摘要</h4>
                <Chip size="sm">{{ logSummary.length }} 条最新</Chip>
              </div>
              <div class="terminal">
                <div v-if="logSummary.length === 0" class="term-line muted">> 暂无日志摘要。</div>
                <template v-else>
                  <div v-for="line in logSummary" :key="line.id" class="term-line" :class="{ 'blocked': line.status === 'blocked', 'failed': line.status === 'failed' }">
                    > {{ line.text }}
                  </div>
                </template>
              </div>
            </div>

            <div class="lane" style="margin-top: 16px;">
              <div class="lane-head">
                <h4>运行历史</h4>
                <Chip size="sm">{{ selectedRuns.length }} 条</Chip>
              </div>
              <div v-if="runsLoading" class="lane-empty">正在读取该任务的运行历史。</div>
              <div v-else-if="selectedRuns.length === 0" class="lane-empty">该任务暂时还没有运行记录。</div>
              <div v-else class="run-list">
                <div v-for="run in selectedRuns" :key="run.id" class="run-item" :class="{ 'is-blocked': run.status === 'blocked', 'is-failed': run.status === 'failed' }">
                  <div class="run-head">
                    <strong>{{ run.status === 'success' ? '成功' : (run.status === 'failed' ? '失败' : run.status) }}</strong>
                    <span>{{ formatDateTime(run.started_at ?? run.created_at) }}</span>
                  </div>
                  <div class="run-meta">
                    <span>开始: {{ run.started_at ? formatDateTime(run.started_at) : "未开始" }}</span>
                    <span>结束: {{ run.finished_at ? formatDateTime(run.finished_at) : "未结束" }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="lane" style="margin-top: 16px;">
              <div class="lane-head">
                <h4>执行配置</h4>
              </div>
              <div class="config-grid">
                <div class="cfg-row"><span>任务类型</span><strong>{{ selectedTask.type }}</strong></div>
                <div class="cfg-row"><span>Cron</span><strong>{{ selectedTask.cron_expr || "未配置" }}</strong></div>
                <div class="cfg-row"><span>配置体</span><pre>{{ selectedTaskConfigPreview }}</pre></div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </transition>

    <!-- Drawer Modal For Add -->
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
import { computed, onMounted, ref, watch, onUnmounted } from "vue";
import { useAutomationStore } from "@/stores/automation";
import { useTaskBusStore } from "@/stores/task-bus";
import type { AutomationTaskCreateInput, AutomationTaskDto } from "@/types/runtime";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import Input from "@/components/ui/Input/Input.vue";

type TaskView = AutomationTaskDto;
type TaskFilterValue = "all" | "enabled" | "disabled";

const automationStore = useAutomationStore();
const taskBusStore = useTaskBusStore();

const selectedTaskId = ref<string | null>(null);
const showDetailsDrawer = ref(false);
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
  if (selectedTask.value) {
     const status = taskRealtimeStatus(selectedTask.value);
     if (status === 'running') return '运行中';
     if (status === 'queued') return '排队中';
  }
  return automationStore.triggerState === "error" ? "触发异常" : "待命";
});

const selectedTaskBlockLabel = computed(() => {
  if (!selectedTask.value) return "未选中";
  if (!selectedTask.value.enabled) return "任务已关闭";
  const st = taskRealtimeStatus(selectedTask.value);
  if (st === "blocked") return "最近运行被阻断";
  if (st === "failed") return "最近运行失败";
  return "可手动运行";
});

const selectedLogs = computed(() =>
  selectedRuns.value.flatMap((run) =>
    (run.log_text ?? "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean).map((line) => ({
      id: `${run.id}-${line}`, status: run.status, text: line
    }))
  )
);

// Only show latest 100 log lines as a summary to avoid clutter
const logSummary = computed(() => {
  const logs = selectedLogs.value;
  return logs.slice(-100);
});

const selectedTaskConfigPreview = computed(() => prettyJson(selectedTask.value?.config_json));

onMounted(() => { 
  taskBusStore.connect();
  void automationStore.loadTasks(); 
});

onUnmounted(() => {
  // Option: disconnect taskBusStore if needed, or leave connected
});

watch(selectedTaskId, (taskId) => { 
  if (taskId) {
    void automationStore.loadRuns(taskId); 
  }
}, { immediate: true });

function selectTask(taskId: string) {
  selectedTaskId.value = taskId;
  showDetailsDrawer.value = true;
}

function closeDetailsDrawer() {
  showDetailsDrawer.value = false;
  // Keep selectedTaskId so background loading still happens, or set to null
}

function taskRealtimeStatus(task: TaskView) {
  const liveTask = taskBusStore.tasks.get(task.id);
  if (liveTask && liveTask.status) {
    return liveTask.status;
  }
  return task.last_run_status || "queued";
}

function isTaskBlocked(task: TaskView) { 
  return !task.enabled || taskRealtimeStatus(task) === "blocked"; 
}

function taskStatusTone(task: TaskView) {
  if (!task.enabled) return "neutral";
  const st = taskRealtimeStatus(task);
  if (st === "blocked") return "warning";
  if (st === "failed" || st === "error") return "danger";
  if (st === "running" || automationStore.triggerState === "running") return "brand";
  if (st === "retried") return "brand";
  if (st === "queued") return "warning";
  if (st === "cancelled") return "neutral";
  if (st === "succeeded" || st === "success") return "success";
  return "success";
}

function taskStatusLabel(task: TaskView) {
  if (!task.enabled) return "已关闭";
  const st = taskRealtimeStatus(task);
  const map: Record<string, string> = {
    'queued': '排队中',
    'running': '运行中',
    'failed': '失败',
    'retried': '已重试',
    'cancelled': '已取消',
    'blocked': '已阻断',
    'succeeded': '已完成',
    'success': '已完成',
    'error': '错误'
  };
  return map[st] || st || "待命";
}

async function handleRunTask(id: string) {
  // Explicitly mapping retry to run logic inside trigger
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

<style scoped src="./AutomationConsolePage.css"></style>
