import { inject, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";

import {
  createSuggestedWorkspaceAction,
  resolveWorkspaceAction
} from "@/app/actions";
import { useAccountAIRecipeStore } from "@/modules/ai-recipes";
import type { AccountDto } from "@/types/runtime/accounts";

import { accountUnsavedGuardRegistrarKey } from "./account-guard-port";
import { useP0AccountManagementStore } from "./account-management-store";
import type {
  AccountCopyForm,
  AccountDetailTab,
  AccountListFilters,
  AccountWizardDependency
} from "./account-management-types";

export type AccountWizardExpose = {
  discardPending(): void;
  isDirty(): boolean;
  savePending(): Promise<void>;
};

export function useAccountManagementPage() {
  const router = useRouter();
  const route = useRoute();
  const store = useP0AccountManagementStore();
  const recipeStore = useAccountAIRecipeStore();
  const registrar = inject(accountUnsavedGuardRegistrarKey, null);
  const refs = storeToRefs(store);
  const filterDraft = reactive<AccountListFilters>({ q: "", status: "" });
  const detailTab = ref<AccountDetailTab>("overview");
  const wizardRef = ref<AccountWizardExpose | null>(null);
  const wizardOpen = ref(false);
  const wizardAccount = ref<AccountDto | null>(null);
  const archiveTarget = ref<AccountDto | null>(null);
  const copyTarget = ref<AccountDto | null>(null);
  const showUnsavedConfirm = ref(false);
  const pendingWizardClose = ref(false);
  const pendingAccountSelection = ref<{
    accountId: string | null;
    detailTab?: AccountDetailTab;
  } | null>(null);
  const visibleLogId = ref<string | null>(null);
  const lastRetry = ref<(() => Promise<void>) | null>(null);
  let unregisterGuard: (() => void) | null = null;

  onMounted(() => {
    void loadAccounts();
    unregisterGuard =
      registrar?.register({
        id: "account-management-wizard",
        label: "账号管理编辑器",
        isDirty: hasUnsaved,
        save: saveAllPending,
        discard: discardAllPending
      }) ?? null;
  });
  onBeforeUnmount(() => unregisterGuard?.());

  watch(
    () => route.query.action,
    async (action) => {
      const normalized = Array.isArray(action) ? action[0] : action;
      if (normalized === "add") {
        openNewWizard();
        await clearActionQuery();
        return;
      }
      if (normalized !== "continue") return;
      const requested = Array.isArray(route.query.account)
        ? route.query.account[0]
        : route.query.account;
      if (typeof requested !== "string" || !requested) return;
      try {
        const account = await store.refreshAccount(requested);
        openExistingWizard(account);
        await clearActionQuery();
      } catch {
        return;
      }
    },
    { immediate: true }
  );

  async function clearActionQuery(): Promise<void> {
    const query = { ...route.query };
    delete query.action;
    delete query.account;
    delete query.from;
    await router.replace({ query }).catch((error) => {
      console.warn("[accounts] 清理账号向导入口参数失败", error);
    });
  }

  async function loadAccounts(): Promise<void> {
    lastRetry.value = loadAccounts;
    await store.loadAccounts();
  }

  async function applyFilters(): Promise<void> {
    lastRetry.value = applyFilters;
    await store.loadAccounts({ ...filterDraft });
  }

  async function clearFilters(): Promise<void> {
    Object.assign(filterDraft, { q: "", status: "" });
    lastRetry.value = clearFilters;
    await store.loadAccounts({ q: "", status: "" });
  }

  function openNewWizard(): void {
    wizardAccount.value = null;
    wizardOpen.value = true;
  }

  function openExistingWizard(account: AccountDto): void {
    wizardAccount.value = account;
    wizardOpen.value = true;
  }

  function requestWizardClose(dirty: boolean): void {
    if (dirty) {
      pendingWizardClose.value = true;
      showUnsavedConfirm.value = true;
    }
    else wizardOpen.value = false;
  }

  async function saveAndClose(): Promise<void> {
    try {
      await saveAllPending();
      finishPendingNavigation();
    } catch {
      return;
    }
  }

  function discardAndClose(): void {
    discardAllPending();
    finishPendingNavigation();
  }

  async function handleWizardCompleted(account: AccountDto): Promise<void> {
    wizardOpen.value = false;
    store.selectAccount(account.id);
    await store.loadAccounts(store.filters);
  }

  async function handleRecommendedAction(account: AccountDto): Promise<void> {
    if (account.status === "archived") {
      await restore(account);
      return;
    }
    const action = account.readiness.suggestedAction;
    if (!action) {
      requestSelectAccount(account.id);
      return;
    }
    const resolution = resolveWorkspaceAction(
      createSuggestedWorkspaceAction(account.id, action),
      account.id
    );
    if (!resolution.ok) {
      store.fail(resolution.message, "connection", account.id, new Error(resolution.message));
      return;
    }
    switch (resolution.action.action) {
      case "open_connection":
        openExistingWizard(account);
        break;
      case "open_knowledge":
        await openDependency(account.id, "knowledge");
        break;
      case "open_ai_recipe":
        requestSelectAccount(account.id, "ai_recipe");
        break;
      case "run_health_check":
        await runHealth(account);
        break;
      case "view_log":
        if (action?.taskId) showLog(action.taskId);
        else requestSelectAccount(account.id);
        break;
      case "open_environment":
        openExistingWizard(account);
        break;
      default:
        requestSelectAccount(account.id);
    }
  }

  async function openDependency(
    accountId: string,
    dependency: AccountWizardDependency
  ): Promise<void> {
    const path =
      dependency === "ai_recipe" ? "/settings/ai-system" : "/strategy-knowledge";
    wizardOpen.value = false;
    try {
      await router.push({
        path,
        query: dependency === "ai_recipe"
          ? {
              account: accountId,
              from: "account-wizard",
              section: "ai",
              surface: "models"
            }
          : { account: accountId, from: "account-wizard" }
      });
    } catch (error) {
      console.error("[accounts] 打开账号配置依赖页面失败", error);
      store.fail("配置页面打开失败，请稍后重试。", "wizard", accountId, error);
    }
  }

  async function confirmArchive(reason: string): Promise<void> {
    const target = archiveTarget.value;
    if (!target) return;
    const archiveLatest = async () => {
      const latest = await store.refreshAccount(target.id);
      archiveTarget.value = latest;
      await store.archive(latest, reason);
      archiveTarget.value = null;
    };
    lastRetry.value = archiveLatest;
    try {
      await archiveLatest();
    } catch {
      return;
    }
  }

  async function confirmCopy(form: AccountCopyForm): Promise<void> {
    const target = copyTarget.value;
    if (!target) return;
    lastRetry.value = () => store.copyConfig(target, form);
    try {
      await store.copyConfig(target, form);
      copyTarget.value = null;
    } catch {
      return;
    }
  }

  async function restore(account: AccountDto): Promise<void> {
    const restoreLatest = async () => {
      const latest = await store.refreshAccount(account.id);
      await store.restore(latest);
    };
    lastRetry.value = restoreLatest;
    try {
      await restoreLatest();
    } catch {
      return;
    }
  }

  async function runHealth(account: AccountDto): Promise<void> {
    lastRetry.value = () =>
      store.startHealthCheck(account).then(() => undefined);
    try {
      await store.startHealthCheck(account);
    } catch {
      return;
    }
  }

  function requestSelectAccount(
    accountId: string | null,
    nextDetailTab?: AccountDetailTab
  ): void {
    if (refs.selectedAccountId.value === accountId) {
      if (nextDetailTab) detailTab.value = nextDetailTab;
      return;
    }
    const currentAccountId = refs.selectedAccountId.value;
    if (
      currentAccountId
      && recipeStore.cache(currentAccountId).dirty
    ) {
      pendingAccountSelection.value = {
        accountId,
        detailTab: nextDetailTab
      };
      showUnsavedConfirm.value = true;
      return;
    }
    store.selectAccount(accountId);
    if (nextDetailTab) detailTab.value = nextDetailTab;
  }

  async function handleRecipeUpdated(accountId: string): Promise<void> {
    lastRetry.value = () =>
      store.refreshAccount(accountId).then(() => undefined);
    try {
      await store.refreshAccount(accountId);
    } catch {
      return;
    }
  }

  function hasUnsaved(): boolean {
    const currentAccountId = refs.selectedAccountId.value;
    return Boolean(
      wizardRef.value?.isDirty()
      || (
        currentAccountId
        && recipeStore.cache(currentAccountId).dirty
      )
    );
  }

  async function saveAllPending(): Promise<void> {
    await wizardRef.value?.savePending();
    const currentAccountId = refs.selectedAccountId.value;
    if (currentAccountId) {
      await recipeStore.saveUnsaved(currentAccountId);
    }
  }

  function discardAllPending(): void {
    wizardRef.value?.discardPending();
    const currentAccountId = refs.selectedAccountId.value;
    if (currentAccountId) {
      recipeStore.discardDraft(currentAccountId);
    }
  }

  function finishPendingNavigation(): void {
    if (pendingWizardClose.value) wizardOpen.value = false;
    if (pendingAccountSelection.value) {
      store.selectAccount(pendingAccountSelection.value.accountId);
      if (pendingAccountSelection.value.detailTab) {
        detailTab.value = pendingAccountSelection.value.detailTab;
      }
    }
    pendingWizardClose.value = false;
    pendingAccountSelection.value = null;
    showUnsavedConfirm.value = false;
  }

  function cancelUnsavedConfirm(): void {
    pendingWizardClose.value = false;
    pendingAccountSelection.value = null;
    showUnsavedConfirm.value = false;
  }

  function showLog(logId: string): void {
    visibleLogId.value = logId;
  }

  async function retryLast(): Promise<void> {
    try {
      await lastRetry.value?.();
    } catch {
      return;
    }
  }

  return {
    ...refs,
    applyFilters,
    archiveTarget,
    cancelUnsavedConfirm,
    clearFilters,
    confirmArchive,
    confirmCopy,
    copyTarget,
    detailTab,
    discardAndClose,
    filterDraft,
    handleRecommendedAction,
    handleRecipeUpdated,
    handleWizardCompleted,
    lastRetry,
    loadAccounts,
    openArchive: (account: AccountDto) => (archiveTarget.value = account),
    openCopy: (account: AccountDto) => (copyTarget.value = account),
    openDependency,
    openNewWizard,
    requestWizardClose,
    requestSelectAccount,
    restore,
    retryLast,
    runHealth,
    saveAndClose,
    showLog,
    showUnsavedConfirm,
    store,
    visibleLogId,
    wizardAccount,
    wizardOpen,
    wizardRef
  };
}
