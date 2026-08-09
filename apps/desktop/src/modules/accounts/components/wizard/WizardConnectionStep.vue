<template>
  <div class="account-wizard-panel">
    <div class="account-wizard-panel__intro">
      <div>
        <strong>选择真实执行连接</strong>
        <p>候选必须同时匹配当前账号、设备工作区、浏览器实例和执行绑定。</p>
      </div>
      <button
        class="account-button is-secondary"
        type="button"
        :disabled="loading || busy"
        @click="$emit('reload')"
      >
        {{ loading ? "加载中…" : "刷新候选" }}
      </button>
    </div>

    <div v-if="loading && !connection" class="account-compact-state">
      <span class="account-spinner"></span>
      正在读取真实环境…
    </div>
    <div v-else-if="errorMessage" class="account-compact-state is-error">
      <span class="material-symbols-outlined">error</span>
      <span>{{ errorMessage }}</span>
      <button class="account-text-action" type="button" @click="$emit('reload')">
        重试
      </button>
    </div>
    <WizardAccountLogin
      v-else-if="connection?.executionBinding && connection.authStatus !== 'valid'"
      :account-id="accountId"
      :environment-id="connection.executionBinding.id"
      @authenticated="$emit('authenticated')"
      @cancelled="$emit('reload')"
      @open-log="$emit('openLog', $event)"
    />
    <div
      v-else-if="connection?.executionBinding && connection.authStatus === 'valid'"
      class="account-dependency-step is-ready"
    >
      <span class="material-symbols-outlined">verified</span>
      <div>
        <strong>执行环境与 TikTok 登录已就绪</strong>
        <p>当前账号已通过真实环境和公开身份探测。</p>
      </div>
      <button class="account-button is-primary" type="button" @click="$emit('authenticated')">
        继续
      </button>
    </div>
    <ExecutionEnvironmentCreator
      v-else-if="showCreator || recoverableEnvironment"
      :account-id="accountId"
      :account-name="accountName"
      :existing-environment="recoverableEnvironment"
      @close="dismissCreator"
      @created="handleCreated"
      @refresh="$emit('reload')"
      @open-log="$emit('openLog', $event)"
    />
    <div v-else-if="environments.length === 0" class="account-blocked-state">
      <span class="material-symbols-outlined">create_new_folder</span>
      <div>
        <strong>还没有执行环境</strong>
        <p>选择一个本机工作目录，系统会创建当前账号专属的浏览器执行环境。</p>
      </div>
      <button
        class="account-button is-primary"
        type="button"
        :disabled="busy"
        @click="showCreator = true"
      >
        新建执行环境
      </button>
    </div>
    <div v-else class="account-candidate-list">
      <label
        v-for="candidate in candidates"
        :key="candidate.executionBinding.id"
        :class="{ 'is-selected': selectedId === candidate.executionBinding.id }"
      >
        <input
          v-model="selectedId"
          type="radio"
          name="connection-candidate"
          :value="candidate.executionBinding.id"
          @change="$emit('dirtyChange', true)"
        />
        <span>
          <strong>{{ candidate.deviceWorkspace.name }}</strong>
          <small>
            {{ candidate.browserInstance.name }} ·
            {{ candidate.executionBinding.status }}
          </small>
        </span>
      </label>
    </div>

    <div class="account-wizard-step-actions">
      <button
        class="account-button is-primary"
        type="button"
        :disabled="busy || !selectedCandidate"
        @click="bindSelected"
      >
        {{ busy ? "正在绑定…" : "绑定并继续" }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import ExecutionEnvironmentCreator from "@/modules/execution-environments/components/ExecutionEnvironmentCreator.vue";
import type { ConnectionCandidateDto, ConnectionDto } from "@/types/runtime/accounts";
import type { ExecutionEnvironmentDto } from "@/types/runtime/execution-environments";
import WizardAccountLogin from "./WizardAccountLogin.vue";

const props = defineProps<{
  accountId: string;
  accountName: string;
  busy: boolean;
  candidates: ConnectionCandidateDto[];
  environments: ExecutionEnvironmentDto[];
  connection: ConnectionDto | null;
  errorMessage: string;
  loading: boolean;
}>();

const emit = defineEmits<{
  bind: [candidate: ConnectionCandidateDto];
  authenticated: [];
  environmentCreated: [environmentId: string];
  dirtyChange: [dirty: boolean];
  openLog: [logId: string];
  reload: [];
}>();

const selectedId = ref("");
const showCreator = ref(false);
const dismissedEnvironmentId = ref("");
const recoverableEnvironment = computed(
  () => props.environments.find(
    (item) =>
      item.recoveryActions.includes("retry_provision")
      && item.id !== dismissedEnvironmentId.value
  ) ?? null
);
const selectedCandidate = computed(
  () =>
    props.candidates.find(
      (item) => item.executionBinding.id === selectedId.value
    ) ?? null
);

function bindSelected(): void {
  if (selectedCandidate.value) emit("bind", selectedCandidate.value);
}

function handleCreated(environmentId: string): void {
  showCreator.value = false;
  emit("environmentCreated", environmentId);
}

function dismissCreator(): void {
  if (recoverableEnvironment.value) {
    dismissedEnvironmentId.value = recoverableEnvironment.value.id;
  }
  showCreator.value = false;
}

function reset(): void {
  selectedId.value = "";
  showCreator.value = false;
  dismissedEnvironmentId.value = "";
  emit("dirtyChange", false);
}

function getSelected(): ConnectionCandidateDto | null {
  return selectedCandidate.value;
}

defineExpose({ getSelected, reset });
</script>
