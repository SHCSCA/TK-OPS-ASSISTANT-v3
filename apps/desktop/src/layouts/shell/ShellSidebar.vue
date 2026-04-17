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
      <div class="shell-sidebar__workspace-card">
        <div class="shell-sidebar__workspace-avatar">TK</div>
        <div class="shell-sidebar__workspace-copy">
          <span>{{ hasProject ? "当前项目" : "等待项目" }}</span>
          <strong>{{ projectLabel }}</strong>
        </div>
      </div>
      <span class="shell-sidebar__footer-label">{{ hasProject ? "工作区已连接" : "部分页面保持只读" }}</span>
    </footer>
  </aside>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";

import type { RouteManifestItem } from "@/types/router";

defineProps<{
  hasProject: boolean;
  isCollapsed: boolean;
  navGroups: Array<{
    label: string;
    items: RouteManifestItem[];
  }>;
  projectLabel: string;
}>();
</script>

<style scoped>
.shell-sidebar {
  background: var(--color-bg-canvas);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  height: 100%;
  min-width: 0;
  padding: var(--space-4) var(--space-3);
}

.shell-sidebar__nav {
  display: grid;
  gap: var(--space-4);
  min-height: 0;
  overflow: auto;
}

.shell-sidebar__group {
  display: grid;
  gap: 4px;
}

.shell-sidebar__group-title {
  align-items: center;
  color: var(--color-text-tertiary);
  display: flex;
  font-size: 11px;
  font-weight: 600;
  height: 24px;
  letter-spacing: 0.8px;
  margin: var(--space-2) 0 0;
  padding: 0 var(--space-3);
  text-transform: uppercase;
  white-space: nowrap;
}

.shell-nav-link {
  align-items: center;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  display: grid;
  gap: var(--space-3);
  grid-template-columns: 20px minmax(0, 1fr);
  height: 40px;
  padding: 0 12px;
  position: relative;
  text-decoration: none;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard),
    transform var(--motion-instant) var(--ease-bounce);
}

.shell-nav-link:hover:not(.shell-nav-link--disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.shell-nav-link.is-active {
  background: var(--color-bg-active);
  border-color: color-mix(in srgb, var(--color-brand-primary) 24%, var(--color-border-default));
  color: var(--color-brand-primary);
}

.shell-nav-link.is-active::before {
  background: var(--color-brand-primary);
  border-radius: 0 2px 2px 0;
  box-shadow: var(--shadow-glow-brand);
  content: "";
  height: 20px;
  left: -12px;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
}

.shell-nav-link__icon {
  font-size: 20px;
}

.shell-nav-link__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shell-nav-link--disabled {
  opacity: 0.48;
}

.shell-sidebar__footer {
  border-top: 1px solid var(--color-border-subtle);
  display: grid;
  gap: var(--space-3);
  margin-top: auto;
  padding-top: var(--space-3);
}

.shell-sidebar__workspace-card {
  align-items: center;
  background: var(--color-bg-surface);
  border-radius: var(--radius-md);
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3);
}

.shell-sidebar__workspace-avatar {
  align-items: center;
  background: var(--gradient-ai-primary);
  border-radius: var(--radius-full);
  color: var(--color-text-on-brand);
  display: inline-flex;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  height: 32px;
  justify-content: center;
  width: 32px;
}

.shell-sidebar__workspace-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.shell-sidebar__workspace-copy span,
.shell-sidebar__footer-label {
  color: var(--color-text-tertiary);
  font-size: var(--font-caption);
}

.shell-sidebar__workspace-copy strong {
  font-size: var(--font-body-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

[data-collapsed="true"] .shell-sidebar__group-title,
[data-collapsed="true"] .shell-nav-link__text,
[data-collapsed="true"] .shell-sidebar__workspace-copy,
[data-collapsed="true"] .shell-sidebar__footer-label {
  display: none;
}

[data-collapsed="true"] .shell-nav-link {
  grid-template-columns: 1fr;
  justify-items: center;
  padding: 0;
}

[data-collapsed="true"] .shell-sidebar__workspace-card {
  justify-content: center;
  padding: var(--space-2);
}
</style>
