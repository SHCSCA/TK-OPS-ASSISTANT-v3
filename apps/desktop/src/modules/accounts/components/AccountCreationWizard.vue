<template>
  <div v-if="open" class="account-modal-backdrop" @click.self="requestClose">
    <section class="account-wizard" role="dialog" aria-modal="true" aria-label="添加账号">
      <header class="account-wizard__header">
        <div>
          <span class="account-eyebrow">TikTok 账号</span>
          <h2>{{ account ? account.name : "添加账号" }}</h2>
        </div>
        <button
          class="account-icon-button"
          type="button"
          aria-label="关闭添加账号向导"
          @click="requestClose"
        >
          <span class="material-symbols-outlined">close</span>
        </button>
      </header>

      <ol class="account-wizard__steps">
        <li
          v-for="(step, index) in ACCOUNT_WIZARD_STEPS"
          :key="step"
          :class="{
            'is-active': activeStep === step,
            'is-complete': completedSteps.includes(step)
          }"
        >
          <button
            type="button"
            :disabled="!completedSteps.includes(step) && activeStep !== step"
            @click="openCompletedStep(step)"
          >
            <span>{{ completedSteps.includes(step) ? "✓" : index + 1 }}</span>
            {{ wizardStepLabel(step) }}
          </button>
        </li>
      </ol>

      <div v-if="operationError" class="account-inline-feedback is-error">
        <span class="material-symbols-outlined">error</span>
        <span>{{ operationError }}</span>
        <button
          v-if="operationLogId"
          class="account-text-action"
          type="button"
          @click="openOperationLog"
        >
          查看日志
        </button>
      </div>

      <main class="account-wizard__body">
        <WizardIdentityStep
          v-if="activeStep === 'identity' && !account"
          ref="identityRef"
          :busy="busy"
          @dirty-change="dirty = $event"
          @submit="createIdentity"
        />

        <WizardConnectionStep
          v-else-if="activeStep === 'connection' && account"
          ref="connectionRef"
          :account-id="account.id"
          :account-name="account.name"
          :busy="busy"
          :candidates="candidates"
          :environments="environments"
          :connection="connection"
          :error-message="connectionError"
          :loading="loadingCandidates"
          @bind="bindCandidate"
          @authenticated="completeLogin"
          @environment-created="bindCreatedEnvironment"
          @dirty-change="dirty = $event"
          @open-log="$emit('openLog', $event)"
          @reload="loadCandidates"
        />

        <WizardDependencyStep
          v-else-if="activeStep === 'positioning' && account"
          action-label="前往定位设置"
          description="定位必须保存为当前账号的真实版本，返回后刷新即可继续。"
          icon="target"
          :ready="completedSteps.includes('positioning')"
          ready-description="已读取到当前账号的定位摘要。"
          ready-title="账号定位已保存"
          title="完成账号定位"
          @continue="goNext('positioning')"
          @open-dependency="$emit('openDependency', account.id, 'positioning')"
        />

        <WizardDependencyStep
          v-else-if="activeStep === 'knowledge' && account"
          action-label="前往知识库"
          description="添加真实来源并完成索引后，知识就绪状态才会通过。"
          icon="library_books"
          :ready="completedSteps.includes('knowledge')"
          ready-description="Runtime 已确认账号知识可用。"
          ready-title="账号知识已就绪"
          title="建立账号知识"
          @continue="goNext('knowledge')"
          @open-dependency="$emit('openDependency', account.id, 'knowledge')"
        />

        <AccountAIRecipePanel
          v-else-if="activeStep === 'ai_recipe' && account"
          :account-id="account.id"
          mode="wizard"
          :restricted="account.status === 'archived'"
          @activated="handleRecipeActivated"
          @open-log="$emit('openLog', $event)"
        />

        <WizardHealthStep
          v-else-if="activeStep === 'health' && account"
          :account="account"
          :busy="busy"
          :task-id="taskId"
          @check="runHealthCheck"
          @refresh="refreshAccount"
        />
      </main>

      <footer class="account-wizard__footer">
        <span>
          已完成 {{ completedSteps.length }} / {{ ACCOUNT_WIZARD_STEPS.length }}
        </span>
        <button
          v-if="canComplete"
          class="account-button is-primary"
          type="button"
          :disabled="busy"
          @click="finishWizard"
        >
          完成向导
        </button>
        <button
          v-else-if="account && activeStep !== 'health'"
          class="account-button is-secondary"
          type="button"
          :disabled="busy"
          @click="refreshAccount"
        >
          刷新依赖状态
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { toRef } from "vue";

import type { AccountDto } from "@/types/runtime/accounts";
import AccountAIRecipePanel from "@/modules/ai-recipes/components/AccountAIRecipePanel.vue";
import { useAccountAIRecipeStore } from "@/modules/ai-recipes";

import { wizardStepLabel } from "../account-formatters";
import {
  type AccountWizardDependency
} from "../account-management-types";
import { useAccountCreationWizard } from "../use-account-creation-wizard";
import WizardConnectionStep from "./wizard/WizardConnectionStep.vue";
import WizardDependencyStep from "./wizard/WizardDependencyStep.vue";
import WizardHealthStep from "./wizard/WizardHealthStep.vue";
import WizardIdentityStep from "./wizard/WizardIdentityStep.vue";

const props = defineProps<{
  initialAccount: AccountDto | null;
  open: boolean;
}>();
const emit = defineEmits<{
  completed: [account: AccountDto];
  openDependency: [accountId: string, dependency: AccountWizardDependency];
  openLog: [logId: string];
  requestClose: [dirty: boolean];
}>();
const recipeStore = useAccountAIRecipeStore();

const wizard = useAccountCreationWizard(
  toRef(props, "open"),
  toRef(props, "initialAccount"),
  (account) => emit("completed", account)
);
const {
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
} = wizard;

function requestClose(): void {
  emit("requestClose", hasUnsaved());
}

function openOperationLog(): void {
  if (operationLogId.value) emit("openLog", operationLogId.value);
}

function hasUnsaved(): boolean {
  return dirty.value || Boolean(
    account.value && recipeStore.cache(account.value.id).dirty
  );
}

async function saveAllPending(): Promise<void> {
  await savePending();
  if (account.value) {
    await recipeStore.saveUnsaved(account.value.id);
  }
}

function discardAllPending(): void {
  discardPending();
  if (account.value) {
    recipeStore.discardDraft(account.value.id);
  }
}

async function handleRecipeActivated(): Promise<void> {
  await refreshAccount();
  if (completedSteps.value.includes("ai_recipe")) {
    goNext("ai_recipe");
  }
}

defineExpose({
  discardPending: discardAllPending,
  isDirty: hasUnsaved,
  savePending: saveAllPending
});
</script>
