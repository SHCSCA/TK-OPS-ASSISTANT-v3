<template>
  <section class="account-management">
    <header class="account-management__hero">
      <div class="account-management__hero-copy">
        <p class="account-management__eyebrow">账号管理 · 真实对象</p>
        <h1>账号管理</h1>
        <p>
          只展示 Runtime 返回的账号对象、状态、分组目录和真实统计，不伪造账号绑定或健康分数。
        </p>
      </div>

      <div class="account-management__hero-actions">
        <button class="account-management__button" type="button" @click="handleReload" :disabled="store.status === 'loading'">
          <span class="material-symbols-outlined">refresh</span>
          重新拉取
        </button>
        <button class="account-management__button account-management__button--brand" type="button" @click="store.showAddModal = true" :disabled="store.status === 'loading'">
          <span class="material-symbols-outlined">person_add</span>
          添加账号
        </button>
      </div>
    </header>

    <p v-if="store.error" class="account-management__banner account-management__banner--error">
      {{ store.error }}
    </p>
    <p v-else-if="store.status === 'loading'" class="account-management__banner">
      正在读取真实账号对象与分组目录，请稍候。
    </p>
    <p v-else-if="store.groups.length === 0" class="account-management__banner account-management__banner--blocked">
      Runtime 尚未返回账号分组目录。页面只展示真实账号对象，不会伪造绑定关系。
    </p>

    <section class="account-management__summary">
      <article class="summary-card">
        <span>账号总数</span>
        <strong>{{ store.accounts.length }}</strong>
        <p>Runtime 返回的真实账号对象</p>
      </article>
      <article class="summary-card">
        <span>当前筛选</span>
        <strong>{{ visibleAccounts.length }}</strong>
        <p>{{ currentGroupLabel }}</p>
      </article>
      <article class="summary-card">
        <span>当前选中</span>
        <strong>{{ selectedAccount ? selectedAccount.name : "未选中" }}</strong>
        <p>{{ selectedAccount ? selectedAccount.platform : "请在左侧选中一个账号" }}</p>
      </article>
      <article class="summary-card">
        <span>分组目录</span>
        <strong>{{ store.groups.length }}</strong>
        <p>仅用于真实筛选，不写入假绑定</p>
      </article>
    </section>

    <main class="account-management__body">
      <aside class="account-management__rail">
        <section class="rail-card">
          <div class="rail-card__header">
            <div>
              <p class="rail-card__eyebrow">搜索与分组</p>
              <h2>筛选真实账号</h2>
            </div>
          </div>

          <label class="search-box">
            <span class="material-symbols-outlined">search</span>
            <input v-model="searchQuery" type="search" placeholder="搜索账号名称或用户名" />
          </label>

          <div class="group-tabs" aria-label="账号分组筛选">
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

          <p class="rail-card__hint">
            {{ groupsHint }}
          </p>
        </section>

        <section class="rail-card rail-card--list">
          <div class="rail-card__header">
            <div>
              <p class="rail-card__eyebrow">账号列表</p>
              <h2>{{ listTitle }}</h2>
            </div>
            <span class="rail-card__badge">{{ visibleAccounts.length }}</span>
          </div>

          <div v-if="store.status === 'loading'" class="state-card">
            <span class="material-symbols-outlined state-card__spinner">sync</span>
            <strong>正在加载账号</strong>
            <p>同步 Runtime 中的账号对象和分组目录。</p>
          </div>

          <div v-else-if="visibleAccounts.length === 0" class="state-card state-card--empty">
            <span class="material-symbols-outlined">person_off</span>
            <strong>没有符合条件的账号</strong>
            <p>可以切换分组、清空搜索，或者添加一个真实账号对象。</p>
          </div>

          <div v-else class="account-list">
            <button
              v-for="account in visibleAccounts"
              :key="account.id"
              :data-testid="`account-card-${account.id}`"
              class="account-card"
              :class="{ 'account-card--selected': selectedAccountId === account.id }"
              type="button"
              @click="selectAccount(account)"
            >
              <div class="account-card__head">
                <div class="account-card__avatar" :data-platform="account.platform">
                  <img v-if="account.avatarUrl" :src="account.avatarUrl" :alt="account.name" />
                  <span v-else>{{ account.name.charAt(0).toUpperCase() }}</span>
                </div>
                <div class="account-card__meta">
                  <strong :title="account.name">{{ account.name }}</strong>
                  <span>@{{ account.username || "未提供用户名" }}</span>
                </div>
                <span class="account-card__status" :class="account.status">{{ getStatusLabel(account.status) }}</span>
              </div>

              <div class="account-card__body">
                <span>{{ platformLabel(account.platform) }}</span>
                <span>{{ formatDateTime(account.updatedAt) }}</span>
              </div>

              <div class="account-card__stats">
                <span><strong>{{ formatCount(account.followerCount) }}</strong> 粉丝</span>
                <span><strong>{{ formatCount(account.videoCount) }}</strong> 视频</span>
              </div>

              <div class="account-card__footer">
                <span class="account-card__tag">
                  {{ account.authExpiresAt ? `到期 ${formatDateTime(account.authExpiresAt)}` : "未返回授权到期时间" }}
                </span>
                <button
                  class="account-card__delete"
                  type="button"
                  :disabled="store.status === 'loading'"
                  @click.stop="handleDeleteAccount(account)"
                >
                  删除
                </button>
              </div>
            </button>
          </div>
        </section>
      </aside>

      <section class="account-management__detail">
        <article class="detail-card">
          <div class="detail-card__header">
            <div>
              <p class="detail-card__eyebrow">账号详情</p>
              <h2>{{ selectedAccount ? selectedAccount.name : "未选中账号" }}</h2>
              <p class="detail-card__summary">
                {{ selectedAccount ? `账号对象来自 ${platformLabel(selectedAccount.platform)}，选中后会同步打开右侧详情面板。` : "在左侧选择一个账号，右侧会显示真实状态、统计和授权到期时间。" }}
              </p>
            </div>
            <div class="detail-card__actions" v-if="selectedAccount">
              <button class="account-management__button" type="button" @click="handleRefreshSelected" :disabled="store.status === 'loading'">
                <span class="material-symbols-outlined">refresh</span>
                刷新统计
              </button>
            </div>
          </div>

          <template v-if="selectedAccount">
            <dl class="detail-metadata">
              <div>
                <dt>平台</dt>
                <dd>{{ platformLabel(selectedAccount.platform) }}</dd>
              </div>
              <div>
                <dt>状态</dt>
                <dd>{{ getStatusLabel(selectedAccount.status) }}</dd>
              </div>
              <div>
                <dt>用户名</dt>
                <dd>{{ selectedAccount.username || "未提供用户名" }}</dd>
              </div>
              <div>
                <dt>授权到期</dt>
                <dd>{{ selectedAccount.authExpiresAt ? formatDateTime(selectedAccount.authExpiresAt) : "未返回到期时间" }}</dd>
              </div>
              <div>
                <dt>创建时间</dt>
                <dd>{{ formatDateTime(selectedAccount.createdAt) }}</dd>
              </div>
              <div>
                <dt>更新时间</dt>
                <dd>{{ formatDateTime(selectedAccount.updatedAt) }}</dd>
              </div>
            </dl>

            <section class="detail-block">
              <div class="detail-block__header">
                <span>真实统计</span>
              </div>
              <div class="metric-grid">
                <article class="metric-card">
                  <span>粉丝</span>
                  <strong>{{ formatCount(selectedAccount.followerCount) }}</strong>
                </article>
                <article class="metric-card">
                  <span>关注</span>
                  <strong>{{ formatCount(selectedAccount.followingCount) }}</strong>
                </article>
                <article class="metric-card">
                  <span>视频</span>
                  <strong>{{ formatCount(selectedAccount.videoCount) }}</strong>
                </article>
              </div>
            </section>

            <section class="detail-block">
              <div class="detail-block__header">
                <span>标签与备注</span>
              </div>
              <div v-if="selectedTags.length" class="tag-list">
                <span v-for="tag in selectedTags" :key="tag">{{ tag }}</span>
              </div>
              <p v-else class="detail-empty">Runtime 还没有为该账号返回标签。</p>
              <p class="detail-note">
                {{ selectedAccount.notes || "Runtime 没有返回备注内容。" }}
              </p>
            </section>

            <section class="detail-block detail-block--blocked">
              <div class="detail-block__header">
                <span>分组与绑定</span>
                <strong>blocked</strong>
              </div>
              <p class="detail-empty">
                当前 Runtime 只返回账号对象和分组目录，没有返回 per-account 的绑定字段。页面只做真实筛选，不伪造账号绑定。
              </p>
            </section>

            <div class="detail-actions">
              <button class="account-management__button account-management__button--brand" type="button" @click="openSelectedAccountDetail">
                打开右侧详情
              </button>
              <button class="account-management__button" type="button" @click="clearSelection">
                清空选择
              </button>
            </div>
          </template>

          <template v-else>
            <div class="detail-empty-state">
              <span class="material-symbols-outlined">person_search</span>
              <strong>未选中账号</strong>
              <p>在左侧选择一个真实账号对象，右侧会展示它的统计、授权到期和备注信息。</p>
            </div>
          </template>
        </article>

        <article class="detail-card detail-card--soft">
          <div class="detail-block__header">
            <span>真实边界</span>
          </div>
          <p class="detail-note">
            账号页只显示 Runtime 真实返回的账号对象，不显示健康分、在线率或人工拼接的绑定结果。
          </p>
        </article>
      </section>
    </main>

    <transition name="drawer">
      <div v-if="store.showAddModal" class="drawer-overlay" @click="store.showAddModal = false">
        <aside class="drawer-panel" @click.stop>
          <div class="drawer-panel__header">
            <div>
              <p class="drawer-panel__eyebrow">添加账号</p>
              <h2>创建真实账号对象</h2>
            </div>
            <button class="drawer-panel__close" type="button" @click="store.showAddModal = false">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <form class="drawer-form" @submit.prevent="handleAddAccount">
            <label class="drawer-form__field">
              <span>账号显示名称</span>
              <input v-model="addForm.name" type="text" placeholder="例如：我的主账号" required />
            </label>

            <label class="drawer-form__field">
              <span>目标平台</span>
              <select v-model="addForm.platform">
                <option value="tiktok">TikTok</option>
                <option value="youtube">YouTube</option>
                <option value="instagram">Instagram</option>
              </select>
            </label>

            <label class="drawer-form__field">
              <span>用户名</span>
              <input v-model="addForm.username" type="text" placeholder="username" />
            </label>

            <label class="drawer-form__field">
              <span>初始状态</span>
              <select v-model="addForm.status">
                <option value="active">已激活</option>
                <option value="inactive">未登录</option>
                <option value="expired">凭证过期</option>
                <option value="suspended">已封禁</option>
              </select>
            </label>

            <p class="drawer-form__hint">
              这里创建的只是账号对象，不包含任何假绑定；后续分组和授权状态仍以 Runtime 返回为准。
            </p>

            <div class="drawer-form__actions">
              <button class="account-management__button" type="button" @click="store.showAddModal = false">取消</button>
              <button class="account-management__button account-management__button--brand" type="submit" :disabled="!addForm.name || store.status === 'loading'">
                保存账号
              </button>
            </div>
          </form>
        </aside>
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import { useAccountManagementStore } from "@/stores/account-management";
import type { AccountDto } from "@/types/runtime";

