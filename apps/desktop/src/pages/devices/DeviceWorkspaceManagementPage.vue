<template>
  <div class="device-workspace-page">
    <!-- 页头 -->
    <header class="page-header">
      <div class="header-left">
        <span class="material-symbols-outlined header-icon">devices</span>
        <h1>设备与工作区管理</h1>
      </div>
      <div class="header-right">
        <button class="btn-primary" @click="isCreating = true">
          <span class="material-symbols-outlined">add</span>
          新建工作区
        </button>
      </div>
    </header>

    <main class="page-content">
      <!-- 左侧：工作区列表 -->
      <aside class="workspace-sidebar">
        <div class="sidebar-header">工作区列表（{{ workspaces.length }}）</div>
        <div class="sidebar-body">
          <div v-if="workspaces.length === 0" class="empty-list">
            <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-muted)">folder_off</span>
            <p>还没有工作区，点击右上角新建</p>
          </div>
          <div
            v-for="ws in workspaces"
            :key="ws.id"
            class="workspace-card"
            :class="{ active: selectedId === ws.id }"
            @click="selectedId = ws.id"
          >
            <div class="ws-status-dot" :class="ws.status"></div>
            <div class="ws-info">
              <div class="ws-name">{{ ws.name }}</div>
              <div class="ws-meta">{{ ws.root_path }}</div>
              <div class="ws-meta">最后使用：{{ ws.last_used_at ?? '从未' }}</div>
            </div>
            <span class="ws-err-badge" v-if="ws.error_count > 0">{{ ws.error_count }}</span>
          </div>
        </div>
      </aside>

      <!-- 右侧：详情/新建表单 -->
      <section class="workspace-detail">
        <!-- 新建表单 -->
        <div v-if="isCreating" class="creation-form">
          <div class="form-header">
            <h2>新建工作区</h2>
            <button class="btn-icon" @click="isCreating = false">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <div class="form-body">
            <div class="form-group">
              <label>工作区名称</label>
              <input v-model="form.name" placeholder="例：PC-01-工作室" />
            </div>
            <div class="form-group">
              <label>根路径 (Root Path)</label>
              <input v-model="form.root_path" placeholder="C:\Users\Admin\TK-Workspace" />
            </div>
            <div class="form-actions">
              <button class="btn-secondary" @click="isCreating = false">取消</button>
              <button class="btn-primary" :disabled="!form.name || !form.root_path" @click="handleCreate">
                保存工作区
              </button>
            </div>
          </div>
        </div>

        <!-- 空态 -->
        <div v-else-if="!selectedWorkspace" class="empty-detail">
          <span class="material-symbols-outlined" style="font-size:64px;opacity:0.2">lan</span>
          <p>选择左侧工作区查看详情，或点击新建</p>
        </div>

        <!-- 详情视图 -->
        <div v-else class="detail-view">
          <div class="detail-header">
            <div class="detail-title">
              <h2>{{ selectedWorkspace.name }}</h2>
              <span class="status-badge" :class="selectedWorkspace.status">{{ statusLabel(selectedWorkspace.status) }}</span>
            </div>
            <div class="detail-actions">
              <button class="btn-secondary" @click="handleHealthCheck">
                <span class="material-symbols-outlined">health_and_safety</span>健康检查
              </button>
              <button class="btn-danger" @click="handleDelete">
                <span class="material-symbols-outlined">delete</span>删除
              </button>
            </div>
          </div>

          <div class="detail-meta">
            <div class="meta-row"><span class="meta-label">存储路径</span><span>{{ selectedWorkspace.root_path }}</span></div>
            <div class="meta-row"><span class="meta-label">错误次数</span><span>{{ selectedWorkspace.error_count }}</span></div>
            <div class="meta-row"><span class="meta-label">创建时间</span><span>{{ selectedWorkspace.created_at }}</span></div>
          </div>

          <div class="detail-sections">
            <div class="detail-section">
              <h3>
                <span class="material-symbols-outlined">open_in_browser</span>
                浏览器实例
              </h3>
              <div class="empty-sub">后端接入后显示浏览器实例列表</div>
            </div>
            <div class="detail-section">
              <h3>
                <span class="material-symbols-outlined">link</span>
                执行绑定
              </h3>
              <div class="empty-sub">后端接入后显示账号-工作区绑定关系</div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

interface Workspace {
  id: string;
  name: string;
  root_path: string;
  status: 'online' | 'offline' | 'running' | 'error';
  error_count: number;
  last_used_at: string | null;
  created_at: string;
}

const workspaces = ref<Workspace[]>([]);
const selectedId = ref<string | null>(null);
const isCreating = ref(false);
const form = ref({ name: '', root_path: '' });

const selectedWorkspace = computed(() =>
  workspaces.value.find((w) => w.id === selectedId.value) ?? null
);

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    online: '在线',
    offline: '离线',
    running: '运行中',
    error: '错误'
  };
  return map[status] ?? status;
}

function handleCreate(): void {
  if (!form.value.name || !form.value.root_path) return;
  alert('后端接入后可创建工作区（B-M11 待实现）');
  isCreating.value = false;
}

