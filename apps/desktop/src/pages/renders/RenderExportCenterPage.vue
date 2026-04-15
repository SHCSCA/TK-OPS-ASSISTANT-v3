<template>
  <ProjectContextGuard>
    <div class="render-center">
    <!-- 工具栏 -->
    <header class="render-toolbar">
      <div class="toolbar-left">
        <button class="btn-primary" @click="handleNewTask">
          <span class="material-symbols-outlined">add_task</span>
          新建渲染任务
        </button>
        <div class="filter-tabs">
          <button v-for="tab in statusTabs" :key="tab.value"
            :class="{ active: currentFilter === tab.value }"
            @click="currentFilter = tab.value">
            {{ tab.label }}
          </button>
        </div>
      </div>
    </header>

    <main class="render-content">
      <!-- 任务列表 -->
      <section class="task-list-section">
        <div v-if="filteredTasks.length === 0" class="empty-state">
          <span class="material-symbols-outlined">movie_edit</span>
          <h3>暂无渲染任务</h3>
          <p>从工作台完成视频编辑后，点击“导出”即可在此查看进度</p>
        </div>
        <div v-else class="task-list">
          <div v-for="task in filteredTasks" :key="task.id"
            class="task-row"
            :class="{ active: selectedTaskId === task.id }"
            @click="selectedTaskId = task.id">
            <div class="task-status">
              <span class="material-symbols-outlined" :class="task.status">
                {{ getStatusIcon(task.status) }}
              </span>
            </div>
            <div class="task-info">
              <div class="task-title">{{ task.projectName }} / {{ task.fileName }}</div>
              <div v-if="task.status === 'running'" class="progress-container">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: task.progress + '%' }"></div>
                </div>
                <span class="progress-text">{{ task.progress }}%</span>
              </div>
              <div class="task-meta">
                <span>{{ task.format }}</span>
                <span class="dot">·</span>
                <span>{{ task.duration }}</span>
                <span class="dot">·</span>
                <span>{{ task.createdAt }}</span>
              </div>
            </div>
            <div class="task-actions">
              <button v-if="task.status === 'completed'" class="btn-download" @click.stop="handleDownload" title="下载视频">
                <span class="material-symbols-outlined">download</span>
              </button>
              <button class="btn-delete" @click.stop="handleDelete(task.id)">
                <span class="material-symbols-outlined">close</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 任务详情 -->
      <transition name="fade">
        <aside v-if="selectedTask" class="task-detail-panel">
          <div class="panel-header">任务详情</div>
          <div class="panel-body">
            <div class="detail-section">
              <label>渲染状态</label>
              <span class="status-badge" :class="selectedTask.status">{{ getStatusLabel(selectedTask.status) }}</span>
            </div>
            <div class="detail-section">
              <label>导出参数</label>
              <div class="params-list">
                <div class="param-item"><span>分辨率</span><span>1080x1920</span></div>
                <div class="param-item"><span>帧率</span><span>30 fps</span></div>
                <div class="param-item"><span>编码</span><span>H.264 / AAC</span></div>
                <div class="param-item"><span>比特率</span><span>8 Mbps</span></div>
              </div>
            </div>
            <div class="detail-section">
              <label>实时日志</label>
              <div class="log-viewer">
                <div v-for="(log, i) in selectedTask.logs" :key="i" class="log-line">
                  <span class="log-time">[{{ log.time }}]</span>
                  <span class="log-msg">{{ log.msg }}</span>
                </div>
                <div v-if="selectedTask.status === 'running'" class="log-line running">
                  <span class="rotating-icon material-symbols-outlined">sync</span>
                  <span>正在合成视频帧...</span>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </transition>
    </main>
  </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";

interface RenderTask {
  id: string;
  projectName: string;
  fileName: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  format: string;
  duration: string;
  createdAt: string;
  logs: Array<{ time: string, msg: string }>;
}