const store = useAccountManagementStore();
const shellUiStore = useShellUiStore();
const searchQuery = ref("");
const selectedAccountId = ref<string | null>(null);

const addForm = reactive({
  name: "",
  platform: "tiktok",
  username: "",
  status: "active"
});

const visibleAccounts = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) {
    return store.accounts;
  }

  return store.accounts.filter((account) => {
    const username = account.username?.toLowerCase() ?? "";
    return account.name.toLowerCase().includes(query) || username.includes(query);
  });
});

const selectedAccount = computed(
  () => store.accounts.find((account) => account.id === selectedAccountId.value) ?? null
);
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

watch(
  selectedAccount,
  (account) => {
    if (!account) {
      shellUiStore.clearDetailContext("binding");
      shellUiStore.closeDetailPanel();
      return;
    }

    shellUiStore.openDetailWithContext(buildAccountDetailContext(account));
  },
  { immediate: true }
);

onMounted(() => {
  void store.load();
});

onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("binding");
  shellUiStore.closeDetailPanel();
});

function handleReload() {
  void store.load();
}

function handleSelectGroup(groupId: string | null) {
  selectedAccountId.value = null;
  shellUiStore.clearDetailContext("binding");
  shellUiStore.closeDetailPanel();
  store.setSelectedGroup(groupId);
}

