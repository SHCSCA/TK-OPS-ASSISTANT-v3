<template>
  <section class="ai-workspace" aria-labelledby="provider-heading">
    <header class="ai-workspace-header">
      <div>
        <span class="ai-eyebrow">系统连接</span>
        <h2 id="provider-heading">Provider</h2>
        <p>连接、凭据引用与健康状态由 Runtime 统一管理。</p>
      </div>
      <button class="ai-button is-primary" type="button" @click="wizardOpen = true">
        <span class="material-symbols-outlined">add</span>
        添加 Provider
      </button>
    </header>

    <div class="ai-toolbar">
      <label class="ai-search">
        <span class="material-symbols-outlined">search</span>
        <input
          v-model="store.search"
          type="search"
          placeholder="搜索名称或地址"
          @input="store.recomputeState"
        />
      </label>
      <select v-model="store.healthFilter" @change="store.recomputeState">
        <option value="">全部健康状态</option>
        <option value="unknown">未检查</option>
        <option value="checking">检查中</option>
        <option value="ready">就绪</option>
        <option value="degraded">降级</option>
        <option value="failed">失败</option>
      </select>
      <button
        v-if="store.hasFilters"
        class="ai-button is-quiet"
        type="button"
        @click="store.clearFilters"
      >
        清除
      </button>
      <button class="ai-button is-quiet" type="button" @click="store.load">
        刷新
      </button>
    </div>

    <AISystemTaskBanner
      :task="store.task"
      task-label="Provider 外部任务"
      @cancel="store.cancelTask"
      @open-log="$emit('openLog', $event)"
      @refresh="store.refreshTask"
    />

    <div v-if="store.feedback" class="ai-inline-feedback is-success">
      <span class="material-symbols-outlined">info</span>
      <span>{{ store.feedback }}</span>
      <button class="ai-icon-button" type="button" @click="store.clearFeedback">
        <span class="material-symbols-outlined">close</span>
      </button>
    </div>

    <AIConfigStatePanel
      v-if="showState"
      :action-label="store.state === 'first_use' ? '添加 Provider' : ''"
      :error-message="store.error?.message"
      :log-id="store.error?.logId"
      :state="store.state"
      @action="wizardOpen = true"
      @clear-filters="store.clearFilters"
      @open-log="$emit('openLog', $event)"
      @retry="store.load"
    />

    <div v-else class="ai-table-detail-layout">
      <div class="ai-table-wrap">
        <table class="ai-data-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>适配方式</th>
              <th>健康</th>
              <th>能力类型</th>
              <th>模型</th>
              <th><span class="sr-only">动作</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="provider in store.filteredProviders"
              :key="provider.id"
              :class="{ 'is-selected': provider.id === store.selectedProviderId }"
            >
              <td>
                <strong>{{ provider.name }}</strong>
                <small>{{ provider.baseUrl }}</small>
              </td>
              <td>{{ providerAdapterLabel(provider.adapterType) }}</td>
              <td>
                <span class="ai-status-chip" :class="`is-${provider.healthStatus}`">
                  {{ providerHealthLabel(provider.healthStatus) }}
                </span>
              </td>
              <td>{{ capabilitySummary(provider.id) }}</td>
              <td>{{ store.modelsForProvider(provider.id).length }}</td>
              <td>
                <button
                  class="ai-button is-quiet"
                  type="button"
                  @click="store.selectProvider(provider.id)"
                >
                  管理
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <aside v-if="store.selectedProvider" class="ai-detail-panel">
        <header>
          <div>
            <span class="ai-eyebrow">Provider 详情</span>
            <h3>{{ store.selectedProvider.name }}</h3>
          </div>
          <button
            class="ai-icon-button"
            type="button"
            aria-label="关闭 Provider 详情"
            @click="store.selectProvider(null)"
          >
            <span class="material-symbols-outlined">close</span>
          </button>
        </header>
        <dl class="ai-detail-list">
          <div><dt>地址</dt><dd>{{ store.selectedProvider.baseUrl }}</dd></div>
          <div>
            <dt>凭据</dt>
            <dd>
              {{ store.selectedProvider.credentialSummary.configured
                ? store.selectedProvider.credentialSummary.maskedValue
                : "未配置" }}
            </dd>
          </div>
          <div>
            <dt>修订</dt>
            <dd>{{ store.selectedProvider.revision }}</dd>
          </div>
        </dl>
        <section
          class="ai-provider-validation"
          data-testid="provider-real-validation"
        >
          <header>
            <div>
              <strong>四阶段真实验证</strong>
              <small>每个阶段都由 Runtime 外呼并保存脱敏证据。</small>
            </div>
          </header>
          <ol>
            <li
              v-for="stage in store.validationStages(store.selectedProvider.id)"
              :key="stage.key"
              :class="`is-${stage.status}`"
            >
              <span class="material-symbols-outlined" aria-hidden="true">
                {{ stage.status === "verified" ? "check_circle" : "pending" }}
              </span>
              <span>
                <strong>{{ stage.label }}</strong>
                <small>{{ validationStageLabel(stage.status) }}</small>
              </span>
            </li>
          </ol>
          <label v-if="store.modelsForProvider(store.selectedProvider.id).length">
            <span>真实小调用模型</span>
            <select
              :value="store.selectedValidationModelId ?? ''"
              :disabled="Boolean(store.busyKey)"
              @change="selectValidationModel"
            >
              <option
                v-for="model in store.modelsForProvider(store.selectedProvider.id)"
                :key="model.id"
                :value="model.id"
              >
                {{ model.displayName }} · {{ model.modelId }}
              </option>
            </select>
          </label>
        </section>
        <label class="ai-toggle-row">
          <span>
            <strong>允许 Route 使用</strong>
            <small>未验证 Provider 即使启用也会被 Runtime 拒绝。</small>
          </span>
          <input
            type="checkbox"
            :checked="store.selectedProvider.enabled"
            :disabled="Boolean(store.busyKey)"
            @change="toggleEnabled"
          />
        </label>
        <div class="ai-detail-actions">
          <button
            class="ai-button is-quiet"
            type="button"
            :disabled="Boolean(modelStore.busyKey)"
            @click="openManualModel"
          >
            手动添加模型
          </button>
          <button
            class="ai-button is-secondary"
            type="button"
            :disabled="Boolean(store.busyKey)"
            @click="store.discoverModels(store.selectedProvider)"
          >
            验证模型发现
          </button>
          <button
            class="ai-button is-secondary"
            type="button"
            :disabled="Boolean(store.busyKey)"
            @click="store.runCheck(store.selectedProvider)"
          >
            验证网络与鉴权
          </button>
          <button
            class="ai-button is-primary"
            type="button"
            :disabled="Boolean(store.busyKey) || !store.selectedValidationModelId"
            @click="store.runRealSmallCall(store.selectedProvider)"
          >
            验证真实小调用
          </button>
        </div>
      </aside>
    </div>

    <ProviderWizard
      :open="wizardOpen"
      @close="wizardOpen = false"
      @open-log="$emit('openLog', $event)"
      @saved="handleSaved"
    />
    <ManualModelDialog
      :busy="Boolean(modelStore.busyKey)"
      :error-log-id="modelStore.error?.logId"
      :error-message="modelStore.error?.message"
      :initial-provider-id="store.selectedProviderId"
      :open="manualModelOpen"
      :providers="store.providers"
      @close="manualModelOpen = false"
      @open-log="$emit('openLog', $event)"
      @submit="handleManualModel"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import type {
  ModelCreateInput,
  ProviderDto
} from "@/types/runtime/ai-system";

