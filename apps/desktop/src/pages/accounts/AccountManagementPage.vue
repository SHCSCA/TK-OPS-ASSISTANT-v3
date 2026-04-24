<template>
  <div class="page-container h-full">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 账号与设备</div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">账号管理</h1>
          <div class="page-header__subtitle">管理多平台分发账号。支持根据发布可用性自动分类与引导修复。</div>
        </div>
        <div class="page-header__actions">
          <Button variant="secondary" @click="handleReload" :disabled="store.status === 'loading'">
            <template #leading><span class="material-symbols-outlined">refresh</span></template>
            重新拉取
          </Button>
          <Button variant="primary" @click="store.showAddModal = true" :disabled="store.status === 'loading'">
            <template #leading><span class="material-symbols-outlined">person_add</span></template>
            添加账号
          </Button>
        </div>
      </div>
    </header>

    <!-- 全局状态反馈 -->
    <div v-if="store.error" class="dashboard-alert" data-tone="danger">
      <span class="material-symbols-outlined">error</span>
      <span>{{ store.error }}</span>
    </div>
    <div v-else-if="store.status === 'loading'" class="dashboard-alert" data-tone="brand">
      <span class="material-symbols-outlined spinning">sync</span>
      <span>正在读取真实账号对象与分组目录，请稍候...</span>
    </div>

    <!-- 概览指标 -->
    <div class="summary-grid">
      <Card class="summary-card">
        <span class="sc-label">可发布账号</span>
        <strong class="sc-val text-success">{{ publishableCount }}</strong>
        <p class="sc-hint">已激活且凭证有效</p>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">待验证/失效</span>
        <strong class="sc-val text-warning">{{ brokenCount }}</strong>
        <p class="sc-hint">凭证过期或未登录</p>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">总账号数</span>
        <strong class="sc-val">{{ store.accounts.length }}</strong>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">同步健康</span>
        <strong class="sc-val text-success">100%</strong>
        <p class="sc-hint">与 Runtime 实时同步</p>
      </Card>
    </div>

    <div class="workspace-grid">
      <aside class="workspace-rail">
        <!-- V2 筛选器 -->
        <Card class="rail-card">
          <div class="rail-card__header">
            <h3>可用性分类</h3>
          </div>
          <div class="rail-card__body">
            <div class="availability-filters">
              <button 
                class="filter-btn" 
                :class="{ active: currentAvailability === 'all' }"
                @click="currentAvailability = 'all'"
              >
                全部账号
                <span class="count">{{ store.accounts.length }}</span>
              </button>
              <button 
                class="filter-btn" 
                :class="{ active: currentAvailability === 'publishable' }"
                @click="currentAvailability = 'publishable'"
              >
                <span class="material-symbols-outlined text-success">check_circle</span>
                可发布
                <span class="count">{{ publishableCount }}</span>
              </button>
              <button 
                class="filter-btn" 
                :class="{ active: currentAvailability === 'pending' }"
                @click="currentAvailability = 'pending'"
              >
                <span class="material-symbols-outlined text-warning">error</span>
                待验证
                <span class="count">{{ pendingCount }}</span>
              </button>
              <button 
                class="filter-btn" 
                :class="{ active: currentAvailability === 'invalid' }"
                @click="currentAvailability = 'invalid'"
              >
                <span class="material-symbols-outlined text-danger">cancel</span>
                已失效
                <span class="count">{{ invalidCount }}</span>
              </button>
            </div>

            <div class="divider">按分组筛选</div>
            
            <div class="group-tabs">
              <button :class="{ active: store.selectedGroupId === null }" type="button" @click="handleSelectGroup(null)">
                全部
              </button>
              <div v-if="store.groups.length === 0" class="empty-hint-inline">
                Runtime 尚未返回账号分组目录，不会伪造绑定关系
              </div>
              <button
                v-for="group in store.groups"
                :key="group.id"
                :class="{ active: store.selectedGroupId === group.id }"
                type="button"
                @click="handleSelectGroup(group.id)"
              >
                {{ group.name }}
              </button>
            </div>
          </div>
        </Card>

        <!-- 账号列表 -->
        <Card class="rail-card flex-1">
          <div class="rail-card__header">
            <div class="search-box-v2">
              <span class="material-symbols-outlined">search</span>
              <input v-model="searchQuery" type="search" placeholder="快速搜索..." />
            </div>
          </div>
          <div class="rail-card__body no-padding scroll-area">
            <div v-if="visibleAccounts.length === 0" class="empty-state">
              <span class="material-symbols-outlined">person_off</span>
              <strong>暂无匹配账号</strong>
            </div>
            <div v-else class="account-list">
              <button
                v-for="account in visibleAccounts"
                :key="account.id"
                class="account-card"
                :class="{ 'account-card--selected': selectedAccountId === account.id }"
                :data-testid="`account-card-${account.id}`"
                @click="selectAccount(account)"
              >
                <div class="ac-head">
                  <div class="ac-avatar" :data-platform="account.platform">
                    <img v-if="account.avatarUrl" :src="account.avatarUrl" :alt="account.name" />
                    <span v-else>{{ account.name.charAt(0).toUpperCase() }}</span>
                  </div>
                  <div class="ac-meta">
                    <strong>{{ account.name }}</strong>
                    <span>{{ platformLabel(account.platform) }} · @{{ account.username || 'unknown' }}</span>
                  </div>
                  <Chip size="xs" :variant="statusTone(account.status)">{{ getStatusLabel(account.status) }}</Chip>
                </div>
              </button>
            </div>
          </div>
        </Card>
      </aside>

      <main class="workspace-main">
        <Card class="detail-card h-full" v-if="selectedAccount">
          <div class="detail-card__header">
            <div class="ac-header-info">
              <div class="ac-avatar large" :data-platform="selectedAccount.platform">
                <img v-if="selectedAccount.avatarUrl" :src="selectedAccount.avatarUrl" />
                <span v-else>{{ selectedAccount.name.charAt(0).toUpperCase() }}</span>
              </div>
              <div>
                <h3>{{ selectedAccount.name }}</h3>
                <p class="summary">账号来自 {{ platformLabel(selectedAccount.platform) }}，最近校验于 {{ formatDateTime(selectedAccount.updatedAt) }}</p>
              </div>
            </div>
            <div class="actions">
              <Button variant="secondary" @click="handleRefreshSelected" :disabled="store.status === 'loading'">
                <template #leading><span class="material-symbols-outlined">refresh</span></template>
                立即验证
              </Button>
            </div>
          </div>

          <div class="detail-card__body scroll-area">
            <!-- V2: 引导式反馈块 -->
            <div v-if="selectedAccount.status !== 'active'" class="guiding-banner" :data-tone="selectedAccount.status === 'suspended' ? 'danger' : 'warning'">
              <span class="material-symbols-outlined">{{ selectedAccount.status === 'suspended' ? 'block' : 'info' }}</span>
              <div class="gb-content">
                <strong>{{ guidanceTitle }}</strong>
                <p>{{ guidanceMessage }}</p>
              </div>
              <Button variant="primary" size="sm" @click="handleRefreshSelected">{{ guidanceAction }}</Button>
            </div>

            <div class="metric-grid">
              <div class="metric-card">
                <span>粉丝总数</span>
                <strong>{{ formatCount(selectedAccount.followerCount) }}</strong>
              </div>
              <div class="metric-card">
                <span>已发视频</span>
                <strong>{{ formatCount(selectedAccount.videoCount) }}</strong>
              </div>
              <div class="metric-card">
                <span>获赞总数</span>
                <strong>—</strong>
              </div>
            </div>

            <dl class="metadata-list">
              <div class="m-item"><dt>授权状态</dt><dd><Chip :variant="statusTone(selectedAccount.status)" size="sm">{{ getStatusLabel(selectedAccount.status) }}</Chip></dd></div>
              <div class="m-item"><dt>用户名</dt><dd>{{ selectedAccount.username || "未提供" }}</dd></div>
              <div class="m-item"><dt>授权到期</dt><dd class="text-mono">{{ selectedAccount.authExpiresAt ? formatDateTime(selectedAccount.authExpiresAt) : "长期有效" }}</dd></div>
              <div class="m-item"><dt>备注说明</dt><dd>{{ selectedAccount.notes || "无" }}</dd></div>
            </dl>

            <div class="detail-actions">
              <Button variant="danger" ghost @click="handleDeleteAccount(selectedAccount)">删除该账号</Button>
              <Button variant="ghost" @click="clearSelection">关闭详情面板</Button>
            </div>
          </div>
        </Card>
        <div v-else class="detail-card empty-wrapper">
          <div class="empty-state">
            <span class="material-symbols-outlined">account_circle</span>
            <strong>选择一个账号查看详情</strong>
            <p>在这里可以管理发布凭证并查看账号统计。</p>
          </div>
        </div>
      </main>
    </div>

    <!-- 添加账号抽屉保持不变 -->
    <transition name="drawer">
      <div v-if="store.showAddModal" class="drawer-overlay" @click="store.showAddModal = false">
        <aside class="drawer-panel" @click.stop>
          <div class="drawer-panel__header">
            <div>
              <p class="drawer-panel__eyebrow">新建账号</p>
              <h2>创建真实账号对象</h2>
            </div>
            <button class="drawer-panel__close" @click="store.showAddModal = false">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <div class="drawer-panel__body">
            <form class="drawer-form" @submit.prevent="handleAddAccount">
              <div class="form-group">
                <label>账号显示名称</label>
                <Input v-model="addForm.name" placeholder="例如：我的主账号" required />
              </div>
              <div class="form-group">
                <label>目标平台</label>
                <select v-model="addForm.platform" class="ui-input-field">
                  <option value="tiktok">TikTok</option>
                  <option value="youtube">YouTube</option>
                </select>
              </div>
              <div class="form-group">
                <label>用户名</label>
                <Input v-model="addForm.username" placeholder="username" />
              </div>
              <div class="form-group">
                <label>初始状态</label>
                <select v-model="addForm.status" class="ui-input-field">
                  <option value="active">已激活</option>
                  <option value="inactive">未登录</option>
                  <option value="expired">凭证过期</option>
                  <option value="suspended">已封禁</option>
                </select>
              </div>
              <div class="drawer-actions">
                <Button variant="ghost" @click="store.showAddModal = false">取消</Button>
                <Button variant="primary" type="submit" :disabled="!addForm.name || store.status === 'loading'">保存账号</Button>
              </div>
            </form>
          </div>
        </aside>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useAccountManagementStore } from "@/stores/account-management";