function selectAccount(account: AccountDto) {
  selectedAccountId.value = account.id;
}

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
  await store.addAccount({
    name: addForm.name.trim(),
    platform: addForm.platform,
    username: addForm.username.trim(),
    status: addForm.status
  });
  addForm.name = "";
  addForm.username = "";
  addForm.platform = "tiktok";
  addForm.status = "active";
  selectedAccountId.value = null;
}

async function handleDeleteAccount(account: AccountDto) {
  if (!window.confirm(`确认删除账号“${account.name}”吗？`)) return;
  await store.removeAccount(account.id);
  if (selectedAccountId.value === account.id) {
    clearSelection();
  }
}

async function handleRefreshSelected() {
  if (!selectedAccount.value) return;
  await store.refreshStats(selectedAccount.value.id);
}

function buildAccountDetailContext(account: AccountDto) {
  return createRouteDetailContext("binding", {
    icon: "account_circle",
    eyebrow: "账号详情",
    title: account.name,
    description: "只展示 Runtime 真实返回的账号对象和状态，不伪造绑定关系。",
    badge: {
      label: getStatusLabel(account.status),
      tone: account.status === "active" ? "success" : account.status === "expired" ? "warning" : "neutral"
    },
    metrics: [
      { id: "followers", label: "粉丝", value: formatCount(account.followerCount), hint: "真实统计" },
      { id: "following", label: "关注", value: formatCount(account.followingCount), hint: "真实统计" },
      { id: "videos", label: "视频", value: formatCount(account.videoCount), hint: "真实统计" }
    ],
    sections: [
      {
        id: "profile",
        title: "账号概览",
        fields: [
          { id: "platform", label: "平台", value: platformLabel(account.platform) },
          { id: "status", label: "状态", value: getStatusLabel(account.status) },
          { id: "username", label: "用户名", value: account.username || "未提供用户名" },
          { id: "auth", label: "授权到期", value: account.authExpiresAt ? formatDateTime(account.authExpiresAt) : "未返回到期时间", mono: true },
          { id: "created", label: "创建时间", value: formatDateTime(account.createdAt), mono: true },
          { id: "updated", label: "更新时间", value: formatDateTime(account.updatedAt), mono: true }
        ]
      },
      {
        id: "tags",
        title: "标签与备注",
        emptyLabel: "Runtime 还没有为该账号返回标签或备注。",
        fields: [
          { id: "tags", label: "标签", value: parseTags(account.tags).join(" / ") || "未返回标签" },
          { id: "notes", label: "备注", value: account.notes || "未返回备注", multiline: true }
        ]
      },
      {
        id: "binding",
        title: "分组与绑定",
        emptyLabel: "Runtime 只返回账号对象与分组目录，没有返回账号绑定字段。"
      }
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
  } catch {
    return [];
  }
}

function formatCount(count: number | null) {
  if (count === null) return "未返回";
  if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
  if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
  return String(count);
}

function getStatusLabel(status: string) {
  switch (status) {
    case "active":
      return "已激活";
    case "inactive":
      return "未登录";
    case "suspended":
      return "已封禁";
    case "expired":
      return "凭证过期";
    default:
      return status || "未知";
  }
}

function platformLabel(platform: string) {
  switch (platform) {
    case "tiktok":
      return "TikTok";
    case "youtube":
      return "YouTube";
    case "instagram":
      return "Instagram";
    default:
      return platform || "未知平台";
  }
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    hourCycle: "h23"
  }).formatToParts(date);

  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")} ${part("hour")}:${part("minute")}:${part("second")}`;
}
</script>