import {
  capabilityLabel,
  providerAdapterLabel,
  providerHealthLabel
} from "../ai-config-helpers";
import { useProviderConfigStore } from "../provider-config-store";
import type { ProviderValidationStage } from "../provider-config-store";
import { useModelRouteConfigStore } from "../model-route-config-store";
import AIConfigStatePanel from "./AIConfigStatePanel.vue";
import AISystemTaskBanner from "./AISystemTaskBanner.vue";
import ManualModelDialog from "./ManualModelDialog.vue";
import ProviderWizard from "./ProviderWizard.vue";

defineEmits<{ openLog: [logId: string] }>();

const store = useProviderConfigStore();
const modelStore = useModelRouteConfigStore();
const wizardOpen = ref(false);
const manualModelOpen = ref(false);
const showState = computed(
  () =>
    store.state !== "ready"
    && !(
      store.state === "waiting_external"
      && store.providers.length > 0
    )
);

onMounted(() => {
  if (store.state === "idle") void store.load();
});

function capabilitySummary(providerId: string): string {
  const labels = new Set(
    store.modelsForProvider(providerId)
      .flatMap((model) => model.capabilities)
      .filter((capability) => capability.availability === "available")
      .map((capability) => capabilityLabel(capability.capabilityKey))
  );
  return labels.size ? [...labels].slice(0, 2).join("、") : "待验证";
}

function toggleEnabled(event: Event): void {
  const provider = store.selectedProvider;
  if (!provider) return;
  const enabled = (event.target as HTMLInputElement).checked;
  void store.updateProvider(provider, { enabled });
}

async function handleSaved(_provider: ProviderDto): Promise<void> {
  await store.load();
}

function openManualModel(): void {
  modelStore.clearFeedback();
  manualModelOpen.value = true;
}

function selectValidationModel(event: Event): void {
  store.selectValidationModel((event.target as HTMLSelectElement).value);
}

function validationStageLabel(
  status: ProviderValidationStage["status"]
): string {
  return {
    pending: "待验证",
    checking: "验证中",
    verified: "已通过",
    failed: "需处理"
  }[status];
}

async function handleManualModel(input: ModelCreateInput): Promise<void> {
  if (!await modelStore.createManualModel(input)) return;
  manualModelOpen.value = false;
  await store.load();
}
</script>
