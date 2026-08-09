import { computed, ref, watch, type Ref } from "vue";
import { listExecutionEnvironments } from "@/app/runtime-client/execution-environments";

import type {
  AccountDto,
  AccountWizardStep,
  ConnectionCandidateDto,
  ConnectionDto
} from "@/types/runtime/accounts";
import type { ExecutionEnvironmentDto } from "@/types/runtime/execution-environments";

import {
  inferCompletedWizardSteps
} from "./account-formatters";
import { useP0AccountManagementStore } from "./account-management-store";
import {
  ACCOUNT_WIZARD_STEPS,
  type AccountDraftInput
} from "./account-management-types";

export type WizardIdentityExpose = {
  reset(): void;
  snapshot(): AccountDraftInput;
};

export type WizardConnectionExpose = {
  getSelected(): ConnectionCandidateDto | null;
  reset(): void;
};

export function useAccountCreationWizard(
  open: Ref<boolean>,
  initialAccount: Ref<AccountDto | null>,
  onCompleted: (account: AccountDto) => void
) {
  const store = useP0AccountManagementStore();
  const account = ref<AccountDto | null>(null);
  const activeStep = ref<AccountWizardStep>("identity");
  const completedSteps = ref<AccountWizardStep[]>([]);
  const candidates = ref<ConnectionCandidateDto[]>([]);
  const environments = ref<ExecutionEnvironmentDto[]>([]);
  const connection = ref<ConnectionDto | null>(null);
  const loadingCandidates = ref(false);
  const connectionError = ref("");
  const operationError = ref("");
  const operationLogId = ref<string | null>(null);
  const taskId = ref<string | null>(null);
  const dirty = ref(false);
  const identityRef = ref<WizardIdentityExpose | null>(null);
  const connectionRef = ref<WizardConnectionExpose | null>(null);

  const busy = computed(() => Boolean(store.busyKey));
  const canComplete = computed(
    () =>
      account.value?.wizardCompletedAt === null &&
      ACCOUNT_WIZARD_STEPS.every((step) => completedSteps.value.includes(step))
  );

  watch(
    open,
    (isOpen) => {
      if (isOpen) initialize(initialAccount.value);
    },
    { immediate: true }
  );

  async function createIdentity(input: AccountDraftInput): Promise<void> {
    clearError();
    try {
      account.value = await store.createDraft({
        name: input.name,
        username: input.username || null,
        platform: "tiktok"
      });
      dirty.value = false;
      syncCompleted();
      activeStep.value = "connection";
      await loadCandidates();
    } catch {
      syncError("账号草稿创建失败。");
    }
  }

  async function loadCandidates(): Promise<void> {
    if (!account.value) return;
    loadingCandidates.value = true;
    connectionError.value = "";
    try {
      const [candidateResult, environmentResult, currentConnection] = await Promise.all([
        store.loadConnectionCandidates(account.value.id),
        listExecutionEnvironments(account.value.id),
        store.loadConnection(account.value.id)
      ]);
      candidates.value = candidateResult.items;
      environments.value = environmentResult.data.items;
      connection.value = currentConnection;
    } catch {
      connectionError.value = store.error?.message ?? "候选连接加载失败。";
    } finally {
      loadingCandidates.value = false;
    }
  }

  async function bindCandidate(candidate: ConnectionCandidateDto): Promise<void> {
    if (!account.value) return;
    clearError();
    try {
      connection.value = await store.bindConnection(
        account.value,
        candidate.environmentId,
        candidate.eligibilityRevision
      );
      connectionRef.value?.reset();
      dirty.value = false;
      await refreshAccount();
      if (connection.value.authStatus === "valid") {
        activeStep.value = "positioning";
      }
    } catch {
      syncError("连接绑定失败。");
    }
  }

  async function bindCreatedEnvironment(environmentId: string): Promise<void> {
    await loadCandidates();
    const candidate = candidates.value.find(
      (item) => item.environmentId === environmentId
    );
    if (!candidate) {
      connectionError.value = "执行环境已创建，但尚未成为可绑定候选，请刷新后检查。";
      return;
    }
    await bindCandidate(candidate);
  }

  async function refreshAccount(): Promise<void> {
    if (!account.value) return;
    clearError();
    try {
      account.value = await store.refreshAccount(account.value.id);
      syncCompleted();
    } catch {
      syncError("账号状态刷新失败。");
    }
  }

  async function runHealthCheck(): Promise<void> {
    if (!account.value) return;
    clearError();
    try {
      taskId.value = await store.startHealthCheck(account.value);
    } catch {
      syncError("健康检查提交失败。");
    }
  }

  async function finishWizard(): Promise<void> {
    if (!account.value || !canComplete.value) return;
    clearError();
    try {
      account.value = await store.completeWizard(
        account.value,
        [...ACCOUNT_WIZARD_STEPS]
      );
      onCompleted(account.value);
    } catch {
      syncError("账号向导提交失败。");
    }
  }

  function initialize(initial: AccountDto | null): void {
    account.value = initial;
    dirty.value = false;
    taskId.value = null;
    candidates.value = [];
    environments.value = [];
    connection.value = null;
    clearError();
    syncCompleted();
    activeStep.value = firstIncompleteStep();
    if (activeStep.value === "connection" && account.value) void loadCandidates();
  }

  function syncCompleted(): void {
    completedSteps.value = account.value
      ? inferCompletedWizardSteps(account.value)
      : [];
  }

  function firstIncompleteStep(): AccountWizardStep {
    return (
      ACCOUNT_WIZARD_STEPS.find(
        (step) => !completedSteps.value.includes(step)
      ) ?? "health"
    );
  }

  function goNext(step: AccountWizardStep): void {
    const index = ACCOUNT_WIZARD_STEPS.indexOf(step);
    activeStep.value = ACCOUNT_WIZARD_STEPS[index + 1] ?? "health";
  }

  function openCompletedStep(step: AccountWizardStep): void {
    if (completedSteps.value.includes(step) || activeStep.value === step) {
      activeStep.value = step;
    }
  }

  async function savePending(): Promise<void> {
    if (!dirty.value) return;
    if (!account.value) {
      const snapshot = identityRef.value?.snapshot();
      if (!snapshot) throw new Error("账号身份表单尚未就绪。");
      await createIdentity(snapshot);
      if (operationError.value) throw new Error(operationError.value);
      return;
    }
    const selected = connectionRef.value?.getSelected();
    if (selected) {
      await bindCandidate(selected);
      if (operationError.value) throw new Error(operationError.value);
    }
  }

  function discardPending(): void {
    identityRef.value?.reset();
    connectionRef.value?.reset();
    dirty.value = false;
  }

  async function completeLogin(): Promise<void> {
    await refreshAccount();
    if (account.value) {
      connection.value = await store.loadConnection(account.value.id);
    }
    if (connection.value?.authStatus === "valid") {
      activeStep.value = "positioning";
    }
  }

  function clearError(): void {
    operationError.value = "";
    operationLogId.value = null;
  }

  function syncError(fallback: string): void {
    operationError.value = store.error?.message ?? fallback;
    operationLogId.value = store.error?.logId ?? null;
  }

  return {
    ACCOUNT_WIZARD_STEPS,
    account,
    activeStep,
    bindCandidate,
    bindCreatedEnvironment,
    busy,
    canComplete,
    candidates,
    environments,
    completedSteps,
    completeLogin,
    connection,
    connectionError,
    connectionRef,
    createIdentity,
    dirty,
    discardPending,
    finishWizard,
    goNext,
    identityRef,
    loadCandidates,
    loadingCandidates,
    operationError,
    operationLogId,
    openCompletedStep,
    refreshAccount,
    runHealthCheck,
    savePending,
    taskId
  };
}