<style scoped>
.account-management {
  display: grid;
  gap: 16px;
  min-height: 100%;
  padding: 18px 24px 24px;
}

.account-management__hero {
  align-items: start;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.account-management__hero-copy {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.account-management__eyebrow {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0;
  text-transform: uppercase;
}

.account-management__hero-copy h1 {
  font-size: 28px;
  line-height: 1.15;
  margin: 0;
}

.account-management__hero-copy p {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
  line-height: 1.7;
  margin: 0;
  max-width: 780px;
}

.account-management__hero-actions,
.detail-actions,
.drawer-form__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.account-management__button {
  align-items: center;
  background: transparent;
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  color: var(--color-text-primary, var(--text-primary));
  cursor: pointer;
  display: inline-flex;
  gap: 6px;
  height: 36px;
  justify-content: center;
  padding: 0 14px;
}

.account-management__button--brand {
  background: var(--color-brand-primary, var(--brand-primary));
  border-color: var(--color-brand-primary, var(--brand-primary));
  color: var(--color-text-on-brand, #fff);
}

.account-management__button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.account-management__banner {
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-md);
  background: var(--color-bg-surface, var(--surface-secondary));
  color: var(--color-text-secondary, var(--text-secondary));
  margin: 0;
  padding: 10px 12px;
}

.account-management__banner--error {
  border-color: color-mix(in srgb, var(--color-danger, var(--status-error)) 32%, var(--color-border-default, var(--border-default)));
  color: var(--color-danger, var(--status-error));
}

.account-management__banner--blocked {
  border-color: color-mix(in srgb, var(--color-warning, var(--status-warning)) 30%, var(--color-border-default, var(--border-default)));
  color: var(--color-warning, var(--status-warning));
}

.account-management__summary {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.summary-card {
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-md);
  background: var(--color-bg-surface, var(--surface-secondary));
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 14px;
}

.summary-card span {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.summary-card strong {
  font-size: 15px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-card p {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
  line-height: 1.5;
  margin: 0;
}

.account-management__body {
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
  min-height: 0;
}

.account-management__rail,
.account-management__detail {
  display: grid;
  gap: 12px;
  min-height: 0;
}

.rail-card,
.detail-card {
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-md);
  background: var(--color-bg-surface, var(--surface-secondary));
  display: grid;
  gap: 14px;
  padding: 16px;
}

.detail-card--soft {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 4%, var(--color-bg-surface, var(--surface-secondary)));
}

.rail-card--list {
  gap: 12px;
  min-height: 0;
}

.rail-card__header,
.detail-card__header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.rail-card__eyebrow,
.detail-card__eyebrow {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0 0 4px;
  text-transform: uppercase;
}

.rail-card__header h2,
.detail-card__header h2 {
  margin: 0;
}

.rail-card__badge {
  align-self: start;
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 14%, transparent);
  border-radius: 999px;
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
}

.search-box {
  align-items: center;
  background: var(--color-bg-canvas, var(--bg-card));
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  display: flex;
  gap: 8px;
  height: 38px;
  padding: 0 10px;
}

.search-box .material-symbols-outlined {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 18px;
}

.search-box input {
  background: transparent;
  border: none;
  color: var(--color-text-primary, var(--text-primary));
  font-size: 13px;
  min-width: 0;
  outline: none;
  width: 100%;
}

.group-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.group-tabs button {
  background: transparent;
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary, var(--text-secondary));
  cursor: pointer;
  font-size: 13px;
  height: 32px;
  padding: 0 12px;
}