function handleHealthCheck(): void {
  alert('后端接入后可执行健康检查（B-M11 待实现）');
}

function handleDelete(): void {
  if (!selectedWorkspace.value) return;
  if (!confirm(`确认删除工作区"${selectedWorkspace.value.name}"？`)) return;
  alert('后端接入后可删除工作区（B-M11 待实现）');
}
</script>

<style scoped>
.device-workspace-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  overflow: hidden;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-lg);
  height: 56px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.header-icon { color: var(--brand-primary); font-size: 22px; }
.header-left h1 { font-size: 17px; font-weight: 600; margin: 0; }

.page-content {
  display: grid;
  grid-template-columns: 300px 1fr;
  flex: 1;
  overflow: hidden;
}

/* ── 侧边栏 ── */
.workspace-sidebar {
  background: var(--bg-card);
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 10px var(--spacing-md);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.sidebar-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.empty-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px var(--spacing-md);
  text-align: center;
  color: var(--text-muted);
  gap: 8px;
  font-size: 13px;
}

.workspace-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border-radius: var(--radius-md);
  margin-bottom: 6px;
  cursor: pointer;
  border: 1px solid var(--border-subtle);
  transition: background 0.15s, border-color 0.15s;
  position: relative;
}

.workspace-card:hover { background: var(--bg-hover); }
.workspace-card.active { border-color: var(--brand-primary); background: rgba(0,242,234,0.05); }

.ws-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
}
.ws-status-dot.online { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
.ws-status-dot.offline { background: var(--text-muted); }
.ws-status-dot.running { background: #3b82f6; }
.ws-status-dot.error { background: var(--brand-secondary); }

.ws-info { flex: 1; min-width: 0; }
.ws-name { font-size: 13px; font-weight: 600; margin-bottom: 3px; }
.ws-meta { font-size: 11px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ws-err-badge { background: var(--brand-secondary); color: #fff; font-size: 10px; padding: 1px 6px; border-radius: 10px; }

/* ── 详情区 ── */
.workspace-detail { padding: var(--spacing-lg); overflow-y: auto; }

.empty-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  gap: 12px;
  font-size: 13px;
}

.creation-form { max-width: 560px; }
.form-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--spacing-lg); }
.form-header h2 { font-size: 16px; font-weight: 600; margin: 0; }
.form-group { margin-bottom: var(--spacing-md); }
.form-group label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
.form-group input {
  width: 100%;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  padding: 10px var(--spacing-sm);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}
.form-group input:focus { border-color: var(--brand-primary); }
.form-actions { display: flex; gap: var(--spacing-sm); justify-content: flex-end; margin-top: var(--spacing-lg); }

.detail-view {}
.detail-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--spacing-lg); }
.detail-title { display: flex; align-items: center; gap: 10px; }
.detail-title h2 { font-size: 18px; font-weight: 600; margin: 0; }
.detail-actions { display: flex; gap: var(--spacing-sm); }

.status-badge { font-size: 11px; padding: 3px 10px; border-radius: 20px; }
.status-badge.online { background: rgba(34,197,94,0.15); color: #22c55e; }
.status-badge.offline { background: rgba(255,255,255,0.05); color: var(--text-muted); }
.status-badge.running { background: rgba(59,130,246,0.15); color: #3b82f6; }
.status-badge.error { background: rgba(255,0,80,0.15); color: var(--brand-secondary); }

.detail-meta { background: var(--bg-elevated); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: var(--spacing-md); margin-bottom: var(--spacing-lg); }
.meta-row { display: flex; gap: 16px; padding: 6px 0; border-bottom: 1px solid var(--border-subtle); font-size: 13px; }
.meta-row:last-child { border-bottom: none; }
.meta-label { color: var(--text-muted); min-width: 80px; }

.detail-sections { display: flex; flex-direction: column; gap: var(--spacing-md); }
.detail-section { background: var(--bg-elevated); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: var(--spacing-md); }
.detail-section h3 { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; margin: 0 0 var(--spacing-md) 0; color: var(--text-secondary); }
.empty-sub { font-size: 12px; color: var(--text-muted); text-align: center; padding: 20px 0; }

/* ── 按钮 ── */
.btn-primary {
  display: flex; align-items: center; gap: 5px;
  background: var(--brand-primary); color: #000; border: none;
  padding: 7px 16px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 700;
  cursor: pointer; transition: opacity 0.15s;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  display: flex; align-items: center; gap: 5px;
  background: var(--bg-elevated); color: var(--text-primary);
  border: 1px solid var(--border-default);
  padding: 7px 14px; border-radius: var(--radius-sm); font-size: 13px; cursor: pointer;
}

.btn-danger {
  display: flex; align-items: center; gap: 5px;
  background: transparent; color: var(--brand-secondary);
  border: 1px solid var(--brand-secondary);
  padding: 7px 14px; border-radius: var(--radius-sm); font-size: 13px; cursor: pointer;
}

.btn-icon {
  background: transparent; border: none; color: var(--text-secondary);
  cursor: pointer; padding: 4px; display: flex; align-items: center;
}
</style>
