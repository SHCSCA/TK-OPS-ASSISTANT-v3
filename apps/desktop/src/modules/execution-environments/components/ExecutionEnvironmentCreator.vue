<template>
  <section class="execution-environment-creator" aria-label="新建执行环境">
    <header>
      <div>
        <strong>{{ currentEnvironment ? "恢复执行环境" : "新建执行环境" }}</strong>
        <p v-if="currentEnvironment">沿用原工作目录、浏览器实例和任务上下文重试。</p>
        <p v-else>选择本机工作目录后，TK-OPS 会创建账号专属目录和浏览器实例。</p>
      </div>
      <button
        class="account-icon-button"
        type="button"
        aria-label="关闭新建执行环境"
        :disabled="working"
        @click="$emit('close')"
      >
        <span class="material-symbols-outlined">close</span>
      </button>
    </header>

    <label class="execution-environment-creator__field">
      <span>环境名称</span>
      <input
        v-model.trim="name"
        maxlength="128"
        :disabled="working || Boolean(currentEnvironment)"
        placeholder="例如：主执行环境"
      />
    </label>

    <div class="execution-environment-creator__directory">
      <div>
        <span>工作目录</span>
        <strong>{{ selectedRoot?.displayPath || "尚未选择" }}</strong>
        <small v-if="selectedRoot">仅当前账号可使用此目录</small>
      </div>
      <button
        class="account-button is-secondary"
        type="button"
        :disabled="working || Boolean(currentEnvironment)"
        @click="selectDirectory"
      >
        {{ selectedRoot ? "更换目录" : "选择目录" }}
      </button>
    </div>

    <div v-if="statusMessage" class="account-compact-state" aria-live="polite">
      <span v-if="working" class="account-spinner"></span>
      <span v-else class="material-symbols-outlined">info</span>
      <span>{{ statusMessage }}</span>
    </div>
    <div v-if="errorMessage" class="account-compact-state is-error" role="alert">
      <span class="material-symbols-outlined">error</span>
      <span>{{ errorMessage }}</span>
      <button
        v-if="errorLogId"
        class="account-text-action"
        type="button"
        @click="$emit('openLog', errorLogId)"
      >
        查看日志
      </button>
    </div>

    <footer>
      <button
        v-if="taskId && working"
        class="account-button is-secondary"
        type="button"
        @click="cancelCreation"
      >
        取消创建
      </button>
      <button
        class="account-button is-primary"
        type="button"
        :disabled="!canCreate"
        @click="submitEnvironment"
      >
        {{ working ? "正在处理…" : currentEnvironment ? "重试创建" : "创建执行环境" }}
      </button>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import {
  createExecutionEnvironment,
  getExecutionEnvironment,
  retryExecutionEnvironment
} from "@/app/runtime-client/execution-environments";
import { waitForAccountTask } from "@/app/runtime-client/task-polling";
import { cancelAccountTask } from "@/app/runtime-client/tasks";
import {
  pickAccountWorkspaceRoot,
  WorkspaceRootBridgeError,
  type AccountWorkspaceRoot
} from "@/app/workspace-roots";
import { RuntimeError } from "@/app/runtime-client/core";
import { createOperationKey } from "@/modules/accounts/account-errors";
import type { ExecutionEnvironmentDto } from "@/types/runtime/execution-environments";

const props = defineProps<{
  accountId: string;
  accountName: string;
  existingEnvironment?: ExecutionEnvironmentDto | null;
}>();
const emit = defineEmits<{
  close: [];
  created: [environmentId: string];
  openLog: [logId: string];
  refresh: [];
}>();

const name = ref("主执行环境");
const selectedRoot = ref<AccountWorkspaceRoot | null>(null);
const working = ref(false);
const statusMessage = ref("");
const errorMessage = ref("");
const errorLogId = ref<string | null>(null);
const taskId = ref<string | null>(null);
const environmentId = ref<string | null>(null);
const currentEnvironment = ref<ExecutionEnvironmentDto | null>(null);
const pollController = ref<AbortController | null>(null);

const canCreate = computed(
  () => Boolean(
    !working.value
    && (
      currentEnvironment.value?.recoveryActions.includes("retry_provision")
      || (name.value.trim() && selectedRoot.value)
    )
  )
);

watch(
  () => props.existingEnvironment,
  (environment) => {
    currentEnvironment.value = environment ?? null;
    environmentId.value = environment?.id ?? null;
    taskId.value = environment?.lastTaskId ?? null;
    if (environment) {
      name.value = environment.name;
      selectedRoot.value = {
        displayName: environment.workspace.displayName,
        rootRef: environment.workspace.rootRef,
        displayPath: environment.workspace.displayName,
        revision: environment.revision,
        status: "active"
      };
      errorMessage.value = environment.errorMessage ?? "执行环境创建失败，可以沿用原上下文重试。";
      errorLogId.value = environment.errorLogId;
    }
  },
  { immediate: true }
);

