<template>
  <div class="automation-page">
    <!-- 工具栏 -->
    <header class="toolbar">
      <div class="toolbar-left">
        <button class="btn-primary" @click="showAddTask = true">
          <span class="material-symbols-outlined">add</span>新建任务
        </button>
        <div class="filter-group">
          <button
            v-for="s in statusFilters"
            :key="s.value"
            class="filter-chip"
            :class="{ active: statusFilter === s.value }"
            @click="statusFilter = s.value"
          >{{ s.label }}</button>
        </div>
        <div class="filter-group">
          <button
            v-for="t in typeFilters"
            :key="t.value"
            class="type-chip"
            :class="[`type-${t.value}`, { active: typeFilter === t.value }]"
            @click="typeFilter = typeFilter === t.value ? '' : t.value"
          >{{ t.label }}</button>
        </div>
      </div>
    </header>

    <main class="console-layout">
      <!-- 左：任务列表 -->
      <aside class="task-sidebar">
        <div v-if="filteredTasks.length === 0" class="empty-guide">
          <span class="material-symbols-outlined guide-icon">robot_2</span>
          <h3>还没有自动化任务</h3>
          <p>点击"新建任务"配置您的第一个自动化流程</p>
          <button class="btn-primary" @click="showAddTask = true">
            <span class="material-symbols-outlined">add</span>立即创建
          </button>
        </div>
        <div v-else class="task-list">
          <div
            v-for="task in filteredTasks"
            :key="task.id"
            class="task-item"
            :class="{ active: selectedTaskId === task.id }"
            @click="selectedTaskId = task.id"
          >
            <div class="task-meta">
              <div class="task-name">{{ task.name }}</div>
              <span class="type-chip-sm" :class="`type-${task.type}`">{{ task.type }}</span>
            </div>
            <div class="task-row2">
              <span class="task-last-run">上次运行：{{ task.lastRun ?? '从未' }}</span>
              <div class="task-toggle" :class="{ enabled: task.enabled }" @click.stop="task.enabled = !task.enabled">
                <div class="toggle-knob"></div>
              </div>
            </div>
            <div class="task-actions">
              <button class="btn-action" @click.stop="handleRunTask(task.id)" title="手动触发">
                <span class="material-symbols-outlined">play_arrow</span>
              </button>
            </div>
          </div>
        </div>
      </aside>

      <!-- 右：监控 -->
      <section class="monitor-area">
        <div v-if="!selectedTask" class="monitor-placeholder">
          <span class="material-symbols-outlined" style="font-size:56px;opacity:0.2">monitoring</span>
          <p>选择任务查看运行历史与日志</p>
        </div>
        <div v-else class="monitor-content">
          <div class="monitor-header">
            <h3>{{ selectedTask.name }}</h3>
            <span class="type-chip-sm" :class="`type-${selectedTask.type}`">{{ selectedTask.type }}</span>
          </div>
          <div class="history-section">
            <h4>运行记录</h4>
            <div class="empty-sub">暂无执行记录</div>
          </div>
          <div class="logs-section">
            <div class="logs-header">
              <h4>实时日志</h4>
              <span class="log-badge">IDLE</span>
            </div>
            <div class="log-terminal">
              <div class="log-line">&gt; 监控系统就绪，等待任务触发…</div>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- 新建任务抽屉 -->
    <div v-if="showAddTask" class="drawer-overlay" @click.self="showAddTask = false">
      <div class="drawer">
        <div class="drawer-header">
          <h2>新建自动化任务</h2>
          <button class="btn-icon" @click="showAddTask = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="drawer-body">
          <div class="form-group">
            <label>任务名称</label>
            <input v-model="addForm.name" placeholder="例：每日采集-主账号" />
          </div>
          <div class="form-group">
            <label>任务类型</label>
            <select v-model="addForm.type">
              <option value="collect">采集 (collect)</option>
              <option value="reply">回复 (reply)</option>
              <option value="sync">同步 (sync)</option>
              <option value="validate">验证 (validate)</option>
            </select>
          </div>
          <div class="drawer-footer">
            <button class="btn-secondary" @click="showAddTask = false">取消</button>
            <button class="btn-primary" @click="handleCreateTask">保存任务</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

