<template>
  <ProjectContextGuard>
    <div class="publishing-page">
    <!-- 工具栏 -->
    <header class="toolbar">
      <div class="toolbar-left">
        <button class="btn-primary" @click="showAddPlan = true">
          <span class="material-symbols-outlined">calendar_add_on</span>新建发布计划
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
      </div>
    </header>

    <main class="page-layout">
      <!-- 左：计划列表 -->
      <aside class="plan-sidebar">
        <div v-if="filteredPlans.length === 0" class="empty-guide">
          <span class="material-symbols-outlined guide-icon">rocket_launch</span>
          <h3>还没有发布计划</h3>
          <p>点击"新建发布计划"安排您的视频发布</p>
          <button class="btn-primary" @click="showAddPlan = true">
            <span class="material-symbols-outlined">add</span>立即创建
          </button>
        </div>
        <div v-else class="plan-list">
          <div
            v-for="plan in filteredPlans"
            :key="plan.id"
            class="plan-item"
            :class="{ active: selectedPlanId === plan.id }"
            @click="selectedPlanId = plan.id"
          >
            <div class="plan-row1">
              <span class="plan-title">{{ plan.title || '（无标题）' }}</span>
              <span class="status-badge" :class="plan.status">{{ statusLabel(plan.status) }}</span>
            </div>
            <div class="plan-row2">
              <span class="plan-meta">账号：{{ plan.accountName }}</span>
            </div>
            <div class="plan-row2">
              <span class="plan-meta">{{ plan.scheduledAt ? '定时：' + plan.scheduledAt : '立即发布' }}</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 右：计划详情 -->
      <section class="detail-area">
        <div v-if="!selectedPlan" class="detail-placeholder">
          <span class="material-symbols-outlined" style="font-size:56px;opacity:0.2">assignment</span>
          <p>选择左侧发布计划查看详情与预检状态</p>
        </div>
        <div v-else class="detail-content">
          <div class="detail-header">
            <h2>{{ selectedPlan.title || '发布计划详情' }}</h2>
            <span class="status-badge lg" :class="selectedPlan.status">{{ statusLabel(selectedPlan.status) }}</span>
          </div>

          <!-- 预检结果 -->
          <div class="precheck-section">
            <h4>
              <span class="material-symbols-outlined">checklist</span>发布预检
            </h4>
            <div class="check-list">
              <div
                v-for="check in precheckItems"
                :key="check.code"
                class="check-item"
                :class="check.result"
              >
                <span class="check-icon material-symbols-outlined">
                  {{ check.result === 'passed' ? 'check_circle' : check.result === 'failed' ? 'cancel' : 'radio_button_unchecked' }}
                </span>
                <div>
                  <div class="check-title">{{ check.label }}</div>
                  <div class="check-msg" v-if="check.message">{{ check.message }}</div>
                </div>
              </div>
            </div>

            <div class="precheck-actions">
              <button class="btn-secondary" @click="handlePrecheck">
                <span class="material-symbols-outlined">refresh</span>执行预检
              </button>
              <button
                class="btn-primary"
                :disabled="hasErrorChecks"
                @click="handleSubmit"
              >
                <span class="material-symbols-outlined">publish</span>提交发布
              </button>
              <button class="btn-danger" @click="handleCancel">
                <span class="material-symbols-outlined">cancel</span>取消
              </button>
            </div>
          </div>

          <!-- 回执信息 -->
          <div class="receipt-section" v-if="receipt">
            <h4>
              <span class="material-symbols-outlined">receipt_long</span>发布回执
            </h4>
            <div class="receipt-status" :class="receipt.status">{{ receipt.status }}</div>
            <div v-if="receipt.error" class="receipt-error">{{ receipt.error }}</div>
          </div>
        </div>
      </section>
    </main>

    <!-- 新建计划抽屉 -->
    <div v-if="showAddPlan" class="drawer-overlay" @click.self="showAddPlan = false">
      <div class="drawer">
        <div class="drawer-header">
          <h2>新建发布计划</h2>
          <button class="btn-icon" @click="showAddPlan = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="drawer-body">
          <div class="form-group">
            <label>视频标题</label>
            <input v-model="addForm.title" placeholder="TikTok 发布标题" />
          </div>
          <div class="form-group">
            <label>发布账号</label>
            <input v-model="addForm.accountName" placeholder="账号昵称或ID" />
          </div>
          <div class="form-group">
            <label>定时发布（选填）</label>
            <input v-model="addForm.scheduledAt" type="datetime-local" />
          </div>
          <div class="drawer-footer">
            <button class="btn-secondary" @click="showAddPlan = false">取消</button>
            <button class="btn-primary" @click="handleCreatePlan">保存计划</button>
          </div>
        </div>
      </div>
    </div>
  </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";

interface PublishPlan {
  id: string;
  title: string;
  accountName: string;
  scheduledAt: string | null;
  status: 'draft' | 'ready' | 'submitting' | 'published' | 'failed' | 'cancelled';
}

interface PrecheckItem {
  code: string;
  label: string;
  result: 'passed' | 'failed' | 'pending';
  message?: string;
}

interface Receipt {
  status: string;
  error?: string;
}

const plans = ref<PublishPlan[]>([]);
const selectedPlanId = ref<string | null>(null);
const statusFilter = ref<string>('all');
const showAddPlan = ref(false);
const receipt = ref<Receipt | null>(null);
const addForm = ref({ title: '', accountName: '', scheduledAt: '' });

const precheckItems = ref<PrecheckItem[]>([
  { code: 'account_online', label: '账号在线状态', result: 'pending' },
  { code: 'render_ready', label: '视频渲染就绪', result: 'pending' },
  { code: 'workspace_bound', label: '工作区绑定', result: 'pending' },
  { code: 'has_title', label: '发布信息完整', result: 'pending' }
]);