onBeforeUnmount(() => pollController.value?.abort());

async function selectDirectory(): Promise<void> {
  clearError();
  try {
    selectedRoot.value = await pickAccountWorkspaceRoot(
      props.accountId,
      props.accountName
    );
  } catch (error) {
    setError(error, "工作目录选择失败，请重试。");
  }
}

async function submitEnvironment(): Promise<void> {
  if (currentEnvironment.value) {
    await retryEnvironment();
    return;
  }
  await createEnvironment();
}

async function createEnvironment(): Promise<void> {
  const root = selectedRoot.value;
  if (!root || !name.value.trim()) return;
  clearError();
  working.value = true;
  statusMessage.value = "正在提交执行环境创建任务…";
  try {
    const result = await createExecutionEnvironment(
      props.accountId,
      {
        activateWhenReady: false,
        browser: { kind: "chrome", selection: "auto" },
        name: name.value.trim(),
        rootRef: root.rootRef
      },
      { idempotencyKey: createOperationKey("environment-create", props.accountId) }
    );
    taskId.value = result.data.taskId;
    environmentId.value = result.data.environmentId;
    statusMessage.value = "正在创建目录并启动受控浏览器…";
    const controller = new AbortController();
    pollController.value = controller;
    await waitForAccountTask(props.accountId, result.data.taskId, {
      signal: controller.signal,
      timeoutMs: 125_000,
      failureMessage: "执行环境创建失败。"
    });
    statusMessage.value = "执行环境已创建，可继续绑定账号。";
    emit("created", result.data.environmentId);
  } catch (error) {
    if (!pollController.value?.signal.aborted) {
      setError(error, "执行环境创建失败，请根据提示重试。");
      await refreshCurrentEnvironment();
    }
  } finally {
    working.value = false;
    pollController.value = null;
  }
}

async function retryEnvironment(): Promise<void> {
  const environment = currentEnvironment.value;
  if (!environment) return;
  clearError();
  working.value = true;
  statusMessage.value = "正在沿用原执行环境重试…";
  try {
    const result = await retryExecutionEnvironment(
      props.accountId,
      environment.id,
      environment.revision,
      { idempotencyKey: createOperationKey("environment-retry", environment.id) }
    );
    taskId.value = result.data.taskId;
    const controller = new AbortController();
    pollController.value = controller;
    await waitForAccountTask(props.accountId, result.data.taskId, {
      signal: controller.signal,
      timeoutMs: 125_000,
      failureMessage: "执行环境恢复失败。"
    });
    statusMessage.value = "执行环境已恢复，可继续绑定账号。";
    emit("created", environment.id);
  } catch (error) {
    if (!pollController.value?.signal.aborted) {
      setError(error, "执行环境恢复失败，请查看日志后重试。");
      await refreshCurrentEnvironment();
    }
  } finally {
    working.value = false;
    pollController.value = null;
  }
}

async function refreshCurrentEnvironment(): Promise<void> {
  const currentId = environmentId.value;
  if (!currentId) return;
  try {
    const result = await getExecutionEnvironment(props.accountId, currentId);
    currentEnvironment.value = result.data;
    taskId.value = result.data.lastTaskId;
    errorLogId.value = result.data.errorLogId ?? errorLogId.value;
    emit("refresh");
  } catch (error) {
    setError(error, "执行环境状态刷新失败，请稍后重试。");
  }
}

async function cancelCreation(): Promise<void> {
  const currentTaskId = taskId.value;
  if (!currentTaskId) return;
  try {
    await cancelAccountTask(props.accountId, currentTaskId, {
      idempotencyKey: createOperationKey("environment-cancel", props.accountId)
    });
    pollController.value?.abort();
    statusMessage.value = "创建任务已取消。";
  } catch (error) {
    setError(error, "取消任务失败，请稍后重试。");
  } finally {
    working.value = false;
  }
}

function clearError(): void {
  errorMessage.value = "";
  errorLogId.value = null;
}

function setError(error: unknown, fallback: string): void {
  errorMessage.value = error instanceof Error && error.message ? error.message : fallback;
  errorLogId.value =
    error instanceof RuntimeError || error instanceof WorkspaceRootBridgeError
      ? error.logId
      : null;
}
</script>

<style src="../styles/execution-environment-creator.css"></style>