interface AutoTask {
  id: string;
  name: string;
  type: 'collect' | 'reply' | 'sync' | 'validate';
  enabled: boolean;
  lastRun: string | null;
}

const tasks = ref<AutoTask[]>([]);
const selectedTaskId = ref<string | null>(null);
const statusFilter = ref<string>('all');
const typeFilter = ref<string>('');
const showAddTask = ref(false);
const addForm = ref({ name: '', type: 'collect' });

const statusFilters = [
  { value: 'all', label: '全部' },
  { value: 'enabled', label: '启用中' },
  { value: 'disabled', label: '已禁用' }
];

const typeFilters = [
  { value: 'collect', label: '采集' },
  { value: 'reply', label: '回复' },
  { value: 'sync', label: '同步' },
  { value: 'validate', label: '验证' }
];

const filteredTasks = computed(() => {
  let list = tasks.value;
  if (statusFilter.value === 'enabled') list = list.filter((t) => t.enabled);
  if (statusFilter.value === 'disabled') list = list.filter((t) => !t.enabled);
  if (typeFilter.value) list = list.filter((t) => t.type === typeFilter.value);
  return list;
});

const selectedTask = computed(() =>
  tasks.value.find((t) => t.id === selectedTaskId.value) ?? null
);

function handleRunTask(id: string): void {
  alert('后端接入后可手动触发任务（B-M12 待实现）');
}

function handleCreateTask(): void {
  if (!addForm.value.name) return;
  alert('后端接入后可保存任务（B-M12 待实现）');
  showAddTask.value = false;
}
</script>

<style scoped>
.automation-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  overflow: hidden;
  position: relative;
}

.toolbar {
  height: 44px;
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-md);
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.toolbar-left { display: flex; align-items: center; gap: var(--spacing-md); }

.filter-group { display: flex; gap: 4px; }

