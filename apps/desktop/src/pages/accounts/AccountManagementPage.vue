<template>
  <div class="page-container h-full">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 账号与设备</div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">账号管理</h1>
          <div class="page-header__subtitle">只展示 Runtime 返回的账号对象、状态、分组目录和真实统计，不伪造账号绑定或健康分数。</div>
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

    <div v-if="store.error" class="dashboard-alert" data-tone="danger">
      <span class="material-symbols-outlined">error</span>
      <span>{{ store.error }}</span>
    </div>
    <div v-else-if="store.status === 'loading'" class="dashboard-alert" data-tone="brand">
      <span class="material-symbols-outlined spinning">sync</span>
      <span>正在读取真实账号对象与分组目录，请稍候...</span>
    </div>
    <div v-else-if="store.groups.length === 0" class="dashboard-alert" data-tone="warning">
      <span class="material-symbols-outlined">warning</span>
      <span>Runtime 尚未返回账号分组目录。页面只展示真实账号对象，不会伪造绑定关系。</span>
    </div>

    <div class="summary-grid">
      <Card class="summary-card">
        <span class="sc-label">账号总数</span>
        <strong class="sc-val">{{ store.accounts.length }}</strong>
        <p class="sc-hint">Runtime 返回的真实账号对象</p>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">当前筛选</span>
        <strong class="sc-val">{{ visibleAccounts.length }}</strong>
        <p class="sc-hint">{{ currentGroupLabel }}</p>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">当前选中</span>
        <strong class="sc-val" :title="selectedAccount ? selectedAccount.name : '未选中'">
          {{ selectedAccount ? selectedAccount.name : "未选中" }}
        </strong>
        <p class="sc-hint" :title="selectedAccount ? selectedAccount.platform : '请在左侧选中一个账号'">
          {{ selectedAccount ? selectedAccount.platform : "请在左侧选中一个账号" }}
        </p>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">分组目录</span>
        <strong class="sc-val">{{ store.groups.length }}</strong>
        <p class="sc-hint">仅用于真实筛选，不写入假绑定</p>
      </Card>
    </div>

    <div class="workspace-grid">
      <aside class="workspace-rail">
        <Card class="rail-card">
          <div class="rail-card__header">
            <h3>筛选真实账号</h3>
          </div>
          <div class="rail-card__body">
            <div class="search-box">
              <span class="material-symbols-outlined">search</span>
              <input v-model="searchQuery" type="search" placeholder="搜索账号名称或用户名" />
            </div>

            <div class="group-tabs">
              <button :class="{ active: store.selectedGroupId === null }" type="button" @click="handleSelectGroup(null)">
                全部账号
              </button>
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

            <p class="rail-card__hint">{{ groupsHint }}</p>
          </div>
        </Card>

        <Card class="rail-card flex-1">
          <div class="rail-card__header">
            <h3>{{ listTitle }}</h3>
            <Chip size="sm" variant="brand">{{ visibleAccounts.length }}</Chip>
          </div>
          <div class="rail-card__body no-padding scroll-area">
            <div v-if="store.status === 'loading'" class="empty-state">
              <span class="material-symbols-outlined spinning">sync</span>
              <strong>正在加载账号</strong>
              <p>同步 Runtime 中的账号对象和分组目录。</p>
            </div>
            <div v-else-if="visibleAccounts.length === 0" class="empty-state">
              <span class="material-symbols-outlined">person_off</span>
              <strong>没有符合条件的账号</strong>
              <p>可以切换分组、清空搜索，或者添加一个真实账号对象。</p>
            </div>
            <div v-else class="account-list">
              <button
                v-for="account in visibleAccounts"
                :key="account.id"
                class="account-card"
                :class="{ 'is-selected': selectedAccountId === account.id }"
                @click="selectAccount(account)"
              >
                <div class="ac-head">
                  <div class="ac-avatar" :data-platform="account.platform">
                    <img v-if="account.avatarUrl" :src="account.avatarUrl" :alt="account.name" />
                    <span v-else>{{ account.name.charAt(0).toUpperCase() }}</span>
                  </div>
                  <div class="ac-meta">
                    <strong :title="account.name">{{ account.name }}</strong>
                    <span>@{{ account.username || "未提供用户名" }}</span>
                  </div>
                  <Chip size="sm" :variant="statusTone(account.status)">{{ getStatusLabel(account.status) }}</Chip>
                </div>
                <div class="ac-body">
                  <span>{{ platformLabel(account.platform) }}</span>
                  <span>{{ formatDateTime(account.updatedAt) }}</span>
                </div>
                <div class="ac-stats">
                  <span><strong>{{ formatCount(account.followerCount) }}</strong> 粉丝</span>
                  <span><strong>{{ formatCount(account.videoCount) }}</strong> 视频</span>
                </div>
                <div class="ac-footer">
                  <span class="ac-tag">{{ account.authExpiresAt ? `到期 ${formatDateTime(account.authExpiresAt)}` : "未返回授权到期时间" }}</span>
                  <Button variant="danger" size="sm" :disabled="store.status === 'loading'" @click.stop="handleDeleteAccount(account)">删除</Button>
                </div>
              </button>
            </div>
          </div>
        </Card>
      </aside>

      <main class="workspace-main">
        <Card class="detail-card">
          <div class="detail-card__header">
            <div>
              <h3>{{ selectedAccount ? selectedAccount.name : "未选中账号" }}</h3>
              <p class="summary">{{ selectedAccount ? `账号对象来自 ${platformLabel(selectedAccount.platform)}，选中后会同步打开右侧详情面板。` : "在左侧选择一个账号，右侧会显示真实状态、统计和授权到期时间。" }}</p>
            </div>
            <div class="actions" v-if="selectedAccount">
              <Button variant="secondary" @click="handleRefreshSelected" :disabled="store.status === 'loading'">
                <template #leading><span class="material-symbols-outlined">refresh</span></template>
                刷新统计
              </Button>
            </div>
          </div>

          <div class="detail-card__body" v-if="selectedAccount">
            <dl class="detail-metadata">
              <div><dt>平台</dt><dd>{{ platformLabel(selectedAccount.platform) }}</dd></div>
              <div><dt>状态</dt><dd><Chip :variant="statusTone(selectedAccount.status)" size="sm">{{ getStatusLabel(selectedAccount.status) }}</Chip></dd></div>
              <div><dt>用户名</dt><dd>{{ selectedAccount.username || "未提供用户名" }}</dd></div>
              <div><dt>授权到期</dt><dd>{{ selectedAccount.authExpiresAt ? formatDateTime(selectedAccount.authExpiresAt) : "未返回到期时间" }}</dd></div>
              <div><dt>创建时间</dt><dd>{{ formatDateTime(selectedAccount.createdAt) }}</dd></div>
              <div><dt>更新时间</dt><dd>{{ formatDateTime(selectedAccount.updatedAt) }}</dd></div>
            </dl>

            <div class="detail-block">
              <div class="detail-block__header"><span>真实统计</span></div>
              <div class="metric-grid">
                <div class="metric-card">
                  <span>粉丝</span>
                  <strong>{{ formatCount(selectedAccount.followerCount) }}</strong>
                </div>
                <div class="metric-card">
                  <span>关注</span>
                  <strong>{{ formatCount(selectedAccount.followingCount) }}</strong>
                </div>
                <div class="metric-card">
                  <span>视频</span>
                  <strong>{{ formatCount(selectedAccount.videoCount) }}</strong>
                </div>
              </div>
            </div>

            <div class="detail-block">
              <div class="detail-block__header"><span>标签与备注</span></div>
              <div v-if="selectedTags.length" class="tag-list">
                <span v-for="tag in selectedTags" :key="tag" class="tag-item">{{ tag }}</span>
              </div>
              <p v-else class="detail-empty">Runtime 还没有为该账号返回标签。</p>
              <p class="detail-note">{{ selectedAccount.notes || "Runtime 没有返回备注内容。" }}</p>
            </div>

            <div class="detail-block detail-block--blocked">
              <div class="detail-block__header">
                <span>分组与绑定</span>
                <Chip variant="warning" size="sm">blocked</Chip>
              </div>
              <p class="detail-empty">当前 Runtime 只返回账号对象和分组目录，没有返回 per-account 的绑定字段。页面只做真实筛选，不伪造账号绑定。</p>
            </div>

            <div class="detail-actions">
              <Button variant="primary" @click="openSelectedAccountDetail">打开右侧详情</Button>
              <Button variant="ghost" @click="clearSelection">清空选择</Button>
            </div>
          </div>
          <div class="detail-card__body empty-wrapper" v-else>
            <div class="empty-state">
              <span class="material-symbols-outlined">person_search</span>
              <strong>未选中账号</strong>
              <p>在左侧选择一个真实账号对象，右侧会展示它的统计、授权到期和备注信息。</p>
            </div>
          </div>
        </Card>

        <Card class="detail-card soft-card">
          <div class="detail-block__header"><span>真实边界</span></div>
          <p class="detail-note">账号页只显示 Runtime 真实返回的账号对象，不显示健康分、在线率或人工拼接的绑定结果。</p>
        </Card>
      </main>
    </div>

    <!-- Drawer Modal -->
    <transition name="drawer">
      <div v-if="store.showAddModal" class="drawer-overlay" @click="store.showAddModal = false">
        <aside class="drawer-panel" @click.stop>
          <div class="drawer-panel__header">
            <div>
              <p class="drawer-panel__eyebrow">添加账号</p>
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
                  <option value="instagram">Instagram</option>
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
              <p class="drawer-form__hint">这里创建的只是账号对象，不包含任何假绑定；后续分组和授权状态仍以 Runtime 返回为准。</p>
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
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import { useAccountManagementStore } from "@/stores/account-management";
import type { AccountDto } from "@/types/runtime";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const store = useAccountManagementStore();
const shellUiStore = useShellUiStore();
const searchQuery = ref("");
const selectedAccountId = ref<string | null>(null);

