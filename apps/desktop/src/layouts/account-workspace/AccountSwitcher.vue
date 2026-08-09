<template>
  <div class="account-switcher" :data-open="String(open)">
    <Teleport to="body">
      <div
        v-if="open"
        id="account-switcher-menu"
        ref="menuRef"
        class="account-switcher__menu"
        role="dialog"
        aria-label="切换账号"
        :style="menuStyle"
      >
        <div class="account-switcher__menu-head">
          <strong>切换账号</strong>
          <button type="button" aria-label="关闭账号列表" @click="emit('close')">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <label class="account-switcher__search">
          <span class="material-symbols-outlined">search</span>
          <input ref="searchRef" v-model="query" type="search" placeholder="搜索账号" />
        </label>

        <div class="account-switcher__list">
          <button
            v-for="account in filteredAccounts"
            :key="account.id"
            class="account-switcher__option"
            :class="{ 'is-current': account.id === currentAccountId }"
            :disabled="disabled || account.status === 'archived'"
            type="button"
            @click="emit('select', account.id)"
          >
            <span class="account-switcher__avatar">
              {{ account.name.slice(0, 1).toUpperCase() }}
            </span>
            <span class="account-switcher__option-copy">
              <strong>{{ account.name }}</strong>
              <small>{{ optionSubtitle(account) }}</small>
            </span>
            <span
              v-if="account.id === currentAccountId"
              class="material-symbols-outlined"
              aria-label="当前账号"
            >
              check
            </span>
          </button>
          <p v-if="filteredAccounts.length === 0" class="account-switcher__empty">
            没有匹配账号
          </p>
        </div>

        <div class="account-switcher__menu-actions">
          <button type="button" @click="emit('add')">
            <span class="material-symbols-outlined">add</span>
            添加账号
          </button>
          <button type="button" @click="emit('manage')">
            <span class="material-symbols-outlined">settings</span>
            管理账号
          </button>
        </div>
      </div>
    </Teleport>

    <button
      ref="triggerRef"
      class="account-switcher__trigger"
      :disabled="disabled"
      type="button"
      aria-haspopup="dialog"
      aria-controls="account-switcher-menu"
      :aria-expanded="open"
      @click="emit('toggle')"
    >
      <span class="account-switcher__avatar">
        {{ currentAccount?.name.slice(0, 1).toUpperCase() || "账" }}
      </span>
      <span class="account-switcher__trigger-copy">
        <strong>{{ currentAccount?.name || "选择账号" }}</strong>
        <small>{{ triggerSubtitle }}</small>
      </span>
      <span
        class="material-symbols-outlined account-switcher__chevron"
        aria-hidden="true"
      >
        expand_less
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  ref,
  watch,
  type CSSProperties
} from "vue";

import type { AccountSwitcherOption } from "./account-workspace-types";

const props = defineProps<{
  accounts: AccountSwitcherOption[];
  currentAccount: AccountSwitcherOption | null;
  currentAccountId: string | null;
  disabled: boolean;
  open: boolean;
}>();

const emit = defineEmits<{
  add: [];
  close: [];
  manage: [];
  select: [accountId: string];
  toggle: [];
}>();

const query = ref("");
const menuRef = ref<HTMLElement | null>(null);
const searchRef = ref<HTMLInputElement | null>(null);
const triggerRef = ref<HTMLButtonElement | null>(null);
const menuStyle = ref<CSSProperties>({});
const filteredAccounts = computed(() => {
  const normalized = query.value.trim().toLocaleLowerCase();
  if (!normalized) {
    return props.accounts;
  }
  return props.accounts.filter((account) =>
    [
      account.name,
      account.username ?? "",
      account.positioningSummary ?? ""
    ]
      .join(" ")
      .toLocaleLowerCase()
      .includes(normalized)
  );
});

const triggerSubtitle = computed(() => {
  if (!props.currentAccount) {
    return "定位与内容按账号隔离";
  }
  if (props.currentAccount.username) {
    return `@${props.currentAccount.username}`;
  }
  return statusLabel(props.currentAccount.status);
});

function optionSubtitle(account: AccountSwitcherOption): string {
  if (account.status === "archived") {
    return "已归档 · 请前往管理恢复";
  }
  return (
    account.positioningSummary ||
    (account.username ? `@${account.username}` : statusLabel(account.status))
  );
}

function statusLabel(status: AccountSwitcherOption["status"]): string {
  switch (status) {
    case "draft":
      return "草稿";
    case "unbound":
      return "待连接";
    case "ready":
      return "可用";
    case "attention":
      return "需处理";
    case "archived":
      return "已归档";
  }
}

function updateMenuPosition(): void {
  const trigger = triggerRef.value;
  if (!trigger) return;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const menuWidth = Math.min(320, Math.max(0, viewportWidth - 24));
  const triggerRect = trigger.getBoundingClientRect();
  const hasGeometry = triggerRect.width > 0 && triggerRect.height > 0;
  const sidebarRect = trigger.closest<HTMLElement>(".account-sidebar")
    ?.getBoundingClientRect();
  const preferredLeft = triggerRect.width < 120
    ? (sidebarRect?.right ?? triggerRect.right) + 12
    : triggerRect.left;
  const left = hasGeometry
    ? Math.min(
        Math.max(12, preferredLeft),
        Math.max(12, viewportWidth - menuWidth - 12)
      )
    : 12;
  const bottom = hasGeometry
    ? Math.max(12, viewportHeight - triggerRect.top + 8)
    : 12;
  const maxHeight = Math.max(160, viewportHeight - bottom - 12);
  menuStyle.value = {
    left: `${left}px`,
    bottom: `${bottom}px`,
    width: `${menuWidth}px`,
    maxHeight: `${maxHeight}px`
  };
}

function handlePointerDown(event: PointerEvent): void {
  const target = event.target;
  if (!(target instanceof Node)) return;
  if (menuRef.value?.contains(target) || triggerRef.value?.contains(target)) {
    return;
  }
  emit("close");
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key !== "Escape") return;
  event.preventDefault();
  emit("close");
}

function startViewportTracking(): void {
  document.addEventListener("pointerdown", handlePointerDown);
  document.addEventListener("keydown", handleKeydown);
  window.addEventListener("resize", updateMenuPosition);
  window.addEventListener("scroll", updateMenuPosition, true);
}

function stopViewportTracking(): void {
  document.removeEventListener("pointerdown", handlePointerDown);
  document.removeEventListener("keydown", handleKeydown);
  window.removeEventListener("resize", updateMenuPosition);
  window.removeEventListener("scroll", updateMenuPosition, true);
}

watch(
  () => props.open,
  async (open, wasOpen) => {
    stopViewportTracking();
    if (open) {
      await nextTick();
      updateMenuPosition();
      startViewportTracking();
      searchRef.value?.focus();
      return;
    }
    if (wasOpen) {
      await nextTick();
      triggerRef.value?.focus();
    }
  },
  { immediate: true }
);

watch(
  () => props.disabled,
  (disabled) => {
    if (disabled && props.open) emit("close");
  }
);

onBeforeUnmount(stopViewportTracking);
</script>
