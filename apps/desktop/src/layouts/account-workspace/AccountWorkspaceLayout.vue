<template>
  <div class="account-workspace-root">
    <div class="account-workspace-shell">
      <AccountSidebar
        :accounts="accountOptions"
        :compact="compact"
        :current-account="currentAccount"
        :current-account-id="currentAccountDto?.id ?? null"
        :switch-disabled="switchBusy"
        :switcher-open="switcherOpen"
        :system-items="systemItems"
        :workspace-items="workspaceItems"
        @add-account="openAccountManagement(true)"
        @close-switcher="switcherOpen = false"
        @manage-accounts="openAccountManagement(false)"
        @switch-account="switchAccount"
        @toggle-switcher="switcherOpen = !switcherOpen"
      />

      <AccountTopBar
        :account-name="currentAccountDto?.name ?? null"
        :details-available="Boolean(detailContext)"
        :details-open="accountDetailOpen"
        :runtime-label="runtimeLabel"
        :runtime-tone="runtimeTone"
        :theme-action-label="themeActionLabel"
        :theme-icon="themeIcon"
        :title="pageTitle"
        @open-details="accountDetailOpen = true"
        @toggle-theme="toggleTheme"
      />

      <div class="account-workspace-main">
        <LegacyRouteMigrationNotice
          :message="migrationMessage"
          @dismiss="dismissMigrationNotice"
        />
        <AccountWorkspaceEmptyState
          v-if="isAccountRoute && !currentAccountDto && !switchBusy"
          @add="openAccountManagement(true)"
          @select="switcherOpen = true"
        />
        <RouterView v-else v-slot="{ Component }">
          <component
            :is="Component"
            v-if="isAccountRoute"
            :account-id="visibleAccountId"
            :workspace-context="visibleContext"
          />
          <component :is="Component" v-else />
        </RouterView>

        <div
          v-if="contentTransitionBusy"
          class="account-workspace-switch-mask"
          role="status"
          aria-live="polite"
        >
          <span class="material-symbols-outlined">progress_activity</span>
          <strong>正在切换账号工作区</strong>
          <small>旧账号内容已暂时隐藏</small>
        </div>
      </div>

      <AccountStatusFeedback
        :feedback="feedback"
        @open-log="showLog"
        @retry="retry"
      />

      <AccountUnsavedChangesDialog
        :pending="application.unsavedDecision.state.pending"
        @decide="resolveUnsavedDecision"
      />
    </div>

    <AccountContextDetailPanel
      :context="detailContext"
      :open="accountDetailOpen"
      :task-state="taskProjection.state.value"
      :tasks="taskProjection.tasks.value"
      @close="accountDetailOpen = false"
    />

    <section class="account-workspace-too-narrow">
      <div>
        <span class="material-symbols-outlined">desktop_windows</span>
        <h1>请扩大应用窗口</h1>
        <p>TK-OPS 是 PC 工作台，当前窗口至少需要 960px 宽度。</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, provide } from "vue";
import { RouterView } from "vue-router";

import type { UnsavedGuardDecision } from "@/app/account-context";
import { accountUnsavedGuardRegistrarKey } from "@/modules/accounts/account-guard-port";

import AccountContextDetailPanel from "./AccountContextDetailPanel.vue";
import AccountSidebar from "./AccountSidebar.vue";
import AccountStatusFeedback from "./AccountStatusFeedback.vue";
import AccountTopBar from "./AccountTopBar.vue";
import AccountUnsavedChangesDialog from "./AccountUnsavedChangesDialog.vue";
import AccountWorkspaceEmptyState from "./AccountWorkspaceEmptyState.vue";
import LegacyRouteMigrationNotice from "./LegacyRouteMigrationNotice.vue";
import { useAccountWorkspaceShell } from "./use-account-workspace-shell";
import { useWorkspaceOverlays } from "./use-workspace-overlays";
import "./account-switcher.css";
import "./account-workspace.css";
import "./account-unsaved-dialog.css";
import "./account-workspace-overlays.css";

const {
  accountOptions,
  application,
  compact,
  currentAccount,
  currentAccountDto,
  currentContext,
  feedback,
  isAccountRoute,
  openAccountManagement,
  pageTitle,
  retry,
  runtimeLabel,
  runtimeTone,
  routeBoundContext,
  showLog,
  switchAccount,
  switchBusy,
  switcherOpen,
  systemItems,
  taskProjection,
  themeActionLabel,
  themeIcon,
  toggleTheme,
  workspaceItems
} = useAccountWorkspaceShell();
const {
  accountDetailOpen,
  dismissMigrationNotice,
  migrationMessage
} = useWorkspaceOverlays();

const contentTransitionBusy = computed(() => {
  const status = application.context.state.switchStatus;
  return status === "preparing"
    || status === "committing"
    || status === "refreshing";
});
const visibleContext = computed(() =>
  contentTransitionBusy.value ? null : routeBoundContext.value
);
const visibleAccountId = computed(
  () => visibleContext.value?.account.id ?? null
);
const detailContext = computed(() =>
  switchBusy.value ? null : currentContext.value
);

function resolveUnsavedDecision(decision: UnsavedGuardDecision): void {
  application.unsavedDecision.resolve(decision);
}

provide(accountUnsavedGuardRegistrarKey, {
  register: (guard) => application.unsavedGuards.register(guard)
});
</script>
