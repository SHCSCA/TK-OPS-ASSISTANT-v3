<template>
  <section class="ai-workspace" aria-labelledby="model-heading">
    <header class="ai-workspace-header">
      <div>
        <span class="ai-eyebrow">真实模型与产品路由</span>
        <h2 id="model-heading">模型与能力</h2>
        <p>能力只有声明、适配器接入和契约验证同时通过后才可选。</p>
      </div>
      <div class="ai-toolbar">
        <button
          v-if="store.mode === 'models' && store.providers.length"
          class="ai-button is-secondary"
          type="button"
          @click="openManualModel"
        >
          手动添加模型
        </button>
        <button
          v-else-if="store.mode === 'routes' && routeCreationOptions.length"
          class="ai-button is-secondary"
          type="button"
          @click="openRouteCreation"
        >
          新建 Route
        </button>
        <button class="ai-button is-quiet" type="button" @click="store.load">
          刷新
        </button>
      </div>
    </header>

    <nav class="ai-segmented" aria-label="模型与能力工作面">
      <button
        type="button"
        :class="{ 'is-active': store.mode === 'models' }"
        @click="store.setMode('models')"
      >
        模型矩阵
      </button>
      <button
        type="button"
        :class="{ 'is-active': store.mode === 'routes' }"
        @click="store.setMode('routes')"
      >
        能力 Route
      </button>
    </nav>

    <div class="ai-toolbar">
      <label class="ai-search">
        <span class="material-symbols-outlined">search</span>
        <input
          v-model="store.search"
          type="search"
          :placeholder="store.mode === 'models' ? '搜索模型或能力' : '搜索产品能力'"
          @input="store.recomputeState"
        />
      </label>
      <button
        v-if="store.hasFilters"
        class="ai-button is-quiet"
        type="button"
        @click="store.clearFilters"
      >
        清除
      </button>
    </div>

    <AISystemTaskBanner
      :task="store.task"
      task-label="模型能力契约验证"
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

    <div
      v-if="store.error && (store.models.length || store.routes.length)"
      class="ai-inline-feedback is-error"
    >
      <span class="material-symbols-outlined">error</span>
      <div>
        <strong>{{ store.error.message }}</strong>
        <small v-if="store.error.errorCode">{{ store.error.errorCode }}</small>
      </div>
      <button
        v-if="store.error.logId"
        class="ai-button is-quiet"
        type="button"
        @click="$emit('openLog', store.error.logId)"
      >
        查看日志
      </button>
      <button class="ai-icon-button" type="button" @click="store.clearFeedback">
        <span class="material-symbols-outlined">close</span>
      </button>
    </div>

    <AIConfigStatePanel
      v-if="showState"
      :error-message="store.error?.message"
      :log-id="store.error?.logId"
      :action-label="stateActionLabel"
      :state="store.state"
      @action="handleStateAction"
      @clear-filters="store.clearFilters"
      @open-log="$emit('openLog', $event)"
      @retry="store.load"
    />

    <div v-else-if="store.mode === 'models'" class="ai-table-detail-layout">
      <div class="ai-table-wrap">
        <table class="ai-data-table">
          <thead>
            <tr>
              <th>模型 ID</th>
              <th>Provider</th>
              <th>启用</th>
              <th>已接入能力</th>
              <th>契约验证</th>
              <th><span class="sr-only">动作</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="model in store.filteredModels"
              :key="model.id"
              :class="{ 'is-selected': model.id === store.selectedModelId }"
            >
              <td><strong>{{ model.modelId }}</strong><small>{{ model.displayName }}</small></td>
              <td>{{ store.providerFor(model)?.name ?? "未知 Provider" }}</td>
              <td>{{ model.enabled ? "是" : "否" }}</td>
              <td>{{ availableCount(model.id) }}</td>
              <td>{{ verifiedCount(model.id) }}</td>
              <td>
                <button
                  class="ai-button is-quiet"
                  type="button"
                  @click="store.selectModel(model.id)"
                >
                  查看矩阵
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <ModelCapabilityMatrix
        v-if="store.selectedModel"
        :busy="Boolean(store.busyKey)"
        :capabilities="store.capabilitiesFor(store.selectedModel.id)"
        :model="store.selectedModel"
        :provider-name="store.providerFor(store.selectedModel)?.name ?? '未知 Provider'"
        @check="store.checkCapabilities(store.selectedModel)"
      />
    </div>

    <div v-else class="ai-table-detail-layout">
      <div class="ai-table-wrap">
        <table class="ai-data-table">
          <thead>
            <tr>
              <th>产品能力</th>
              <th>主模型</th>
              <th>回退模型</th>
              <th>Prompt</th>
              <th>状态</th>
              <th><span class="sr-only">动作</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="route in store.filteredRoutes"
              :key="route.capabilityKey"
              :class="{ 'is-selected': route.capabilityKey === store.selectedCapabilityKey }"
            >
              <td>{{ capabilityLabel(route.capabilityKey) }}</td>
              <td>{{ modelName(route.primaryModelProfileId) }}</td>
              <td>{{ modelName(route.fallbackModelProfileId) }}</td>
              <td>{{ promptName(route.promptProfileId) }}</td>
              <td>
                <span class="ai-status-chip" :class="`is-${route.validationStatus}`">
                  {{ route.validationStatus }}
                </span>
              </td>
              <td>
                <button
                  class="ai-button is-quiet"
                  type="button"
                  @click="store.selectRoute(route.capabilityKey)"
                >
                  修复
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <CapabilityRouteEditor
        v-if="store.selectedRoute"
        :busy="Boolean(store.busyKey)"
        :eligible-models="store.eligibleModels(store.selectedRoute.capabilityKey)"
        :prompts="store.promptsFor(store.selectedRoute.capabilityKey)"
        :route="store.selectedRoute"
        @save="saveSelectedRoute"
        @validate="validateSelectedRoute"
      />
    </div>

    <ManualModelDialog
      :busy="Boolean(store.busyKey)"
      :error-log-id="store.error?.logId"
      :error-message="store.error?.message"
      :open="manualModelOpen"
      :providers="store.providers"
      @close="manualModelOpen = false"
      @open-log="$emit('openLog', $event)"
      @submit="createManualModel"
    />
    <CapabilityRouteCreateDialog
      :busy="Boolean(store.busyKey)"
      :error-log-id="store.error?.logId"
      :error-message="store.error?.message"
      :open="routeCreateOpen"
      :options="routeCreationOptions"
      @close="routeCreateOpen = false"
      @open-log="$emit('openLog', $event)"
      @submit="createRoute"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import {
  AI_CAPABILITY_KEYS,
  type AICapabilityKey,
  type CapabilityRouteInput,
  type ModelCreateInput
} from "@/types/runtime/ai-system";

