<template>
  <aside class="account-sidebar" :data-compact="String(compact)">
    <div class="account-sidebar__brand">
      <span class="account-sidebar__brand-mark">TK</span>
      <strong>TK-OPS</strong>
    </div>

    <nav class="account-sidebar__nav" aria-label="账号工作区">
      <RouterLink
        v-for="item in workspaceItems"
        :key="item.id"
        :to="item.path"
        class="account-sidebar__link"
        :title="item.title"
      >
        <span class="material-symbols-outlined">{{ item.icon }}</span>
        <span>{{ item.title }}</span>
      </RouterLink>
    </nav>

    <nav class="account-sidebar__system" aria-label="系统">
      <RouterLink
        v-for="item in systemItems"
        :key="item.id"
        :to="item.path"
        class="account-sidebar__link"
        :title="item.title"
      >
        <span class="material-symbols-outlined">{{ item.icon }}</span>
        <span>{{ item.title }}</span>
      </RouterLink>
    </nav>

    <AccountSwitcher
      :accounts="accounts"
      :current-account="currentAccount"
      :current-account-id="currentAccountId"
      :disabled="switchDisabled"
      :open="switcherOpen"
      @add="emit('addAccount')"
      @close="emit('closeSwitcher')"
      @manage="emit('manageAccounts')"
      @select="emit('switchAccount', $event)"
      @toggle="emit('toggleSwitcher')"
    />
  </aside>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";

import AccountSwitcher from "./AccountSwitcher.vue";
import type {
  AccountSwitcherOption,
  AccountWorkspaceNavItem
} from "./account-workspace-types";

defineProps<{
  accounts: AccountSwitcherOption[];
  compact: boolean;
  currentAccount: AccountSwitcherOption | null;
  currentAccountId: string | null;
  switchDisabled: boolean;
  switcherOpen: boolean;
  systemItems: AccountWorkspaceNavItem[];
  workspaceItems: AccountWorkspaceNavItem[];
}>();

const emit = defineEmits<{
  addAccount: [];
  closeSwitcher: [];
  manageAccounts: [];
  switchAccount: [accountId: string];
  toggleSwitcher: [];
}>();
</script>
