<template>
  <aside class="shell-sidebar" :data-collapsed="String(isCollapsed)">
    <nav class="shell-sidebar__nav" aria-label="TK-OPS 页面导航">
      <section v-for="group in navGroups" :key="group.label" class="shell-sidebar__group">
        <p class="shell-sidebar__group-title">{{ group.label }}</p>

        <template v-for="item in group.items" :key="item.id">
          <RouterLink
            v-if="!item.requiresProjectContext || hasProject"
            :data-route-id="item.id"
            :title="isCollapsed ? item.title : ''"
            :to="item.path"
            active-class="is-active"
            class="shell-nav-link"
          >
            <span class="shell-nav-link__icon material-symbols-outlined">{{ item.icon }}</span>
            <span class="shell-nav-link__text">{{ item.title }}</span>
          </RouterLink>

          <div
            v-else
            :data-route-id="item.id"
            :title="isCollapsed ? item.title : '请先在创作总览选择项目'"
            class="shell-nav-link shell-nav-link--disabled"
          >
            <span class="shell-nav-link__icon material-symbols-outlined">{{ item.icon }}</span>
            <span class="shell-nav-link__text">{{ item.title }}</span>
          </div>
        </template>
      </section>
    </nav>

    <footer class="shell-sidebar__footer">
      <div class="shell-sidebar__user-card">
        <div class="shell-sidebar__avatar">
          <span class="material-symbols-outlined">person</span>
        </div>
        <div class="shell-sidebar__user-info">
          <span class="user-name">本地创作者</span>
          <span class="user-status">{{ hasProject ? "工作区已连接" : "离线授权" }}</span>
        </div>
      </div>

      <button class="shell-sidebar__toggle" :title="isCollapsed ? '展开侧边栏' : '折叠侧边栏'" @click="shellUiStore.toggleSidebar()">
        <span class="material-symbols-outlined">{{ isCollapsed ? "keyboard_double_arrow_right" : "keyboard_double_arrow_left" }}</span>
      </button>
    </footer>
  </aside>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import type { RouteManifestItem } from "@/types/router";
import { useShellUiStore } from "@/stores/shell-ui";

defineProps<{
  hasProject: boolean;
  isCollapsed: boolean;
  navGroups: Array<{
    label: string;
    items: RouteManifestItem[];
  }>;
  projectLabel: string;
}>();

const shellUiStore = useShellUiStore();
</script>

<style scoped>
.shell-sidebar {
  background: var(--color-bg-canvas);
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  /* 展开态：padding: var(--space-4) var(--space-3) */
  padding: var(--space-4) var(--space-3);
  transition: padding var(--motion-default) var(--ease-spring);
}

.shell-sidebar[data-collapsed="true"] {
  /* 折叠态：padding: var(--space-4) var(--space-2) */
  padding: var(--space-4) var(--space-2);
}

.shell-sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.shell-sidebar__group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.shell-sidebar__group-title {
  align-items: center;
  color: var(--color-text-tertiary);
  display: flex;
  font: var(--font-caption);
  height: 24px;
  letter-spacing: 0.8px;
  margin: var(--space-2) 0 0;
  padding: 0 var(--space-3);
  text-transform: uppercase;
  white-space: nowrap;
  transition: opacity var(--motion-default) var(--ease-standard);
  opacity: 1;
}

.shell-sidebar[data-collapsed="true"] .shell-sidebar__group-title {
  opacity: 0;
  pointer-events: none;
  height: 0;
  margin: 0;
  overflow: hidden;
}

.shell-nav-link {
  align-items: center;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  display: flex;
  gap: var(--space-3);
  height: 40px;
  padding: 0 12px;
  text-decoration: none;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard),
    transform var(--motion-instant) var(--ease-bounce);
  white-space: nowrap;
  position: relative;
}

.shell-sidebar[data-collapsed="true"] .shell-nav-link {
  padding: 0;
  justify-content: center;
}

.shell-nav-link:hover:not(.shell-nav-link--disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.shell-nav-link:active:not(.shell-nav-link--disabled) {
  transform: scale(0.98);
}

.shell-nav-link.is-active {
  background: var(--color-bg-active);
  color: var(--color-brand-primary);
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--color-brand-primary);
  position: relative;
}

/* 活跃项左侧指示条微流光 */
.shell-nav-link.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, var(--color-brand-primary), var(--color-brand-secondary), var(--color-brand-primary));
  background-size: 100% 200%;
  animation: sidebar-active-flow var(--motion-breathe) ease-in-out infinite alternate;
}

@keyframes sidebar-active-flow {
  from { background-position: 0% 0%; }
  to { background-position: 0% 100%; }
}

.shell-nav-link__icon {
  font-size: 20px;
  flex-shrink: 0;
}

.shell-nav-link__text {
  font: var(--font-title-sm);
  letter-spacing: var(--ls-title-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  transition: opacity var(--motion-default) var(--ease-standard);
  opacity: 1;
}

.shell-sidebar[data-collapsed="true"] .shell-nav-link__text {
  opacity: 0;
  width: 0;
  display: none;
}

.shell-nav-link--disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

/* 底部固定区 */
.shell-sidebar__footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding-top: var(--space-4);
}

.shell-sidebar__user-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 40px;
  overflow: hidden;
  transition: opacity var(--motion-default) var(--ease-standard);
  white-space: nowrap;
}

.shell-sidebar[data-collapsed="true"] .shell-sidebar__user-card {
  opacity: 0;
  width: 0;
  display: none;
}

.shell-sidebar__avatar {
  align-items: center;
  background: var(--gradient-ai-primary);
  border-radius: var(--radius-full);
  color: var(--color-text-on-brand);
  display: flex;
  flex-shrink: 0;
  height: 32px;
  justify-content: center;
  width: 32px;
  box-shadow: var(--shadow-glow-brand);
}

.shell-sidebar__avatar .material-symbols-outlined {
  font-size: 16px;
}

.shell-sidebar__user-info {
  display: flex;
  flex-direction: column;
}

.shell-sidebar__user-info .user-name {
  font: var(--font-title-sm);
  letter-spacing: var(--ls-title-sm);
  color: var(--color-text-primary);
  line-height: 1.2;
}

.shell-sidebar__user-info .user-status {
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.shell-sidebar__toggle {
  align-items: center;
  appearance: none;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  display: flex;
  flex-shrink: 0;
  height: 32px;
  justify-content: center;
  width: 32px;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}

.shell-sidebar[data-collapsed="true"] .shell-sidebar__toggle {
  margin: 0 auto;
}

.shell-sidebar__toggle:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.shell-sidebar__toggle:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
</style>
