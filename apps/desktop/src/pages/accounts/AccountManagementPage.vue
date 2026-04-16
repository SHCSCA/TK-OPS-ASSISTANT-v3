<template>
  <div class="account-management">
    <!-- 页头 -->
    <header class="account-header">
      <div class="header-left">
        <button class="btn-primary" @click="store.showAddModal = true">
          <span class="material-symbols-outlined">person_add</span>
          添加账号
        </button>
        <div class="group-tabs">
          <button
            :class="{ active: store.selectedGroupId === null }"
            @click="store.setSelectedGroup(null)">
            全部账号
          </button>
          <button v-for="group in store.groups" :key="group.id"
            :class="{ active: store.selectedGroupId === group.id }"
            @click="store.setSelectedGroup(group.id)">
            {{ group.name }}
          </button>
        </div>
      </div>
      <div class="header-right">
        <div class="search-box">
          <span class="material-symbols-outlined">search</span>
          <input type="text" v-model="searchQuery" placeholder="搜索账号..." />
        </div>
      </div>
    </header>

    <main class="account-content">
      <div v-if="store.status === 'loading'" class="loading-state">
        <span class="material-symbols-outlined rotating">sync</span>
        <span>加载账号中...</span>
      </div>
      <div v-else-if="filteredAccounts.length === 0" class="empty-state">
        <span class="material-symbols-outlined">account_circle</span>
        <span>暂无账号</span>
      </div>
      <div v-else class="account-grid">
        <div v-for="account in filteredAccounts" :key="account.id"
          class="account-card"
          @click="selectedAccountId = account.id">
          <div class="card-header">
            <div class="avatar-container" :class="{ 'pulse-active': account.status === 'active' }">
              <img v-if="account.avatarUrl" :src="account.avatarUrl" :alt="account.name" />
              <div v-else class="avatar-placeholder">
                {{ account.name.charAt(0).toUpperCase() }}
              </div>
            </div>
            <div class="account-main-info">
              <div class="account-name">{{ account.name }}</div>
              <div class="account-username">@{{ account.username || 'unknown' }}</div>
            </div>
            <button class="delete-btn" @click.stop="store.removeAccount(account.id)">
               <span class="material-symbols-outlined">delete</span>
            </button>
          </div>
          <div class="card-body">
            <div class="platform-row">
              <span class="platform-label">{{ account.platform.toUpperCase() }}</span>
              <span class="last-sync">同步于: {{ formatDate(account.updatedAt) }}</span>
            </div>
            <div class="stats-row">
              <div class="stat-item">
                <span class="stat-value">{{ formatCount(account.followerCount) }}</span>
                <span class="stat-label">粉丝</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">{{ formatCount(account.videoCount) }}</span>
                <span class="stat-label">视频</span>
              </div>
            </div>
          </div>
          <div class="card-footer">
            <span class="status-badge" :class="account.status">
              <span class="status-dot"></span>
              {{ getStatusLabel(account.status) }}
            </span>
            <button class="refresh-btn" @click.stop="handleRefresh(account.id)" title="刷新统计">
              <span class="material-symbols-outlined">refresh</span>
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- 添加账号抽屉 -->
    <transition name="drawer">
      <div v-if="store.showAddModal" class="drawer-overlay" @click="store.showAddModal = false">
        <aside class="add-account-drawer" @click.stop>
          <div class="drawer-header">
            <h3>添加新账号</h3>
            <button @click="store.showAddModal = false" class="close-btn">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <form @submit.prevent="handleAddAccount" class="drawer-form">
            <div class="form-item">
              <label>账号显示名称</label>
              <input v-model="addForm.name" type="text" placeholder="例如：我的主账号" required />
            </div>
            <div class="form-item">
              <label>目标平台</label>
              <select v-model="addForm.platform">
                <option value="tiktok">TikTok</option>
                <option value="youtube">YouTube</option>
                <option value="instagram">Instagram</option>
              </select>
            </div>
            <div class="form-item">
              <label>用户名 (Handle)</label>
              <input v-model="addForm.username" type="text" placeholder="username" />
            </div>
            <div class="form-item">
              <label>初始状态</label>
              <select v-model="addForm.status">
                <option value="active">Active (正常)</option>
                <option value="inactive">Inactive (离线)</option>
              </select>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn-save">保存账号</button>
              <button type="button" class="btn-cancel" @click="store.showAddModal = false">取消</button>
            </div>
          </form>
        </aside>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import { useAccountManagementStore } from '@/stores/account-management';

const store = useAccountManagementStore();
const searchQuery = ref('');
const selectedAccountId = ref<string | null>(null);

const addForm = reactive({
  name: '',
  platform: 'tiktok',
  username: '',
  status: 'active'
});

