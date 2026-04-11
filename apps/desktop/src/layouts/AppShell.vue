<template>
  <div class="app-shell">
    <header class="title-bar">
      <div class="title-bar__brand">
        <div class="brand-mark">TK</div>
        <div>
          <p class="brand-label">TK-OPS</p>
          <h1>{{ currentPage.title }}</h1>
        </div>
      </div>
      <div class="title-bar__status">
        <span class="status-pill" :class="`status-pill--${runtimeHealthStore.status}`">
          {{ runtimeStatusLabel }}
        </span>
        <span class="title-bar__meta">{{ currentPage.navGroup }}</span>
      </div>
    </header>

    <div class="app-shell__body">
      <aside class="sidebar">
        <nav>
          <section v-for="group in navGroups" :key="group.label" class="nav-group">
            <p class="nav-group__title">{{ group.label }}</p>
            <RouterLink
              v-for="item in group.items"
              :key="item.id"
              :to="item.path"
              class="nav-link"
              active-class="nav-link--active"
              :data-route-id="item.id"
            >
              <span class="nav-link__icon">{{ item.icon }}</span>
              <span>{{ item.title }}</span>
            </RouterLink>
          </section>
        </nav>
      </aside>

      <main class="content-host">
        <RouterView />
      </main>

      <aside class="detail-panel">
        <div class="detail-panel__section">
          <p class="detail-panel__label">当前页面</p>
          <h2>{{ currentPage.title }}</h2>
          <p>{{ currentPage.componentImport }}</p>
        </div>

        <div class="detail-panel__section">
          <p class="detail-panel__label">Runtime</p>
          <template v-if="runtimeHealthStore.snapshot">
            <p>服务状态：{{ runtimeHealthStore.snapshot.service }}</p>
            <p>运行模式：{{ runtimeHealthStore.snapshot.mode }}</p>
            <p>版本：{{ runtimeHealthStore.snapshot.version }}</p>
          </template>
          <p v-else>{{ runtimeHealthDetail }}</p>
        </div>
      </aside>
    </div>

    <footer class="status-bar">
      <span>{{ runtimeStatusLabel }}</span>
      <span>{{ runtimeHealthDetail }}</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, watchEffect } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

import { routeManifest } from "@/app/router";
import { useRuntimeHealthStore } from "@/stores/runtime-health";

const route = useRoute();
const runtimeHealthStore = useRuntimeHealthStore();
const { snapshot } = storeToRefs(runtimeHealthStore);

const navGroups = computed(() => {
  const labels = [...new Set(routeManifest.map((item) => item.navGroup))];
  return labels.map((label) => ({
    label,
    items: routeManifest.filter((item) => item.navGroup === label)
  }));
});

const currentPage = computed(() => {
  return routeManifest.find((item) => item.id === route.name) ?? routeManifest[0];
});

const runtimeStatusLabel = computed(() => {
  switch (runtimeHealthStore.status) {
    case "loading":
      return "Runtime 检查中";
    case "online":
      return "Runtime 在线";
    case "offline":
      return "Runtime 离线";
    default:
      return "Runtime 未检查";
  }
});

const runtimeHealthDetail = computed(() => {
  if (runtimeHealthStore.status === "online" && snapshot.value) {
    return `版本 ${snapshot.value.version} · ${snapshot.value.mode} · ${snapshot.value.now}`;
  }

  if (runtimeHealthStore.error) {
    return runtimeHealthStore.error;
  }

  return "尚未获得 Runtime 健康状态。";
});

watchEffect(() => {
  document.title = `TK-OPS · ${currentPage.value.title}`;
});

onMounted(() => {
  void runtimeHealthStore.refresh();
});
</script>