.group-tabs button.active {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 12%, transparent);
  border-color: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 35%, var(--color-border-default, var(--border-default)));
  color: var(--color-brand-primary, var(--brand-primary));
}

.rail-card__hint {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
  line-height: 1.6;
  margin: 0;
}

.account-list {
  display: grid;
  gap: 10px;
  max-height: min(68vh, 760px);
  overflow: auto;
  padding-right: 2px;
}

.account-card {
  background: transparent;
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-md);
  color: inherit;
  cursor: pointer;
  display: grid;
  gap: 10px;
  padding: 12px;
  text-align: left;
}

.account-card--selected {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 8%, var(--color-bg-surface, var(--surface-secondary)));
  border-color: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 55%, var(--color-border-default, var(--border-default)));
}

.account-card__head {
  display: grid;
  gap: 10px;
  grid-template-columns: 48px minmax(0, 1fr) auto;
  align-items: center;
}

.account-card__avatar {
  align-items: center;
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 14%, transparent);
  border-radius: 50%;
  display: flex;
  height: 48px;
  justify-content: center;
  overflow: hidden;
  width: 48px;
}

.account-card__avatar[data-platform="youtube"] {
  background: color-mix(in srgb, var(--color-danger, var(--status-error)) 14%, transparent);
}

.account-card__avatar[data-platform="instagram"] {
  background: color-mix(in srgb, var(--color-warning, var(--status-warning)) 14%, transparent);
}