const statusTabs = [
  { label: '全部', value: 'all' },
  { label: '进行中', value: 'running' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' }
];

const currentFilter = ref('all');
const selectedTaskId = ref<string | null>(null);

// Memory state for demo/V1
const tasks = ref<RenderTask[]>([
  {
    id: '1',
    projectName: '夏季爆款带货',
    fileName: 'video_v1_0620.mp4',
    status: 'completed',
    progress: 100,
    format: 'MP4 (H.264)',
    duration: '00:15',
    createdAt: '2024-06-20 14:20',
    logs: [
      { time: '14:20:01', msg: 'Task initialized' },
      { time: '14:20:05', msg: 'Media sources loaded' },
      { time: '14:21:30', msg: 'Render successful' }
    ]
  },
  {
    id: '2',
    projectName: '剧情脚本测试',
    fileName: 'draft_preview.mp4',
    status: 'running',
    progress: 45,
    format: 'MP4 (H.264)',
    duration: '01:20',
    createdAt: '2024-06-20 15:45',
    logs: [
      { time: '15:45:10', msg: 'Starting render engine' },
      { time: '15:45:30', msg: 'Encoding audio streams' }
    ]
  }
]);

const filteredTasks = computed(() => {
  if (currentFilter.value === 'all') return tasks.value;
  return tasks.value.filter(t => t.status === currentFilter.value);
});

const selectedTask = computed(() => 
  tasks.value.find(t => t.id === selectedTaskId.value)
);

function handleNewTask() {
  alert('渲染引擎 B-M14 后端尚未就绪，功能接入中');
}

function handleDownload() {
  alert('视频文件准备中，请稍后');
}

function handleDelete(id: string) {
  tasks.value = tasks.value.filter(t => t.id !== id);
  if (selectedTaskId.value === id) selectedTaskId.value = null;
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'pending': return 'schedule';
    case 'running': return 'sync';
    case 'completed': return 'check_circle';
    case 'failed': return 'cancel';
    default: return 'help';
  }
}

function getStatusLabel(status: string) {
  switch (status) {
    case 'pending': return '等待中';
    case 'running': return '渲染中';
    case 'completed': return '已完成';
    case 'failed': return '渲染失败';
    default: return status;
  }
}
</script>

<style scoped>
.render-center {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  overflow: hidden;
}

/* ── 工具栏 ── */
.render-toolbar {
  height: 44px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-md);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--brand-primary);
  color: #000;
  border: none;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.filter-tabs {
  display: flex;
  gap: var(--spacing-sm);
}

.filter-tabs button {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  border-radius: var(--radius-sm);
}

.filter-tabs button.active {
  color: var(--brand-primary);
  background: rgba(0, 242, 234, 0.1);
}

/* ── 主内容 ── */
.render-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.task-list-section {
  flex: 1;
  overflow-y: auto;
  border-right: 1px solid var(--border-default);
}

.task-list {
  display: flex;
  flex-direction: column;
}

.task-row {
  display: flex;
  align-items: center;
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background 0.2s;
  gap: var(--spacing-md);
}

.task-row:hover {
  background: var(--bg-hover);
}

.task-row.active {
  background: rgba(0, 242, 234, 0.04);
}

.task-status .material-symbols-outlined {
  font-size: 20px;
}

.task-status .running {
  color: var(--brand-primary);
  animation: rotate 2s linear infinite;
}

.task-status .completed { color: #00ff88; }
.task-status .failed { color: var(--brand-secondary); }
.task-status .pending { color: var(--text-muted); }

.task-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.task-title {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--brand-primary);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 11px;
  color: var(--brand-primary);
  width: 30px;
}

.task-meta {
  font-size: 11px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 6px;
}

.task-actions {
  display: flex;
  gap: 8px;
}

.task-actions button {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.task-actions button:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.btn-download:hover {
  color: var(--brand-primary) !important;
}

/* ── 详情面板 ── */
.task-detail-panel {
  width: 350px;
  background: var(--bg-elevated);
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 12px var(--spacing-md);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.panel-body {
  flex: 1;
  padding: var(--spacing-md);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-section label {
  font-size: 11px;
  color: var(--text-muted);
}

.params-list {
  background: var(--bg-card);
  border-radius: var(--radius-sm);
  padding: 8px;
}

.param-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 4px 0;
}

.param-item span:first-child {
  color: var(--text-secondary);
}

.log-viewer {
  background: #000;
  border-radius: var(--radius-sm);
  padding: 12px;
  font-family: 'Cascadia Code', monospace;
  font-size: 11px;
  min-height: 150px;
}

.log-line {
  margin-bottom: 4px;
  line-height: 1.4;
}

.log-time {
  color: #666;
  margin-right: 8px;
}

.log-msg {
  color: #ccc;
}

.log-line.running {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--brand-primary);
}

.rotating-icon {
  font-size: 14px;
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 100px;
  color: var(--text-muted);
  text-align: center;
}

.empty-state .material-symbols-outlined {
  font-size: 64px;
  margin-bottom: var(--spacing-md);
}

.empty-state h3 {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.empty-state p {
  font-size: 13px;
  max-width: 300px;
}

.status-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
  width: fit-content;
}

.status-badge.completed { background: rgba(0, 255, 136, 0.1); color: #00ff88; }
.status-badge.running { background: rgba(0, 242, 234, 0.1); color: var(--brand-primary); }
.status-badge.failed { background: rgba(255, 0, 80, 0.1); color: var(--brand-secondary); }

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
