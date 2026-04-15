<template>
  <header class="shell-title-bar" data-tauri-drag-region>
    <div class="shell-title-bar__left" data-tauri-drag-region>
      <!-- 侧边栏折叠按钮 -->
      <button class="icon-button" @click="handleToggleSidebar" title="收起/展开侧边栏">
        <span class="material-symbols-outlined icon-size">
          {{ isCollapsed ? 'menu_open' : 'menu' }}
        </span>
      </button>

      <!-- Logo 与 品牌 -->
      <div class="shell-brand" data-tauri-drag-region>
        <div class="shell-brand__logo" data-tauri-drag-region>TK</div>
        <span class="shell-brand__text" data-tauri-drag-region>TK-OPS</span>
        <span style="position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;">本地 AI 视频创作中枢</span>
      </div>
    </div>

    <!-- 中间区域留空，作为可拖拽区域 -->
    <div class="shell-title-bar__center" data-tauri-drag-region></div>

    <div class="shell-title-bar__right">
      <div class="shell-title-bar__actions">
        <!-- 系统通知 -->
        <button class="icon-button notification-btn" title="系统通知">
          <span class="material-symbols-outlined icon-size">notifications</span>
          <span class="notification-badge"></span>
        </button>

        <!-- 侧边抽屉 -->
        <button class="icon-button" @click="handleToggleDetail" title="切换属性面板">
          <span class="material-symbols-outlined icon-size">dock_to_left</span>
        </button>

        <!-- 主题切换 -->
        <button class="icon-button" @click="handleToggleTheme" title="切换主题">
          <span class="material-symbols-outlined icon-size">contrast</span>
        </button>

        <div class="divider"></div>
        
        <div class="user-profile">
          <div class="user-profile__avatar">AD</div>
        </div>

        <div class="divider"></div>

        <!-- 窗口控制 -->
        <div class="window-controls" aria-label="窗口控制">
          <button class="win-btn" type="button" title="最小化" @click="handleMinimize">
            <span class="material-symbols-outlined win-btn-icon">remove</span>
          </button>
          <button class="win-btn" type="button" title="最大化/还原" @click="handleToggleMaximize">
            <span class="material-symbols-outlined win-btn-icon">crop_square</span>
          </button>
          <button class="win-btn win-btn--close" type="button" title="关闭" @click="handleClose">
            <span class="material-symbols-outlined win-btn-icon">close</span>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  isCollapsed: boolean;
}>();

const emit = defineEmits<{
  (e: 'toggle-sidebar'): void;
  (e: 'toggle-theme'): void;
  (e: 'toggle-detail'): void;
}>();

function handleToggleSidebar() {
  emit('toggle-sidebar');
}

function handleToggleTheme() {
  emit('toggle-theme');
}

function handleToggleDetail() {
  emit('toggle-detail');
}

function handleWindowError(action: string, error: unknown) {
  console.warn(`[Tauri 模拟] 窗口${action}动作被触发，但在测试/浏览器环境中被忽略。`, error);
}

async function handleMinimize() {
  try { 
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    await getCurrentWindow().minimize(); 
  } catch (e) { handleWindowError('最小化', e); }
}

async function handleToggleMaximize() {
  try { 
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    await getCurrentWindow().toggleMaximize(); 
  } catch (e) { handleWindowError('最大化切换', e); }
}

async function handleClose() {
  try { 
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    await getCurrentWindow().close(); 
  } catch (e) { handleWindowError('关闭', e); }
}
</script>

<style scoped>
.shell-title-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 0 16px;
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
  height: 100%;
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
  margin: 0 2px;
  position: relative;
}

.icon-button:hover {
  background: color-mix(in srgb, var(--brand-primary) 10%, transparent);
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

.shell-title-bar__actions {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 100%;
}

.divider {
  width: 1px;
  height: 20px;
  background: var(--border-default);
  margin: 0 8px;
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

.user-profile {
  margin: 0 8px;
}

.user-profile__avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--brand-primary) 15%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  color: var(--brand-primary);
  border: 1px solid color-mix(in srgb, var(--brand-primary) 30%, transparent);
}

.window-controls {
  display: flex;
  align-items: center;
  height: 100%;
}

.win-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 100%;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--motion-fast);
}

.win-btn:hover {
  background: var(--surface-tertiary);
  color: var(--text-primary);
}

.win-btn--close:hover {
  background: #e81123;
  color: #ffffff;
}

.win-btn-icon {
  font-size: 18px;
}
</style>