const addForm = reactive({ name: "", platform: "tiktok", username: "", status: "active" });

const visibleAccounts = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return store.accounts;
  return store.accounts.filter((account) => {
    const username = account.username?.toLowerCase() ?? "";
    return account.name.toLowerCase().includes(query) || username.includes(query);
  });
});

const selectedAccount = computed(() => store.accounts.find((account) => account.id === selectedAccountId.value) ?? null);
const selectedTags = computed(() => (selectedAccount.value ? parseTags(selectedAccount.value.tags) : []));
const currentGroupLabel = computed(() => {
  if (store.selectedGroupId === null) return "全部账号";
  const group = store.groups.find((item) => item.id === store.selectedGroupId);
  return group ? `分组：${group.name}` : "当前分组已不存在";
});

const groupsHint = computed(() => {
  if (store.status === "loading") return "Runtime 正在返回分组目录。";
  if (store.groups.length === 0) return "当前没有分组目录，列表仅按账号对象显示。";
  return "分组筛选只影响列表结果，不会写入假绑定。";
});

const listTitle = computed(() => {
  if (store.status === "loading") return "加载中";
  if (visibleAccounts.value.length === 0) return "暂无可见账号";
  return "账号列表";
});

watch(selectedAccount, (account) => {
  if (!account) {
    shellUiStore.clearDetailContext("binding");
    shellUiStore.closeDetailPanel();
    return;
  }
  shellUiStore.openDetailWithContext(buildAccountDetailContext(account));
}, { immediate: true });

