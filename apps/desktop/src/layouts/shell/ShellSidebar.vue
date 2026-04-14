<template>
  <aside class="sidebar command-sidebar shell-sidebar">
    <div class="sidebar__intro command-sidebar__intro">
      <p>工作台导航</p>
      <strong>创作、媒体与执行闭环</strong>
    </div>

    <nav aria-label="TK-OPS 页面导航">
      <section v-for="group in navGroups" :key="group.label" class="nav-group">
        <p class="nav-group__title">{{ group.label }}</p>
        <RouterLink
          v-for="item in group.items"
          :key="item.id"
          :to="item.path"
          class="nav-link command-nav-link"
          active-class="nav-link--active"
          :data-route-id="item.id"
        >
          <span class="nav-link__icon">{{ item.icon }}</span>
          <span>{{ item.title }}</span>
        </RouterLink>
      </section>
    </nav>
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
}>();
</script>
