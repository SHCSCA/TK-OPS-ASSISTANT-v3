<template>
  <aside class="shell-sidebar" :class="{ 'sidebar--collapsed': isCollapsed }">
    <nav class="shell-sidebar__nav" aria-label="TK-OPS 页面导航">
      <section v-for="group in navGroups" :key="group.label">
        <p v-if="!isCollapsed" class="nav-group__title">{{ group.label }}</p>
        <div v-else class="nav-group__divider"></div>

        <RouterLink
          v-for="item in group.items"
          :key="item.id"
          :to="item.path"
          class="shell-nav-link"
          active-class="nav-link--active"
          :data-route-id="item.id"
          :title="isCollapsed ? item.title : ''"
        >
          <span class="shell-nav-link__icon material-symbols-outlined">{{ item.icon }}</span>
          <span v-if="!isCollapsed" class="shell-nav-link__text">{{ item.title }}</span>
        </RouterLink>
      </section>
    </nav>

    <div class="sidebar-footer" v-show="!isCollapsed">
      <p>© 2026 TK-OPS v3</p>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import type { RouteManifestItem } from "@/types/router";

defineProps<{
  navGroups: Array<{
    label: string;
    items: RouteManifestItem[];
  }>;
  isCollapsed: boolean;
}>();
</script>

<style scoped>
.shell-sidebar {
  transition: width var(--motion-base), background var(--motion-base);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow-x: hidden;
  height: 100%;
}

.sidebar--collapsed {
  width: 68px !important;
}

.nav-group__title {
  font-size: 11px;
  font-weight: 800;
  color: var(--text-tertiary);
  padding: 16px 20px 8px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  white-space: nowrap;
}

.nav-group__divider {
  height: 1px;
  background: var(--border-default);
  margin: 16px 14px;
}

.shell-nav-link {
  margin: 4px 12px;
  padding: 0 12px;
  height: 40px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  transition: all var(--motion-fast);
  position: relative;
  white-space: nowrap;
}

.sidebar--collapsed .shell-nav-link {
  margin: 4px 10px;
  padding: 0;
  justify-content: center;
}

.shell-nav-link__icon {
  font-size: 22px;
  min-width: 24px;
  text-align: center;
}

.shell-nav-link__text {
  font-size: 14px;
  font-weight: 500;
}

.shell-nav-link:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.shell-nav-link.nav-link--active {
  background: var(--surface-tertiary);
  color: var(--brand-primary);
  box-shadow: inset 3px 0 0 var(--brand-primary);
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-default);
  font-size: 10px;
  color: var(--text-tertiary);
  text-align: center;
}
</style>