onMounted(() => { void store.load(); });
onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("binding");
  shellUiStore.closeDetailPanel();
});

function handleReload() { void store.load(); }
function handleSelectGroup(groupId: string | null) {
  selectedAccountId.value = null;
  shellUiStore.clearDetailContext("binding");
  shellUiStore.closeDetailPanel();
  store.setSelectedGroup(groupId);
}

function selectAccount(account: AccountDto) { selectedAccountId.value = account.id; }
function clearSelection() {
  selectedAccountId.value = null;
  shellUiStore.clearDetailContext("binding");
  shellUiStore.closeDetailPanel();
}

function openSelectedAccountDetail() {
  if (!selectedAccount.value) return;
  shellUiStore.openDetailWithContext(buildAccountDetailContext(selectedAccount.value));
}

async function handleAddAccount() {
  await store.addAccount({ name: addForm.name.trim(), platform: addForm.platform, username: addForm.username.trim(), status: addForm.status });
  addForm.name = ""; addForm.username = ""; addForm.platform = "tiktok"; addForm.status = "active";
  selectedAccountId.value = null;
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

function buildAccountDetailContext(account: AccountDto) {
  return createRouteDetailContext("binding", {
    icon: "account_circle", eyebrow: "账号详情", title: account.name, description: "只展示 Runtime 真实返回的账号对象和状态，不伪造绑定关系。",
    badge: { label: getStatusLabel(account.status), tone: account.status === "active" ? "success" : account.status === "expired" ? "warning" : "neutral" },
    metrics: [
      { id: "followers", label: "粉丝", value: formatCount(account.followerCount), hint: "真实统计" },
      { id: "following", label: "关注", value: formatCount(account.followingCount), hint: "真实统计" },
      { id: "videos", label: "视频", value: formatCount(account.videoCount), hint: "真实统计" }
    ],
    sections: [
      { id: "profile", title: "账号概览", fields: [
          { id: "platform", label: "平台", value: platformLabel(account.platform) },
          { id: "status", label: "状态", value: getStatusLabel(account.status) },
          { id: "username", label: "用户名", value: account.username || "未提供用户名" },
          { id: "auth", label: "授权到期", value: account.authExpiresAt ? formatDateTime(account.authExpiresAt) : "未返回到期时间", mono: true },
          { id: "created", label: "创建时间", value: formatDateTime(account.createdAt), mono: true },
          { id: "updated", label: "更新时间", value: formatDateTime(account.updatedAt), mono: true }
      ]},
      { id: "tags", title: "标签与备注", emptyLabel: "Runtime 还没有为该账号返回标签或备注。", fields: [
          { id: "tags", label: "标签", value: parseTags(account.tags).join(" / ") || "未返回标签" },
          { id: "notes", label: "备注", value: account.notes || "未返回备注", multiline: true }
      ]},
      { id: "binding", title: "分组与绑定", emptyLabel: "Runtime 只返回账号对象与分组目录，没有返回账号绑定字段。" }
    ],
    actions: [
      { id: "refresh", label: "刷新统计", icon: "refresh", tone: "brand" },
      { id: "clear", label: "清空选择", icon: "close", tone: "neutral" }
    ]
  });
}

function parseTags(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];
  } catch { return []; }
}

