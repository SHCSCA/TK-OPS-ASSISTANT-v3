<template>
  <section class="account-login-step" aria-label="TikTok 监督登录">
    <div class="account-login-step__icon">
      <span class="material-symbols-outlined">login</span>
    </div>
    <div class="account-login-step__content">
      <strong>{{ title }}</strong>
      <p>{{ description }}</p>

      <div v-if="errorMessage" class="account-compact-state is-error" role="alert">
        <span class="material-symbols-outlined">error</span>
        <span>{{ errorMessage }}</span>
        <button
          v-if="loginSession?.errorLogId"
          class="account-text-action"
          type="button"
          @click="$emit('openLog', loginSession.errorLogId)"
        >
          查看日志
        </button>
      </div>

      <div
        v-if="loginSession?.detectedIdentity && loginSession.errorCode === 'ACCOUNT_PLATFORM_IDENTITY_MISMATCH'"
        class="account-login-step__identity"
      >
        <span>目标：@{{ loginSession.expectedIdentity || "未指定" }}</span>
        <span>检测到：@{{ loginSession.detectedIdentity }}</span>
      </div>

      <div class="account-wizard-step-actions">
        <button
          v-if="canStartLogin"
          class="account-button is-primary"
          type="button"
          @click="startLogin"
        >
          {{ startActionLabel }}
        </button>
        <template v-else-if="state === 'waiting_user'">
          <button class="account-button is-secondary" type="button" @click="cancelLogin">
            取消登录
          </button>
          <button class="account-button is-primary" type="button" @click="confirmLogin">
            我已完成登录
          </button>
        </template>
        <button
          v-else-if="state === 'preparing' || state === 'probing'"
          class="account-button is-secondary"
          type="button"
          @click="cancelLogin"
        >
          取消
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";

import {
  cancelAccountLoginSession,
  createAccountLoginSession,
  getAccountLoginSession,
  probeAccountLoginSession
} from "@/app/runtime-client/account-login-sessions";
import { waitForAccountTask } from "@/app/runtime-client/task-polling";
import { cancelAccountTask } from "@/app/runtime-client/tasks";
import { RuntimeError } from "@/app/runtime-client/core";
import { createOperationKey } from "@/modules/accounts/account-errors";
import type {
  LoginSessionDto,
  LoginSessionState
} from "@/types/runtime/account-login-sessions";

const props = defineProps<{
  accountId: string;
  environmentId: string;
}>();
const emit = defineEmits<{
  authenticated: [identity: string];
  cancelled: [];
  openLog: [logId: string];
}>();

const state = ref<LoginSessionState | "idle" | "error">("idle");
const loginSession = ref<LoginSessionDto | null>(null);
const errorMessage = ref("");
const controller = ref<AbortController | null>(null);
const activeSessionId = ref<string | null>(null);
const activeTaskId = ref<string | null>(null);
const canStartLogin = computed(
  () => ["idle", "error", "cancelled", "failed", "timed_out"].includes(state.value)
);
const startActionLabel = computed(
  () => state.value === "idle" ? "打开浏览器登录" : "重新开始登录"
);

const title = computed(() => ({
  idle: "登录 TikTok",
  preparing: "正在打开受控浏览器",
  waiting_user: "请在浏览器中自行登录",
  probing: "正在确认登录身份",
  completed: "TikTok 登录已确认",
  cancelled: "登录已取消",
  failed: "登录失败",
  timed_out: "登录已超时",
  error: "登录需要处理"
}[state.value]));
const description = computed(() => {
  if (state.value === "waiting_user") {
    return "系统不会读取密码或绕过验证码。登录完成后回到这里确认。";
  }
  if (state.value === "probing" || state.value === "preparing") {
    return "正在使用当前账号的受控浏览器执行本机任务，请稍候。";
  }
  return "登录只在可见浏览器中由你完成，系统仅探测公开账号身份。";
});

onBeforeUnmount(() => controller.value?.abort());