import { useShellUiStore } from "@/stores/shell-ui";
import type { AccountDto } from "@/types/runtime";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import Input from "@/components/ui/Input/Input.vue";

const store = useAccountManagementStore();
const shellUiStore = useShellUiStore();
const searchQuery = ref("");
const selectedAccountId = ref<string | null>(null);
const currentAvailability = ref<"all" | "publishable" | "pending" | "invalid">("all");
const addForm = reactive({ name: "", platform: "tiktok", username: "", status: "active" });

const publishableCount = computed(() => store.accounts.filter(a => a.publishReadiness?.canPublish).length);
const pendingCount = computed(() => store.accounts.filter(a => a.publishReadiness?.status === 'action_required' || a.publishReadiness?.status === 'binding_required').length);
const invalidCount = computed(() => store.accounts.filter(a => a.publishReadiness?.status === 'blocked' || a.publishReadiness?.status === 'expired').length);
const brokenCount = computed(() => store.accounts.filter(a => !a.publishReadiness?.canPublish).length);

const visibleAccounts = computed(() => {
  let list = store.accounts;
  
  if (currentAvailability.value === 'publishable') list = list.filter(a => a.publishReadiness?.canPublish);
  else if (currentAvailability.value === 'pending') list = list.filter(a => a.publishReadiness?.status === 'action_required' || a.publishReadiness?.status === 'binding_required');
  else if (currentAvailability.value === 'invalid') list = list.filter(a => a.publishReadiness?.status === 'blocked' || a.publishReadiness?.status === 'expired');
  
  if (store.selectedGroupId !== null) {
     list = list.filter(a => (a as any).groupId === store.selectedGroupId);
  }

  const query = searchQuery.value.trim().toLowerCase();
  if (query) {
    list = list.filter(a => a.name.toLowerCase().includes(query) || a.username?.toLowerCase().includes(query));
  }
  
  return list;
});