function formatCount(count: number | null) {
  if (count === null) return "未返回";
  if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
  if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
  return String(count);
}

function statusTone(status: string): "success" | "neutral" | "danger" | "warning" {
  if (status === "active") return "success";
  if (status === "inactive") return "neutral";
  if (status === "suspended") return "danger";
  if (status === "expired") return "warning";
  return "neutral";
}

function getStatusLabel(status: string) {
  switch (status) {
    case "active": return "已激活";
    case "inactive": return "未登录";
    case "suspended": return "已封禁";
    case "expired": return "凭证过期";
    default: return status || "未知";
  }
}

function platformLabel(platform: string) {
  switch (platform) {
    case "tiktok": return "TikTok";
    case "youtube": return "YouTube";
    case "instagram": return "Instagram";
    default: return platform || "未知平台";
  }
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false, hourCycle: "h23"
  }).formatToParts(date);
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")} ${part("hour")}:${part("minute")}:${part("second")}`;
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

.page-header__actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
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

.dashboard-alert[data-tone="danger"] {
  border-color: rgba(255, 90, 99, 0.20);
  background: rgba(255, 90, 99, 0.08);
  color: var(--color-danger);
}

.dashboard-alert[data-tone="warning"] {
  border-color: rgba(245, 183, 64, 0.20);
  background: rgba(245, 183, 64, 0.08);
  color: var(--color-warning);
}

.dashboard-alert[data-tone="brand"] {
  border-color: rgba(0, 188, 212, 0.20);
  background: rgba(0, 188, 212, 0.08);
  color: var(--color-brand-primary);
}

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