const statusFilters = [
  { value: 'all', label: '全部' },
  { value: 'draft', label: '草稿' },
  { value: 'ready', label: '就绪' },
  { value: 'published', label: '已发布' },
  { value: 'failed', label: '失败' }
];

const filteredPlans = computed(() => {
  if (statusFilter.value === 'all') return plans.value;
  return plans.value.filter((p) => p.status === statusFilter.value);
});

const selectedPlan = computed(() =>
  plans.value.find((p) => p.id === selectedPlanId.value) ?? null
);

const hasErrorChecks = computed(() =>
  precheckItems.value.some((c) => c.result === 'failed')
);

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: '草稿', ready: '就绪', submitting: '发布中',
    published: '已发布', failed: '失败', cancelled: '已取消'
  };
  return map[status] ?? status;
}

function handlePrecheck(): void {
  alert('后端接入后可执行预检（B-M13 待实现）');
}

function handleSubmit(): void {
  if (hasErrorChecks.value) return;
  alert('后端接入后可提交发布（B-M13 待实现）');
}

function handleCancel(): void {
  alert('后端接入后可取消发布（B-M13 待实现）');
}

function handleCreatePlan(): void {
  if (!addForm.value.title) return;
  alert('后端接入后可保存计划（B-M13 待实现）');
  showAddPlan.value = false;
}
</script>

<style scoped>
.publishing-page {
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

.page-layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  flex: 1;
  overflow: hidden;
}

.plan-sidebar {
  border-right: 1px solid var(--border-default);
  background: var(--bg-card);
  overflow-y: auto;
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

.plan-list { padding: var(--spacing-sm); }

.plan-item {
  padding: 12px;
  border-radius: var(--radius-md);
  margin-bottom: 6px;
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background 0.15s;
}
.plan-item:hover { background: var(--bg-hover); }
.plan-item.active { border-color: var(--brand-primary); background: rgba(0,242,234,0.04); }

.plan-row1 { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.plan-title { font-size: 13px; font-weight: 600; }
.plan-row2 { }
.plan-meta { font-size: 11px; color: var(--text-muted); }

.status-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
}
.status-badge.draft { background: rgba(255,255,255,0.08); color: var(--text-muted); }
.status-badge.ready { background: rgba(34,197,94,0.15); color: #4ade80; }
.status-badge.submitting { background: rgba(59,130,246,0.15); color: #60a5fa; }
.status-badge.published { background: rgba(34,197,94,0.2); color: #22c55e; }
.status-badge.failed { background: rgba(255,0,80,0.15); color: var(--brand-secondary); }
.status-badge.cancelled { background: rgba(255,255,255,0.05); color: var(--text-muted); }
.status-badge.lg { font-size: 12px; padding: 4px 12px; }

.detail-area { padding: var(--spacing-lg); overflow-y: auto; }

.detail-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  gap: 8px;
  font-size: 13px;
}

.detail-content { display: flex; flex-direction: column; gap: var(--spacing-lg); }
.detail-header { display: flex; align-items: center; gap: 12px; }
.detail-header h2 { font-size: 18px; font-weight: 600; margin: 0; }

.precheck-section, .receipt-section {
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
}

.precheck-section h4, .receipt-section h4 {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--text-muted); margin: 0 0 var(--spacing-md) 0;
}

.check-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: var(--spacing-md); }

.check-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
}

.check-icon { font-size: 18px; flex-shrink: 0; }
.check-item.passed .check-icon { color: #22c55e; }
.check-item.failed .check-icon { color: var(--brand-secondary); }
.check-item.pending .check-icon { color: var(--text-muted); }

.check-title { color: var(--text-primary); }
.check-msg { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

.precheck-actions { display: flex; gap: var(--spacing-sm); }

.receipt-status { font-size: 13px; font-weight: 600; }
.receipt-error { font-size: 12px; color: var(--brand-secondary); margin-top: 6px; }

/* 抽屉 */
.drawer-overlay {
  position: absolute; inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex; justify-content: flex-end;
  z-index: 100;
}
.drawer { width: 400px; background: var(--bg-elevated); border-left: 1px solid var(--border-default); display: flex; flex-direction: column; height: 100%; }
.drawer-header { display: flex; align-items: center; justify-content: space-between; padding: var(--spacing-md) var(--spacing-lg); border-bottom: 1px solid var(--border-default); }
.drawer-header h2 { font-size: 16px; font-weight: 600; margin: 0; }
.drawer-body { flex: 1; overflow-y: auto; padding: var(--spacing-lg); }
.drawer-footer { display: flex; gap: var(--spacing-sm); justify-content: flex-end; margin-top: var(--spacing-xl); }

.form-group { margin-bottom: var(--spacing-md); }
.form-group label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
.form-group input {
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
.form-group input:focus { border-color: var(--brand-primary); }

/* 按钮 */
.btn-primary {
  display: flex; align-items: center; gap: 5px;
  background: var(--brand-primary); color: #000; border: none;
  padding: 7px 14px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 700; cursor: pointer;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  display: flex; align-items: center; gap: 5px;
  background: var(--bg-card); color: var(--text-primary);
  border: 1px solid var(--border-default);
  padding: 7px 14px; border-radius: var(--radius-sm); font-size: 12px; cursor: pointer;
}
.btn-danger {
  display: flex; align-items: center; gap: 5px;
  background: transparent; color: var(--brand-secondary);
  border: 1px solid var(--brand-secondary);
  padding: 7px 14px; border-radius: var(--radius-sm); font-size: 12px; cursor: pointer;
}
.btn-icon {
  background: transparent; border: none; color: var(--text-secondary);
  cursor: pointer; padding: 4px; display: flex; align-items: center;
}
</style>