const filteredAccounts = computed(() => {
  let list = store.accounts;
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase();
    list = list.filter(a =>
      a.name.toLowerCase().includes(q) ||
      (a.username && a.username.toLowerCase().includes(q))
    );
  }
  return list;
});

onMounted(() => {
  store.load();
});

function handleAddAccount() {
  store.addAccount({
    name: addForm.name,
    platform: addForm.platform,
    username: addForm.username,
    status: addForm.status
  });
  // Reset form
  addForm.name = '';
  addForm.username = '';
}

function handleRefresh(id: string) {
  store.refreshStats(id);
  alert('同步请求已发送 (pending_provider)');
}

function formatCount(count: number | null) {
  if (count === null) return '--';
  if (count >= 1000000) return (count / 1000000).toFixed(1) + 'M';
  if (count >= 1000) return (count / 1000).toFixed(1) + 'K';
  return count.toString();
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString();
}

function getStatusLabel(status: string) {
  switch (status) {
    case 'active': return '已激活';
    case 'inactive': return '未登录';
    case 'suspended': return '已封禁';
    case 'expired': return 'Token过期';
    default: return status;
  }
}
</script>

<style scoped>
.account-management {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  overflow: hidden;
}

/* ── 页头 ── */
.account-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-lg);
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.header-left {
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
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.group-tabs {
  display: flex;
  gap: var(--spacing-sm);
}

.group-tabs button {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 4px 12px;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.group-tabs button.active {
  color: var(--brand-primary);
  background: rgba(0, 242, 234, 0.1);
  font-weight: 600;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 0 10px;
  width: 200px;
  height: 30px;
}

.search-box input {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 12px;
  width: 100%;
  outline: none;
}

/* ── 主内容 ── */
.account-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
}

.account-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-lg);
}

.account-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  padding: var(--spacing-md);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.account-card:hover {
  border-color: var(--border-default);
  background: var(--bg-hover);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
}

.avatar-container {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #333;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  flex-shrink: 0;
}

.avatar-container img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.avatar-placeholder {
  font-size: 20px;
  font-weight: 700;
  color: var(--brand-primary);
}

.pulse-active::after {
  content: '';
  position: absolute;
  inset: -3px;
  border: 2px solid var(--brand-primary);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(1.15); opacity: 0; }
}

.account-main-info {
  flex: 1;
  min-width: 0;
}

.account-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-username {
  font-size: 11px;
  color: var(--text-muted);
}

.delete-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.delete-btn:hover {
  color: var(--brand-secondary);
  background: rgba(255, 0, 80, 0.1);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.platform-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.platform-label {
  font-size: 10px;
  font-weight: 800;
  color: var(--text-muted);
  letter-spacing: 0.05em;
}

.last-sync {
  font-size: 10px;
  color: var(--text-muted);
}

.stats-row {
  display: flex;
  gap: var(--spacing-xl);
  padding: 8px 0;
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 15px;
  font-weight: 700;
}

.stat-label {
  font-size: 10px;
  color: var(--text-muted);
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid var(--border-subtle);
  padding-top: 12px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-badge.active { color: #00ff88; }
.status-badge.active .status-dot { background: #00ff88; box-shadow: 0 0 6px #00ff88; }

.status-badge.inactive { color: #888; }
.status-badge.inactive .status-dot { background: #888; }

.status-badge.suspended { color: var(--brand-secondary); }
.status-badge.suspended .status-dot { background: var(--brand-secondary); }

.status-badge.expired { color: #ffcc00; }
.status-badge.expired .status-dot { background: #ffcc00; }

.refresh-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
}

.refresh-btn:hover {
  color: var(--brand-primary);
}

/* ── 抽屉 ── */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 1000;
}

.add-account-drawer {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 400px;
  background: var(--bg-elevated);
  box-shadow: -4px 0 20px rgba(0,0,0,0.5);
  display: flex;
  flex-direction: column;
}

.drawer-header {
  padding: var(--spacing-lg);
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-default);
}

.drawer-form {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-item label {
  font-size: 13px;
  color: var(--text-secondary);
}

.form-item input, .form-item select {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  outline: none;
}

.form-actions {
  margin-top: var(--spacing-xl);
  display: flex;
  gap: var(--spacing-md);
}

.btn-save {
  flex: 1;
  background: var(--brand-primary);
  color: #000;
  border: none;
  padding: 10px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel {
  flex: 1;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  padding: 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--text-muted);
  gap: 12px;
}

.rotating {
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.drawer-enter-active, .drawer-leave-active {
  transition: transform 0.3s ease;
}
.drawer-enter-from, .drawer-leave-to {
  transform: translateX(100%);
}
</style>