const selectedAccount = computed(() => store.accounts.find(a => a.id === selectedAccountId.value) ?? null);

const guidanceTitle = computed(() => {
  if (!selectedAccount.value) return "";
  const readiness = selectedAccount.value.publishReadiness;
  if (!readiness) return "未知状态";
  if (readiness.status === 'expired') return "账号凭证已过期";
  if (readiness.status === 'blocked') return "账号已被封禁/失效";
  if (readiness.status === 'binding_required') return "账号缺少环境绑定";
  return readiness.errorMessage || "账号需要进一步验证";
});

const guidanceMessage = computed(() => {
  if (!selectedAccount.value) return "";
  const readiness = selectedAccount.value.publishReadiness;
  if (!readiness) return "无法读取账号发布就绪状态。";
  if (readiness.suggestedAction) return readiness.suggestedAction;
  if (readiness.status === 'expired') return "当前授权令牌已失效，发布任务将被阻断。请重新完成登录授权。";
  if (readiness.status === 'blocked') return "由于违反平台规则或安全校验失败，该账号目前不可用。";
  return readiness.errorMessage || "该账号对象已创建，但尚未建立真实的 Runtime 浏览器会话连接。";
});

const guidanceAction = computed(() => {
  if (selectedAccount.value?.publishReadiness?.status === 'blocked') return "重新扫描";
  return "前往验证";
});