import { capabilityLabel } from "../ai-config-helpers";
import { useModelRouteConfigStore } from "../model-route-config-store";
import AIConfigStatePanel from "./AIConfigStatePanel.vue";
import AISystemTaskBanner from "./AISystemTaskBanner.vue";
import CapabilityRouteCreateDialog from "./CapabilityRouteCreateDialog.vue";
import CapabilityRouteEditor from "./CapabilityRouteEditor.vue";
import ManualModelDialog from "./ManualModelDialog.vue";
import ModelCapabilityMatrix from "./ModelCapabilityMatrix.vue";

defineEmits<{ openLog: [logId: string] }>();

const store = useModelRouteConfigStore();
const manualModelOpen = ref(false);
const routeCreateOpen = ref(false);
const showState = computed(
  () =>
    store.state !== "ready"
    && !(
      ["waiting_external", "error"].includes(store.state)
      && (store.models.length || store.routes.length)
    )
);
const stateActionLabel = computed(() => {
  if (
    store.mode === "models"
    && store.providers.length
    && !store.models.length
  ) {
    return "手动添加模型";
  }
  if (
    store.mode === "routes"
    && routeCreationOptions.value.length
    && !store.routes.length
  ) {
    return "新建 Route";
  }
  return "";
});
const routeCreationOptions = computed(
  () =>
    AI_CAPABILITY_KEYS
      .filter(
        (capabilityKey) =>
          !store.routes.some(
            (route) => route.capabilityKey === capabilityKey
          )
      )
      .map((capabilityKey) => ({
        capabilityKey,
        label: capabilityLabel(capabilityKey),
        models: store.eligibleModels(capabilityKey),
        prompts: store.promptsFor(capabilityKey)
      }))
);

onMounted(() => {
  if (store.state === "idle") void store.load();
});

function availableCount(modelId: string): string {
  return String(
    store.capabilitiesFor(modelId).filter(
      (item) => item.availability === "available"
    ).length
  );
}

function verifiedCount(modelId: string): string {
  const capabilities = store.capabilitiesFor(modelId);
  return `${capabilities.filter((item) => item.contractVerified).length}/${capabilities.length}`;
}

function modelName(modelId: string | null): string {
  if (!modelId) return "未配置";
  return store.models.find((model) => model.id === modelId)?.displayName ?? "引用已失效";
}

function promptName(activeVersionId: string | null): string {
  if (!activeVersionId) return "未配置";
  return store.prompts.find(
    (prompt) => prompt.activeVersionId === activeVersionId
  )?.name ?? "引用已失效";
}

function openManualModel(): void {
  store.clearFeedback();
  manualModelOpen.value = true;
}

function openRouteCreation(): void {
  store.clearFeedback();
  routeCreateOpen.value = true;
}

function handleStateAction(): void {
  if (store.mode === "models") openManualModel();
  else openRouteCreation();
}

async function createManualModel(input: ModelCreateInput): Promise<void> {
  if (await store.createManualModel(input)) manualModelOpen.value = false;
}

async function createRoute(
  capabilityKey: AICapabilityKey,
  input: CapabilityRouteInput
): Promise<void> {
  if (await store.createRoute(capabilityKey, input)) {
    routeCreateOpen.value = false;
  }
}

async function saveSelectedRoute(input: CapabilityRouteInput): Promise<void> {
  const route = store.selectedRoute;
  if (route) await store.saveRoute(route, input);
}

async function validateSelectedRoute(): Promise<void> {
  const route = store.selectedRoute;
  if (route) await store.validateRoute(route);
}
</script>
