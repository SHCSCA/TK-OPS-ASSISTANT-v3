<template>
  <AppShell v-if="bootstrapStore.phase === 'ready'" />
  <BootstrapLoadingScreen v-else-if="bootstrapStore.phase === 'boot_loading'" />
  <BootstrapErrorScreen
    v-else-if="bootstrapStore.phase === 'boot_error'"
    :error-summary="errorSummary"
    @retry="handleRetry"
  />
  <BootstrapLicenseScreen v-else-if="bootstrapStore.phase === 'license_required'" />
  <BootstrapInitializationScreen v-else />
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { routeIds } from "@/app/router";
import AppShell from "@/layouts/AppShell.vue";
import { useBootstrapStore } from "@/stores/bootstrap";
import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";

import BootstrapErrorScreen from "./BootstrapErrorScreen.vue";
import BootstrapInitializationScreen from "./BootstrapInitializationScreen.vue";
import BootstrapLicenseScreen from "./BootstrapLicenseScreen.vue";
import BootstrapLoadingScreen from "./BootstrapLoadingScreen.vue";

const bootstrapStore = useBootstrapStore();
const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const route = useRoute();
const router = useRouter();

const errorSummary = computed(() => {
  if (configBusStore.error) {
    return configBusStore.error.requestId
      ? `${configBusStore.error.message} (${configBusStore.error.requestId})`
      : configBusStore.error.message;
  }

  if (licenseStore.error) {
    return licenseStore.error.requestId
      ? `${licenseStore.error.message} (${licenseStore.error.requestId})`
      : licenseStore.error.message;
  }

  return "启动检查失败。";
});

onMounted(() => {
  void bootstrapStore.load();
});

watch(
  () => bootstrapStore.phase,
  async (phase) => {
    if (phase !== "ready") {
      return;
    }

    if (route.name === routeIds.setupLicenseWizard && !route.query.preview) {
      await router.replace(resolveRedirectTarget(route.query.redirect));
    }
  }
);

async function handleRetry(): Promise<void> {
  await bootstrapStore.retry();
}

function resolveRedirectTarget(value: unknown): string {
  if (typeof value !== "string" || value.length === 0) {
    return "/dashboard";
  }

  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
</script>

