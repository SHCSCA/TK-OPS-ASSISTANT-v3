import {
  computed,
  onBeforeUnmount,
  reactive,
  ref,
  watch,
  type Ref
} from "vue";

import {
  createModelProfile,
  createProviderProfile,
  startProviderCheck,
  startProviderModelDiscovery,
  updateProviderCredential
} from "@/app/runtime-client/ai-system";
import { cancelSystemTask, getSystemTask } from "@/app/runtime-client/tasks";
import type { ProviderDto } from "@/types/runtime/ai-system";
import type { RuntimeTaskDto, TaskAcceptedDto } from "@/types/runtime/tasks";

import {
  createAIOperationKey,
  logAIConfigError,
  toAIConfigUiError
} from "./ai-config-helpers";
import type {
  AIConfigUiError,
  ProviderWizardDraft,
  ProviderWizardStep
} from "./ai-config-types";

const STEPS: ProviderWizardStep[] = [
  "connection",
  "credential",
  "network",
  "models",
  "verify"
];

export function useProviderWizard(
  open: Ref<boolean>,
  onSaved: (provider: ProviderDto) => void
) {
  const step = ref<ProviderWizardStep>("connection");
  const draft = reactive<ProviderWizardDraft>(emptyDraft());
  const savedProvider = ref<ProviderDto | null>(null);
  const task = ref<TaskAcceptedDto | RuntimeTaskDto | null>(null);
  const error = ref<AIConfigUiError | null>(null);
  const submitting = ref(false);
  const submitted = ref(false);
  const pendingDiscovery = ref(false);

  const stepIndex = computed(() => STEPS.indexOf(step.value));
  const canGoBack = computed(() => stepIndex.value > 0 && !submitted.value);
  const canGoNext = computed(() => validateCurrentStep() === null);

  watch(open, (isOpen) => {
    if (isOpen) reset();
    else clearSensitiveDraft();
  });
  onBeforeUnmount(clearSensitiveDraft);

  function next(): void {
    const validation = validateCurrentStep();
    if (validation) {
      error.value = validation;
      return;
    }
    step.value = STEPS[stepIndex.value + 1] ?? "verify";
    error.value = null;
  }

  function back(): void {
    step.value = STEPS[Math.max(0, stepIndex.value - 1)];
    error.value = null;
  }

  async function submit(): Promise<void> {
    if (submitting.value || submitted.value) return;
    submitting.value = true;
    error.value = null;
    let provider: ProviderDto | null = null;
    try {
      const createdProvider = (
        await createProviderProfile(
          {
            name: draft.name.trim(),
            adapterType: draft.adapterType,
            baseUrl: draft.baseUrl.trim(),
            region: draft.region.trim() || null,
            timeoutMs: draft.timeoutMs,
            maxConcurrency: draft.maxConcurrency,
            enabled: false
          },
          { idempotencyKey: createAIOperationKey("provider-create") }
        )
      ).data;
      provider = createdProvider;
      let currentProvider = createdProvider;
      savedProvider.value = currentProvider;

      const credential = draft.credential;
      if (credential) {
        const summary = await updateProviderCredential(
          currentProvider.id,
          { credential },
          { expectedRevision: currentProvider.revision }
        );
        currentProvider = {
          ...currentProvider,
          credentialSummary: {
            configured: true,
            maskedValue: summary.data.maskedValue
          },
          revision: summary.data.providerRevision
        };
        provider = currentProvider;
        savedProvider.value = currentProvider;
      }
      clearSensitiveDraft();

      if (draft.modelMode === "manual") {
        await createModelProfile(
          {
            providerProfileId: currentProvider.id,
            modelId: draft.modelId.trim(),
            displayName: draft.modelDisplayName.trim(),
            enabled: true
          },
          {
            idempotencyKey: createAIOperationKey(
              "model-create",
              currentProvider.id
            )
          }
        );
      }

      task.value = (
        await startProviderCheck(
          currentProvider.id,
          { force: true },
          {
            idempotencyKey: createAIOperationKey(
              "provider-check",
              currentProvider.id
            )
          }
        )
      ).data;
      pendingDiscovery.value = draft.modelMode === "discover";
      submitted.value = true;
      onSaved(currentProvider);
    } catch (cause) {
      clearSensitiveDraft();
      logAIConfigError("Provider 向导保存失败", cause);
      error.value = toAIConfigUiError(
        cause,
        provider
          ? "Provider 已安全保存为禁用配置，但后续验证未完成。"
          : "Provider 保存失败，请修复后重试。"
      );
      if (provider) {
        submitted.value = true;
        onSaved(provider);
      }
    } finally {
      submitting.value = false;
    }
  }

  async function refreshTask(): Promise<void> {
    if (!task.value) return;
    try {
      const refreshed = (await getSystemTask(task.value.taskId)).data;
      task.value = refreshed;
      if (!pendingDiscovery.value) return;
      if (
        refreshed.status !== "completed"
        || refreshed.completionKind !== "succeeded"
      ) {
        if (refreshed.status === "failed" || refreshed.status === "completed") {
          pendingDiscovery.value = false;
          error.value = {
            message: "Provider 连接检查未成功，已停止后续模型发现。",
            errorCode: refreshed.errorCode,
            logId: refreshed.logId,
            requestId: null,
            retryable: true
          };
        }
        return;
      }
      const provider = savedProvider.value;
      pendingDiscovery.value = false;
      if (!provider) {
        error.value = {
          message: "Provider 摘要已失效，请关闭向导后重新发现模型。",
          errorCode: "PROVIDER_NOT_FOUND",
          logId: null,
          requestId: null,
          retryable: true
        };
        return;
      }
      task.value = (
        await startProviderModelDiscovery(
          provider.id,
          { replaceMissing: false },
          {
            idempotencyKey: createAIOperationKey(
              "model-discovery",
              provider.id
            )
          }
        )
      ).data;
    } catch (cause) {
      logAIConfigError("刷新 Provider 向导任务失败", cause);
      error.value = toAIConfigUiError(cause, "任务状态读取失败。");
    }
  }

  async function cancelTask(): Promise<void> {
    if (!task.value?.cancellable) return;
    try {
      task.value = (
        await cancelSystemTask(task.value.taskId, {
          idempotencyKey: createAIOperationKey(
            "provider-wizard-cancel",
            task.value.taskId
          )
        })
      ).data;
    } catch (cause) {
      logAIConfigError("取消 Provider 向导任务失败", cause);
      error.value = toAIConfigUiError(cause, "任务取消失败。");
    }
  }

  function reset(): void {
    clearSensitiveDraft();
    Object.assign(draft, emptyDraft());
    step.value = "connection";
    savedProvider.value = null;
    task.value = null;
    error.value = null;
    submitting.value = false;
    submitted.value = false;
    pendingDiscovery.value = false;
  }

  function clearSensitiveDraft(): void {
    draft.credential = "";
  }

  function validateCurrentStep(): AIConfigUiError | null {
    let message = "";
    if (step.value === "connection" && !draft.name.trim()) {
      message = "请输入 Provider 名称。";
    } else if (step.value === "credential" && !draft.baseUrl.trim()) {
      message = "请输入受控 http 或 https 地址。";
    } else if (
      step.value === "network"
      && (
        !Number.isInteger(draft.timeoutMs)
        || draft.timeoutMs < 1_000
        || !Number.isInteger(draft.maxConcurrency)
        || draft.maxConcurrency < 1
      )
    ) {
      message = "超时与并发必须填写有效正整数。";
    } else if (
      step.value === "models"
      && draft.modelMode === "manual"
      && (!draft.modelId.trim() || !draft.modelDisplayName.trim())
    ) {
      message = "手动录入模型时必须填写模型 ID 和显示名。";
    }
    return message
      ? {
          message,
          errorCode: "REQUEST_VALIDATION_FAILED",
          logId: null,
          requestId: null,
          retryable: false
        }
      : null;
  }

  return {
    STEPS,
    back,
    canGoBack,
    canGoNext,
    cancelTask,
    draft,
    error,
    next,
    pendingDiscovery,
    refreshTask,
    reset,
    savedProvider,
    step,
    stepIndex,
    submit,
    submitted,
    submitting,
    task
  };
}

function emptyDraft(): ProviderWizardDraft {
  return {
    name: "",
    adapterType: "direct_api",
    baseUrl: "",
    credential: "",
    region: "",
    timeoutMs: 30_000,
    maxConcurrency: 2,
    modelMode: "discover",
    modelId: "",
    modelDisplayName: ""
  };
}