async function startLogin(): Promise<void> {
  clearError();
  state.value = "preparing";
  try {
    const accepted = await createAccountLoginSession(
      props.accountId,
      props.environmentId,
      { idempotencyKey: createOperationKey("account-login", props.accountId) }
    );
    activeSessionId.value = accepted.data.sessionId;
    activeTaskId.value = accepted.data.taskId;
    await refreshSession(accepted.data.sessionId);
    controller.value = new AbortController();
    await waitForAccountTask(props.accountId, accepted.data.taskId, {
      signal: controller.value.signal,
      timeoutMs: 35_000
    });
    await refreshSession(accepted.data.sessionId);
  } catch (error) {
    handleError(error, "无法打开登录浏览器，请检查执行环境后重试。");
  }
}

async function confirmLogin(): Promise<void> {
  const current = loginSession.value;
  if (!current) return;
  clearError();
  state.value = "probing";
  try {
    const accepted = await probeAccountLoginSession(
      props.accountId,
      current.id,
      current.revision,
      { idempotencyKey: createOperationKey("account-login-probe", props.accountId) }
    );
    activeSessionId.value = accepted.data.sessionId;
    activeTaskId.value = accepted.data.taskId;
    controller.value = new AbortController();
    await waitForAccountTask(props.accountId, accepted.data.taskId, {
      signal: controller.value.signal,
      timeoutMs: 25_000
    });
    await refreshSession(current.id);
    if (loginSession.value?.state === "completed") {
      emit("authenticated", loginSession.value.detectedIdentity ?? "");
    }
  } catch (error) {
    await refreshSession(current.id).catch(() => undefined);
    handleError(error, "登录状态确认失败，请返回浏览器检查后重试。");
  }
}

async function cancelLogin(): Promise<void> {
  controller.value?.abort();
  const sessionId = loginSession.value?.id ?? activeSessionId.value;
  if (!sessionId) {
    handleError(new Error("登录会话尚未建立，请稍后重试。"), "取消登录失败。");
    return;
  }
  try {
    const result = await cancelAccountLoginSession(
      props.accountId,
      sessionId,
      { idempotencyKey: createOperationKey("account-login-cancel", sessionId) }
    );
    loginSession.value = result.data;
    const taskIds = new Set([
      activeTaskId.value,
      result.data.prepareTaskId,
      result.data.probeTaskId
    ].filter((value): value is string => Boolean(value)));
    for (const taskId of taskIds) {
      await cancelAccountTask(props.accountId, taskId, {
        idempotencyKey: createOperationKey("account-login-task-cancel", taskId)
      });
    }
    await refreshSession(sessionId);
    if (loginSession.value?.state === "completed") {
      emit("authenticated", loginSession.value.detectedIdentity ?? "");
      return;
    }
    if (loginSession.value?.state !== "cancelled") {
      throw new Error("Runtime 尚未确认登录取消，请重试。");
    }
    activeTaskId.value = null;
    state.value = "cancelled";
    emit("cancelled");
  } catch (error) {
    await refreshSession(sessionId).catch(() => undefined);
    handleError(error, "取消登录未完成，请保留当前页面并重试。");
  }
}

async function refreshSession(sessionId: string): Promise<void> {
  const result = await getAccountLoginSession(props.accountId, sessionId);
  loginSession.value = result.data;
  state.value = result.data.state;
  if (result.data.errorCode) {
    errorMessage.value = errorText(result.data.errorCode);
  }
}

function clearError(): void {
  errorMessage.value = "";
}

function handleError(error: unknown, fallback: string): void {
  state.value = "error";
  errorMessage.value = error instanceof Error && error.message ? error.message : fallback;
}

function errorText(errorCode: string): string {
  if (errorCode === "ACCOUNT_PLATFORM_IDENTITY_MISMATCH") {
    return "登录的账号与当前 TK-OPS 账号不一致，请在浏览器切换后重试。";
  }
  if (errorCode === "ACCOUNT_PLATFORM_AUTH_REQUIRED") {
    return "尚未检测到登录，请在浏览器完成登录后重试。";
  }
  return "登录状态需要处理，请根据提示重试。";
}
</script>