.filter-chip {
  padding: 3px 10px;
  border-radius: 20px;
  border: 1px solid var(--border-default);
  font-size: 11px;
  color: var(--text-secondary);
  background: transparent;
  cursor: pointer;
}
.filter-chip.active { background: var(--brand-primary); color: #000; border-color: var(--brand-primary); font-weight: 600; }

.type-chip {
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}
.type-chip.active { opacity: 1; }

.type-collect, .type-chip.type-collect { background: rgba(59,130,246,0.15); color: #60a5fa; border-color: rgba(59,130,246,0.3); }
.type-reply, .type-chip.type-reply { background: rgba(168,85,247,0.15); color: #c084fc; border-color: rgba(168,85,247,0.3); }
.type-sync, .type-chip.type-sync { background: rgba(34,197,94,0.15); color: #4ade80; border-color: rgba(34,197,94,0.3); }
.type-validate, .type-chip.type-validate { background: rgba(251,146,60,0.15); color: #fb923c; border-color: rgba(251,146,60,0.3); }

.type-chip-sm {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
}

.console-layout {
  display: grid;
  grid-template-columns: 360px 1fr;
  flex: 1;
  overflow: hidden;
}

.task-sidebar {
  border-right: 1px solid var(--border-default);
  overflow-y: auto;
  background: var(--bg-card);
}

.empty-guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px;
  text-align: center;
  color: var(--text-muted);
  gap: var(--spacing-sm);
}

.guide-icon { font-size: 56px; color: var(--brand-primary); opacity: 0.4; }
.empty-guide h3 { font-size: 15px; color: var(--text-secondary); margin: 0; }
.empty-guide p { font-size: 12px; margin: 0; }

.task-list { padding: var(--spacing-sm); }

.task-item {
  padding: 12px;
  border-radius: var(--radius-md);
  margin-bottom: 6px;
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background 0.15s;
}
.task-item:hover { background: var(--bg-hover); }
.task-item.active { border-color: var(--brand-primary); background: rgba(0,242,234,0.04); }

.task-meta { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.task-name { font-size: 13px; font-weight: 600; }

.task-row2 { display: flex; align-items: center; justify-content: space-between; }
.task-last-run { font-size: 11px; color: var(--text-muted); }

.task-toggle {
  width: 32px;
  height: 18px;
  border-radius: 9px;
  background: var(--text-muted);
  position: relative;
  cursor: pointer;
  transition: background 0.2s;
}
.task-toggle.enabled { background: var(--brand-primary); }
.toggle-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  transition: left 0.2s;
}
.task-toggle.enabled .toggle-knob { left: 16px; }

.task-actions { display: flex; justify-content: flex-end; margin-top: 6px; }
.btn-action {
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  width: 28px; height: 28px;
  border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
}
.btn-action:hover { color: var(--brand-primary); border-color: var(--brand-primary); }

.monitor-area {
  display: flex;
  flex-direction: column;
  background: var(--bg-base);
  overflow: hidden;
}

.monitor-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  gap: 8px;
  font-size: 13px;
}

.monitor-content { display: flex; flex-direction: column; padding: var(--spacing-lg); gap: var(--spacing-md); height: 100%; overflow-y: auto; }
.monitor-header { display: flex; align-items: center; gap: 8px; }
.monitor-header h3 { font-size: 16px; font-weight: 600; margin: 0; }

.history-section, .logs-section {
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
}

.history-section h4, .logs-section h4 { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin: 0 0 var(--spacing-md) 0; }

.logs-section { flex: 1; display: flex; flex-direction: column; min-height: 200px; }
.logs-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-sm); }
.log-badge { background: rgba(255,255,255,0.08); color: var(--text-muted); font-size: 10px; padding: 2px 8px; border-radius: 4px; font-family: monospace; }

.log-terminal {
  flex: 1;
  background: #040404;
  border-radius: 6px;
  padding: 12px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  overflow-y: auto;
  border: 1px solid rgba(255,255,255,0.05);
}

.log-line { color: var(--brand-primary); opacity: 0.75; line-height: 1.8; }
.empty-sub { font-size: 12px; color: var(--text-muted); text-align: center; padding: 16px 0; }

/* 抽屉 */
.drawer-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: flex-end;
  z-index: 100;
}
.drawer { width: 380px; background: var(--bg-elevated); border-left: 1px solid var(--border-default); display: flex; flex-direction: column; height: 100%; }
.drawer-header { display: flex; align-items: center; justify-content: space-between; padding: var(--spacing-md) var(--spacing-lg); border-bottom: 1px solid var(--border-default); }
.drawer-header h2 { font-size: 16px; font-weight: 600; margin: 0; }
.drawer-body { flex: 1; overflow-y: auto; padding: var(--spacing-lg); }
.drawer-footer { display: flex; gap: var(--spacing-sm); justify-content: flex-end; margin-top: var(--spacing-xl); }

.form-group { margin-bottom: var(--spacing-md); }
.form-group label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
.form-group input, .form-group select {
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  padding: 9px var(--spacing-sm);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}
.form-group input:focus, .form-group select:focus { border-color: var(--brand-primary); }

/* 按钮 */
.btn-primary {
  display: flex; align-items: center; gap: 5px;
  background: var(--brand-primary); color: #000; border: none;
  padding: 7px 14px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 700; cursor: pointer;
}
.btn-secondary {
  display: flex; align-items: center; gap: 5px;
  background: var(--bg-card); color: var(--text-primary);
  border: 1px solid var(--border-default);
  padding: 7px 14px; border-radius: var(--radius-sm); font-size: 12px; cursor: pointer;
}
.btn-icon {
  background: transparent; border: none; color: var(--text-secondary);
  cursor: pointer; padding: 4px; display: flex; align-items: center;
}
</style>
