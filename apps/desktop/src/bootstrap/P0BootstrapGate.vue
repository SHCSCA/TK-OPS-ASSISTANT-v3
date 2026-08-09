<template>
  <RouterView v-if="isSetupRoute" />
  <AccountWorkspaceLayout v-else-if="bootstrapStore.phase === 'ready'" />
  <BootstrapLoadingScreen
    v-else-if="
      bootstrapStore.phase === 'idle'
      || bootstrapStore.phase === 'loading'
    "
  />
  <BootstrapErrorScreen
    v-else-if="bootstrapStore.phase === 'error'"
    :can-restart="bootstrapStore.canRestartRuntime"
    :error-summary="errorSummary"
    :restarting="bootstrapStore.operation === 'restarting_runtime'"
    @restart="bootstrapStore.restartRuntime"
    @retry="bootstrapStore.load"
  />
  <RouterView v-else />
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterView, useRoute } from "vue-router";

import { routeIds } from "@/app/router";
import AccountWorkspaceLayout from "@/layouts/account-workspace/AccountWorkspaceLayout.vue";
import { useP0BootstrapStore } from "@/modules/system/bootstrap-store";

import BootstrapErrorScreen from "./BootstrapErrorScreen.vue";
import BootstrapLoadingScreen from "./BootstrapLoadingScreen.vue";

const bootstrapStore = useP0BootstrapStore();
const route = useRoute();

const isSetupRoute = computed(
  () => route.name === routeIds.setupLicenseWizard
);
const errorSummary = computed(() => {
  const error = bootstrapStore.error;
  if (!error) return "本机 Runtime 启动检查失败。";
  const reference = error.logId || error.requestId;
  return reference ? `${error.message}（${reference}）` : error.message;
});

</script>
