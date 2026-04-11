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
        <span class="status-pill" :class="`status-pill--${configBusStore.runtimeStatus}`">
          {{ runtimeStatusLabel }}
        </span>
        <span class="status-pill" :class="`status-pill--${configStatusTone}`">
          {{ configStatusLabel }}
        </span>
        <span class="status-pill" :class="`status-pill--${licenseStatusTone}`">
          {{ licenseStatusLabel }}
        </span>
        <span class="title-bar__meta">{{ currentPage.navGroup }}</span>
      </div>
    </header>

    <div class="app-shell__body" :class="{ 'app-shell__body--wizard': isWizardPage }">
      <aside v-if="showWorkspaceChrome" class="sidebar">
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

      <aside v-if="showWorkspaceChrome" class="detail-panel">
        <div class="detail-panel__section">
          <p class="detail-panel__label">Current Page</p>
          <h2>{{ currentPage.title }}</h2>
          <p>{{ currentPage.componentImport }}</p>
        </div>

        <div class="detail-panel__section">
          <p class="detail-panel__label">Runtime</p>
          <template v-if="health">
            <p>Service: {{ health.service }}</p>
            <p>Mode: {{ health.mode }}</p>
            <p>Version: {{ health.version }}</p>
          </template>
          <p v-else>{{ runtimeDetail }}</p>
        </div>

        <div v-if="showSettingsDiagnostics" class="detail-panel__section">
          <p class="detail-panel__label">Diagnostics</p>
          <template v-if="diagnostics">
            <p>Database: {{ diagnostics.databasePath }}</p>
            <p>Log dir: {{ diagnostics.logDir }}</p>
            <p>Revision: {{ diagnostics.revision }}</p>
            <p>Health: {{ diagnostics.healthStatus }}</p>
          </template>
          <p v-else>No diagnostics loaded.</p>
        </div>

        <div v-if="showSettingsDiagnostics" class="detail-panel__section">
          <p class="detail-panel__label">Last Error</p>
          <p>{{ lastErrorSummary }}</p>
        </div>

        <div v-if="showSettingsDiagnostics" class="detail-panel__section">
          <p class="detail-panel__label">License</p>
          <p>Status: {{ licenseStatusLabel }}</p>
          <p>Machine: {{ licenseStore.machineId || "pending" }}</p>
          <p>Bound: {{ licenseStore.machineBound ? "yes" : "no" }}</p>
          <p>Code: {{ licenseStore.maskedCode || "not activated" }}</p>
        </div>
      </aside>
    </div>

    <footer class="status-bar">
      <span>{{ runtimeStatusLabel }}</span>
      <span>{{ isWizardPage ? licenseStatusLabel : configStatusLabel }}</span>
      <span>{{ isWizardPage ? wizardStatusLabel : lastSyncLabel }}</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, watchEffect } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

import { routeIds, routeManifest } from "@/app/router";
import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";

const route = useRoute();
const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const { diagnostics, error, health } = storeToRefs(configBusStore);

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
const isWizardPage = computed(() => currentPage.value.pageType === "wizard");
const showWorkspaceChrome = computed(() => !isWizardPage.value);

const runtimeStatusLabel = computed(() => {
  switch (configBusStore.runtimeStatus) {
    case "loading":
      return "Runtime checking";
    case "online":
      return "Runtime online";
    case "offline":
      return "Runtime offline";
    default:
      return "Runtime idle";
  }
});

const licenseStatusLabel = computed(() => {
  if (licenseStore.active) {
    return "License active";
  }

  if (licenseStore.status === "loading" || licenseStore.status === "submitting") {
    return "License checking";
  }

  return "License restricted";
});

const licenseStatusTone = computed(() => {
  if (licenseStore.active) {
    return "online";
  }

  if (licenseStore.status === "loading" || licenseStore.status === "submitting") {
    return "loading";
  }

  return "offline";
});

const configStatusLabel = computed(() => {
  switch (configBusStore.status) {
    case "loading":
      return "Config loading";
    case "saving":
      return "Config saving";
    case "ready":
      return "Config ready";
    case "error":
      return "Config error";
    default:
      return "Config idle";
  }
});

const configStatusTone = computed(() => {
  switch (configBusStore.status) {
    case "ready":
      return "online";
    case "error":
      return "offline";
    case "loading":
    case "saving":
      return "loading";
    default:
      return "idle";
  }
});

const runtimeDetail = computed(() => {
  if (configBusStore.runtimeStatus === "online" && health.value) {
    return `${health.value.version} · ${health.value.mode} · ${health.value.now}`;
  }

  if (error.value) {
    return lastErrorSummary.value;
  }

  return "No runtime snapshot yet.";
});

const lastSyncLabel = computed(() => {
  return configBusStore.lastSyncedAt
    ? `Last sync ${configBusStore.lastSyncedAt}`
    : "Last sync pending";
});

const wizardStatusLabel = computed(() => {
  return licenseStore.machineId
    ? `Machine ${licenseStore.machineId}`
    : "Machine pending";
});

const showSettingsDiagnostics = computed(() => currentPage.value.id === routeIds.aiSystemSettings);

const lastErrorSummary = computed(() => {
  if (licenseStore.error) {
    return licenseStore.error.requestId
      ? `${licenseStore.error.message} (${licenseStore.error.requestId})`
      : licenseStore.error.message;
  }

  if (!error.value) {
    return "No recent runtime errors.";
  }

  return error.value.requestId
    ? `${error.value.message} (${error.value.requestId})`
    : error.value.message;
});

watchEffect(() => {
  document.title = `TK-OPS | ${currentPage.value.title}`;
});

onMounted(() => {
  if (configBusStore.status === "idle") {
    void configBusStore.load();
  }

  if (licenseStore.status === "idle") {
    void licenseStore.loadStatus();
  }
});
</script>