onMounted(() => { void store.load(); });

watch(selectedAccount, (account) => {
  if (!account) {
    shellUiStore.closeDetailPanel();
    return;
  }
  // 在详情面板展示账号核心指标与状态
  shellUiStore.openDetailWithContext({
    id: "account",
    title: account.name,
    sections: [
      {
        title: "账号概览",
        fields: [
          { label: "平台", value: platformLabel(account.platform) },
          { label: "用户名", value: account.username || "@unknown" },
          { label: "状态", value: getStatusLabel(account.status) }
        ]
      },
      {
        title: "指标统计",
        fields: [
          { label: "粉丝数", value: formatCount(account.followerCount) },
          { label: "视频数", value: formatCount(account.videoCount) }
        ]
      },
      {
        title: "分组与绑定",
        fields: [
          { label: "所属分组", value: store.groups.find(g => (account as any).groupId === g.id)?.name ?? "默认分组" }
        ]
      }
    ]
  });
}, { immediate: true });

function handleReload() { void store.load(); }
function handleSelectGroup(groupId: string | null) {
  selectedAccountId.value = null;
  store.setSelectedGroup(groupId);
}

function selectAccount(account: AccountDto) { selectedAccountId.value = account.id; }
function clearSelection() { selectedAccountId.value = null; }

async function handleAddAccount() {
  await store.addAccount({ ...addForm });
  addForm.name = ""; store.showAddModal = false;
}

async function handleDeleteAccount(account: AccountDto) {
  if (!window.confirm(`确认删除账号“${account.name}”吗？`)) return;
  await store.removeAccount(account.id);
  if (selectedAccountId.value === account.id) clearSelection();
}

async function handleRefreshSelected() {
  if (!selectedAccount.value) return;
  await store.refreshStats(selectedAccount.value.id);
}

function formatCount(count: number | null) {
  if (count === null) return "—";
  return count.toLocaleString();
}

function statusTone(status: string): any {
  if (status === "ready" || status === "active") return "success";
  if (status === "blocked" || status === "suspended") return "danger";
  if (status === "expired" || status === "action_required") return "warning";
  return "neutral";
}

function getStatusLabel(status: string) {
  const map: any = { 
    ready: "可发布", 
    active: "可发布",
    action_required: "待验证", 
    inactive: "待验证",
    blocked: "已失效", 
    suspended: "已失效",
    expired: "凭证过期",
    binding_required: "未绑定"
  };
  return map[status] || status;
}

function platformLabel(platform: string) {
  return platform.charAt(0).toUpperCase() + platform.slice(1);
}

function formatDateTime(v: string) {
  return new Date(v).toLocaleString("zh-CN", { hour12: false });
}
</script>

<style scoped src="./AccountManagementPage.css"></style>