.account-card__avatar img {
  height: 100%;
  object-fit: cover;
  width: 100%;
}

.account-card__avatar span {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 20px;
  font-weight: 800;
}

.account-card__meta {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.account-card__meta strong {
  font-size: 15px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-card__meta span,
.account-card__body,
.account-card__stats,
.account-card__footer {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
}

.account-card__status {
  align-self: start;
  border-radius: 999px;
  padding: 2px 8px;
  white-space: nowrap;
}

.account-card__status.active {
  background: color-mix(in srgb, var(--color-success, var(--status-success)) 12%, transparent);
  color: var(--color-success, var(--status-success));
}

.account-card__status.inactive {
  background: color-mix(in srgb, var(--color-text-tertiary, var(--text-tertiary)) 12%, transparent);
  color: var(--color-text-tertiary, var(--text-tertiary));
}

.account-card__status.suspended {
  background: color-mix(in srgb, var(--color-danger, var(--status-error)) 12%, transparent);
  color: var(--color-danger, var(--status-error));
}

.account-card__status.expired {
  background: color-mix(in srgb, var(--color-warning, var(--status-warning)) 12%, transparent);
  color: var(--color-warning, var(--status-warning));
}

.account-card__body,
.account-card__stats,
.account-card__footer {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.account-card__body span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-card__stats strong {
  color: var(--color-text-primary, var(--text-primary));
  font-size: 15px;
}

.account-card__tag {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-card__delete {
  background: transparent;
  border: 1px solid color-mix(in srgb, var(--color-danger, var(--status-error)) 30%, var(--color-border-default, var(--border-default)));
  border-radius: var(--radius-sm);
  color: var(--color-danger, var(--status-error));
  cursor: pointer;
  height: 28px;
  padding: 0 10px;
}

.account-card__delete:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.detail-card__summary {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
  line-height: 1.7;
  margin: 6px 0 0;
}

.detail-metadata {
  display: grid;
  gap: 12px;
  margin: 0;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.detail-metadata div {
  display: grid;
  gap: 4px;
}

.detail-metadata dt {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
}

.detail-metadata dd {
  font-size: 13px;
  margin: 0;
  overflow-wrap: anywhere;
}

.detail-block {
  border-top: 1px solid var(--color-border-default, var(--border-default));
  display: grid;
  gap: 10px;
  padding-top: 14px;
}

.detail-block--blocked {
  background: color-mix(in srgb, var(--color-warning, var(--status-warning)) 6%, transparent);
  border: 1px dashed color-mix(in srgb, var(--color-warning, var(--status-warning)) 28%, var(--color-border-default, var(--border-default)));
  border-radius: var(--radius-md);
  padding: 14px;
}

.detail-block__header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.detail-block__header span {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.detail-block__header strong {
  background: color-mix(in srgb, var(--color-danger, var(--status-error)) 12%, transparent);
  border-radius: 999px;
  color: var(--color-danger, var(--status-error));
  font-size: 12px;
  padding: 2px 8px;
}

.metric-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.metric-card {
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  background: var(--color-bg-canvas, var(--surface-tertiary));
  display: grid;
  gap: 6px;
  padding: 12px;
}

.metric-card span {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
}

.metric-card strong {
  font-size: 18px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-list span {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 22%, transparent);
  border-radius: 999px;
  color: var(--color-text-primary, var(--text-primary));
  font-size: 11px;
  padding: 2px 8px;
}

.detail-empty {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
  line-height: 1.7;
  margin: 0;
}

.detail-note {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
  line-height: 1.7;
  margin: 0;
}

.detail-empty-state {
  align-items: center;
  display: grid;
  gap: 10px;
  justify-items: center;
  min-height: 320px;
  padding: 24px 12px;
  text-align: center;
}

.detail-empty-state .material-symbols-outlined {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 42px;
}

.detail-empty-state strong {
  font-size: 15px;
}

.drawer-overlay {
  background: color-mix(in srgb, var(--color-bg-overlay, rgba(0, 0, 0, 0.55)) 100%, transparent);
  inset: 0;
  position: fixed;
  z-index: 1300;
}

.drawer-panel {
  background: var(--color-bg-surface, var(--surface-secondary));
  bottom: 0;
  box-shadow: -12px 0 32px rgba(0, 0, 0, 0.22);
  display: grid;
  gap: 16px;
  max-width: 420px;
  overflow: auto;
  padding: 18px;
  position: absolute;
  right: 0;
  top: 0;
  width: min(420px, 100vw);
}

.drawer-panel__header {
  align-items: start;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.drawer-panel__eyebrow {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0 0 4px;
  text-transform: uppercase;
}

.drawer-panel__header h2 {
  margin: 0;
}

.drawer-panel__close {
  align-items: center;
  background: transparent;
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary, var(--text-secondary));
  cursor: pointer;
  display: inline-flex;
  height: 32px;
  justify-content: center;
  width: 32px;
}

.drawer-form {
  display: grid;
  gap: 14px;
}

.drawer-form__field {
  display: grid;
  gap: 6px;
}

.drawer-form__field span {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
}

.drawer-form__field input,
.drawer-form__field select {
  background: var(--color-bg-canvas, var(--surface-tertiary));
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  color: var(--color-text-primary, var(--text-primary));
  font: inherit;
  min-height: 38px;
  padding: 0 12px;
}

.drawer-form__hint {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
  line-height: 1.7;
  margin: 0;
}

.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 160ms ease;
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

@media (max-width: 1280px) {
  .account-management__summary,
  .account-management__body {
    grid-template-columns: 1fr;
  }

  .account-management__hero {
    flex-direction: column;
  }

  .account-management__hero-actions {
    justify-content: flex-start;
  }

  .metric-grid,
  .detail-metadata {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .account-management {
    padding-left: 16px;
    padding-right: 16px;
  }
}
</style>