.sc-hint {
  font: var(--font-caption);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
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

.flex-1 {
  flex: 1;
}

.rail-card__header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.rail-card__header h3 {
  margin: 0;
  font: var(--font-title-md);
  color: var(--color-text-primary);
}

.rail-card__body {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.rail-card__body.no-padding {
  padding: 0;
}

.scroll-area {
  overflow-y: auto;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  padding: 0 10px;
  height: 36px;
}

.search-box input {
  background: transparent;
  border: none;
  color: var(--color-text-primary);
  outline: none;
  flex: 1;
  font: var(--font-body-md);
}

.group-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.group-tabs button {
  background: transparent;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: 13px;
  padding: 6px 12px;
  transition: all var(--motion-fast) var(--ease-standard);
}

.group-tabs button.active {
  background: color-mix(in srgb, var(--color-brand-primary) 12%, transparent);
  border-color: color-mix(in srgb, var(--color-brand-primary) 35%, var(--color-border-default));
  color: var(--color-brand-primary);
}

.rail-card__hint {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
}

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

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin { 100% { transform: rotate(360deg); } }

.account-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.account-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: var(--space-4);
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--color-border-subtle);
  cursor: pointer;
  text-align: left;
  transition: background-color var(--motion-fast) var(--ease-standard);
}

.account-card:hover {
  background: var(--color-bg-hover);
}

.account-card:active {
  transform: scale(0.98);
  transition-duration: var(--motion-instant);
}

.account-list-transition-move,
.account-list-transition-enter-active,
.account-list-transition-leave-active {
  transition: all var(--motion-default) var(--ease-spring);
}
.account-list-transition-enter-from,
.account-list-transition-leave-to {
  opacity: 0;
  transform: translateX(-16px);
}
.account-list-transition-leave-active {
  position: absolute;
  width: 100%;
}

.account-card.is-selected {
  background: color-mix(in srgb, var(--color-brand-primary) 8%, var(--color-bg-surface));
  border-left: 3px solid var(--color-brand-primary);
  padding-left: calc(var(--space-4) - 3px);
}

.ac-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ac-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--color-brand-primary) 14%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: var(--color-brand-primary);
  font-size: 18px;
  font-weight: bold;
}

.ac-avatar[data-platform="youtube"] { background: color-mix(in srgb, var(--color-danger) 14%, transparent); color: var(--color-danger); }
.ac-avatar[data-platform="instagram"] { background: color-mix(in srgb, var(--color-warning) 14%, transparent); color: var(--color-warning); }
.ac-avatar img { width: 100%; height: 100%; object-fit: cover; }

.ac-meta {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.ac-meta strong {
  font: var(--font-title-sm);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ac-meta span {
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.ac-body, .ac-stats, .ac-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.ac-stats strong {
  color: var(--color-text-primary);
  font-size: 14px;
}

.ac-tag {
  color: var(--color-text-tertiary);
}

.workspace-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
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

.detail-card__body {
  padding: var(--space-6);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.empty-wrapper {
  flex: 1;
  justify-content: center;
}

.detail-metadata {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
  margin: 0;
}

.detail-metadata div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-metadata dt {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.detail-metadata dd {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-primary);
}

.detail-block {
  border-top: 1px solid var(--color-border-subtle);
  padding-top: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.detail-block__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.detail-block__header span {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}

.metric-card {
  padding: var(--space-4);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-card span {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.metric-card strong {
  font: var(--font-title-lg);
  color: var(--color-text-primary);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  font: var(--font-caption);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  padding: 2px 8px;
  border-radius: 999px;
  color: var(--color-text-secondary);
}

.detail-empty, .detail-note {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
  line-height: 1.6;
}

.detail-block--blocked {
  background: color-mix(in srgb, var(--color-warning) 6%, transparent);
  border: 1px dashed color-mix(in srgb, var(--color-warning) 28%, var(--color-border-default));
  border-radius: var(--radius-md);
  padding: var(--space-4);
}

.detail-actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

.soft-card {
  background: color-mix(in srgb, var(--color-brand-primary) 4%, var(--color-bg-surface));
}

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

.drawer-panel__header h2 {
  margin: 0;
  font: var(--font-title-lg);
  color: var(--color-text-primary);
}

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

.drawer-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

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

.drawer-form__hint {
  margin: 0;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  line-height: 1.6;
}

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
  .summary-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>