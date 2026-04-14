<template>
  <header class="shell-title-bar">
    <div class="shell-title-bar__left">
      <!-- 侧边栏折叠按钮 -->
      <button class="icon-button" @click="handleToggleSidebar" title="收起/展开侧边栏">
        <span class="material-symbols-outlined icon-size">
          {{ isCollapsed ? 'menu_open' : 'menu' }}
        </span>
      </button>

      <!-- Logo 与 品牌 -->
      <div class="shell-brand">
        <div class="shell-brand__logo">TK</div>
        <span class="shell-brand__text">TK-OPS</span>
        <span style="position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;">本地 AI 视频创作中枢</span>
      </div>

      <div class="divider"></div>

      <!-- 项目上下文 -->
      <div v-if="projectName" class="project-indicator">
        <span class="material-symbols-outlined project-icon">folder_open</span>
        <span class="project-indicator__name">{{ projectName }}</span>
      </div>
    </div>

    <div class="shell-title-bar__center">
      <div class="shell-title-bar__search">
        <span class="material-symbols-outlined search-icon">search</span>
        <input type="text" placeholder="搜索项目、脚本、资产 (Cmd+K)" disabled />
      </div>
    </div>

    <div class="shell-title-bar__right">
      <div class="shell-title-bar__actions">
        <!-- 系统通知 -->
        <button class="icon-button notification-btn" title="系统通知">
          <span class="material-symbols-outlined icon-size">notifications</span>
          <span class="notification-badge"></span>
        </button>

        <!-- 主题切换 -->
        <button class="icon-button" @click="handleToggleTheme" title="切换主题">
          <span class="material-symbols-outlined icon-size">contrast</span>
        </button>

        <div class="divider"></div>

        <!-- 状态与用户 -->
        <div class="runtime-status-container">
          <span class="runtime-dot" :class="'runtime-dot--' + runtimeTone"></span>
        </div>
        
        <div class="user-profile">
          <div class="user-profile__avatar">AD</div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
const props = defineProps<{
  runtimeTone: string;
  isCollapsed: boolean;
  projectName?: string;
}>();

const emit = defineEmits<{
  (e: 'toggle-sidebar'): void;
  (e: 'toggle-theme'): void;
}>();

function handleToggleSidebar() {
  emit('toggle-sidebar');
}

function handleToggleTheme() {
  emit('toggle-theme');
}
</script>

<style scoped>
.shell-title-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 100%;
}

.shell-title-bar__left,
.shell-title-bar__right {
  display: flex;
  align-items: center;
  height: 100%;
}

.shell-title-bar__center {
  flex: 1;
  display: flex;
  justify-content: center;
  max-width: 600px;
}

.icon-button {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  transition: all var(--motion-fast);
  margin: 0 4px;
  position: relative;
}

.icon-button:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--brand-primary);
}

.icon-size {
  font-size: 22px;
}

.shell-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: 12px;
}

.shell-brand__logo {
  width: 30px;
  height: 30px;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 900;
  font-size: 14px;
}

.shell-brand__text {
  font-weight: 900;
  font-size: 18px;
  letter-spacing: -0.03em;
  color: var(--text-primary);
}

.project-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 12px;
  padding: 6px 14px;
  background: var(--surface-sunken);
  border-radius: 20px;
  color: var(--text-secondary);
  font-size: 13px;
  border: 1px solid var(--border-default);
  max-width: 200px;
}

.project-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.project-indicator__name {
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shell-title-bar__search {
  display: flex;
  align-items: center;
  background: var(--surface-sunken);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 0 14px;
  width: 100%;
  max-width: 440px;
  transition: all var(--motion-fast);
}

.shell-title-bar__search:focus-within {
  border-color: var(--brand-primary);
  box-shadow: 0 0 15px rgba(0, 242, 234, 0.2);
  max-width: 500px;
}

.shell-title-bar__search input {
  background: transparent;
  border: none;
  color: var(--text-primary);
  flex: 1;
  font-size: 13px;
  height: 36px;
  outline: none;
  padding-left: 10px;
}

.search-icon {
  font-size: 18px;
  color: var(--text-tertiary);
}

.shell-title-bar__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.divider {
  width: 1px;
  height: 20px;
  background: var(--border-default);
  margin: 0 12px;
}

.notification-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 7px;
  height: 7px;
  background: var(--status-error);
  border-radius: 50%;
  border: 2px solid var(--surface-secondary);
  box-shadow: 0 0 5px rgba(239, 68, 68, 0.4);
}

.runtime-status-container {
  display: flex;
  align-items: center;
  margin: 0 8px;
}

.user-profile {
  margin-left: 8px;
}

.user-profile__avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--surface-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  color: var(--brand-primary);
  border: 1px solid var(--border-default);
}
</style>
