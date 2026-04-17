<template>
  <ProjectContextGuard>
    <div class="publishing-console" data-testid="publishing-console">
      <header class="publishing-console__header">
        <div class="publishing-console__headline">
          <p class="publishing-console__eyebrow">发布链路</p>
          <h1>发布工作面</h1>
          <p class="publishing-console__summary">
            这里直接消费账号、计划和预检状态。未绑定的项目或失败的预检会被标成阻断，而不是伪装成已完成。
          </p>
        </div>

        <div class="publishing-console__metrics">
          <article class="publishing-console__metric">
            <span>计划总数</span>
            <strong>{{ plans.length }}</strong>
          </article>
          <article class="publishing-console__metric">
            <span>待预检</span>
            <strong>{{ draftPlanCount }}</strong>
          </article>
          <article class="publishing-console__metric">
            <span>已阻断</span>
            <strong>{{ blockedPlanCount }}</strong>
          </article>
          <article class="publishing-console__metric">
            <span>工作状态</span>
            <strong>{{ workflowStateLabel }}</strong>
          </article>
        </div>
      </header>

      <div class="publishing-console__context">
        <span class="publishing-console__context-chip">当前项目 {{ currentProjectLabel }}</span>
        <span class="publishing-console__context-chip">同步状态 {{ configSyncLabel }}</span>
        <span class="publishing-console__context-chip">{{ licenseLabel }}</span>
      </div>

      <div v-if="publishingStore.error" class="publishing-console__banner publishing-console__banner--error">
        {{ publishingStore.error }}
      </div>
      <div v-else-if="publishingStore.loading" class="publishing-console__banner publishing-console__banner--loading">
        正在读取发布计划。
      </div>
      <div v-else-if="publishingStore.workflowState === 'blocked'" class="publishing-console__banner publishing-console__banner--blocked">
        <strong>当前计划被阻断：</strong>
        <span>{{ selectedPlanBlockReason }}</span>
      </div>

      <main class="publishing-console__body">
        <aside class="publishing-console__rail">
          <div class="publishing-console__rail-toolbar">
            <button class="publishing-console__primary" type="button" @click="showAddPlan = true">
              <span class="material-symbols-outlined">calendar_add_on</span>
              新建发布计划
            </button>

            <div class="publishing-console__chips">
              <button
                v-for="item in statusFilters"
                :key="item.value"
                type="button"
                class="publishing-console__chip"
                :class="{ 'publishing-console__chip--active': statusFilter === item.value }"
                @click="statusFilter = item.value"
              >
                {{ item.label }}
              </button>
            </div>
          </div>

          <div v-if="isEmpty" class="publishing-console__empty" data-testid="publishing-empty-state">
            <span class="material-symbols-outlined publishing-console__empty-icon">rocket_launch</span>
            <h2>还没有发布计划</h2>
            <p>创建一个计划后，可以在这里执行预检、提交和取消。</p>
            <button class="publishing-console__secondary" type="button" @click="showAddPlan = true">
              立刻创建
            </button>
          </div>

          <div v-else class="publishing-console__plan-list" data-testid="publishing-plan-list">
            <button
              v-for="plan in filteredPlans"
              :key="plan.id"
              type="button"
              class="publishing-console__plan"
              :class="{
                'publishing-console__plan--active': selectedPlanId === plan.id,
                'publishing-console__plan--blocked': isPlanBlocked(plan)
              }"
              @click="selectedPlanId = plan.id"
            >
              <div class="publishing-console__plan-row">
                <div class="publishing-console__plan-title">
                  <strong>{{ plan.title || "未命名计划" }}</strong>
                  <span>{{ plan.status }}</span>
                </div>
                <span class="publishing-console__status-pill" :class="planStatusTone(plan)">
                  {{ planStatusLabel(plan) }}
                </span>
              </div>

              <div class="publishing-console__plan-meta">
                <span>账号 {{ plan.accountLabel }}</span>
                <span>项目 {{ plan.projectLabel }}</span>
              </div>
              <div class="publishing-console__plan-meta">
                <span>视频 {{ plan.videoAssetLabel }}</span>
                <span>定时 {{ plan.scheduledAtLabel }}</span>
              </div>
            </button>
          </div>
        </aside>

        <section class="publishing-console__workspace" data-testid="publishing-plan-detail">
          <template v-if="selectedPlan">
            <div class="publishing-console__workspace-head">
              <div>
                <p class="publishing-console__eyebrow">当前计划</p>
                <h2>{{ selectedPlan.title || "未命名计划" }}</h2>
                <p class="publishing-console__summary publishing-console__summary--compact">
                  账号 {{ selectedPlan.accountLabel }}，项目 {{ selectedPlan.projectLabel }}，视频
                  {{ selectedPlan.videoAssetLabel }}。
                </p>
              </div>

              <div class="publishing-console__workspace-actions">
                <span class="publishing-console__status-pill" :class="planStatusTone(selectedPlan)">
                  {{ planStatusLabel(selectedPlan) }}
                </span>
                <button
                  class="publishing-console__secondary"
                  type="button"
                  :disabled="isActionDisabled"
                  @click="handlePrecheck"
                >
                  执行预检
                </button>
                <button
                  class="publishing-console__primary"
                  type="button"
                  :disabled="isSubmitDisabled"
                  @click="handleSubmit"
                >
                  提交发布
                </button>
                <button class="publishing-console__ghost" type="button" :disabled="isBusy" @click="handleCancel">
                  取消计划
                </button>
              </div>
            </div>

            <div class="publishing-console__state-row">
              <article class="publishing-console__state-tile">
                <span>绑定账号</span>
                <strong>{{ selectedPlan.accountLabel }}</strong>
              </article>
              <article class="publishing-console__state-tile">
                <span>绑定项目</span>
                <strong>{{ selectedPlan.projectLabel }}</strong>
              </article>
              <article class="publishing-console__state-tile">
                <span>预检结果</span>
                <strong>{{ precheckSummaryLabel }}</strong>
              </article>
              <article class="publishing-console__state-tile">
                <span>阻断语义</span>
                <strong>{{ selectedPlanBlockReason }}</strong>
              </article>
            </div>

            <section class="publishing-console__lane">
              <div class="publishing-console__lane-head">
                <h3>发布绑定</h3>
                <span>{{ selectedPlan.status }}</span>
              </div>
              <div class="publishing-console__binding-grid">
                <div class="publishing-console__binding-row">
                  <span>账号 ID</span>
                  <strong>{{ selectedPlan.account_id || "未绑定" }}</strong>
                </div>
                <div class="publishing-console__binding-row">
                  <span>账号名称</span>
                  <strong>{{ selectedPlan.account_name || "未绑定" }}</strong>
                </div>
                <div class="publishing-console__binding-row">
                  <span>项目 ID</span>
                  <strong>{{ selectedPlan.project_id || "未绑定" }}</strong>
                </div>
                <div class="publishing-console__binding-row">
                  <span>视频素材 ID</span>
                  <strong>{{ selectedPlan.video_asset_id || "未绑定" }}</strong>
                </div>
                <div class="publishing-console__binding-row">
                  <span>定时发布</span>
                  <strong>{{ selectedPlan.scheduled_at ? formatDateTime(selectedPlan.scheduled_at) : "立即发布" }}</strong>
                </div>
              </div>
            </section>

            <section class="publishing-console__lane">
              <div class="publishing-console__lane-head">
                <h3>预检结果</h3>
                <span>{{ precheckItems.length }} 项</span>
              </div>

              <div v-if="precheckItems.length === 0" class="publishing-console__empty publishing-console__empty--inline">
                还没有执行预检，先点“执行预检”读取真实结果。
              </div>
              <div v-else class="publishing-console__check-list">
                <article
                  v-for="item in precheckItems"
                  :key="item.code"
                  class="publishing-console__check"
                  :class="item.result"
                >
                  <span class="publishing-console__check-icon material-symbols-outlined">
                    {{ checkIcon(item.result) }}
                  </span>
                  <div class="publishing-console__check-copy">
                    <strong>{{ item.label }}</strong>
                    <p>{{ item.message || "无额外说明" }}</p>
                  </div>
                  <span class="publishing-console__status-pill" :class="precheckTone(item.result)">
                    {{ item.result }}
                  </span>
                </article>
              </div>
            </section>

            <section class="publishing-console__lane">
              <div class="publishing-console__lane-head">
                <h3>提交回执</h3>
                <span>{{ receiptLabel }}</span>
              </div>

              <div v-if="receipt === null" class="publishing-console__empty publishing-console__empty--inline">
                提交后，这里会显示 Runtime 返回的真实回执。
              </div>
              <div v-else class="publishing-console__receipt">
                <div class="publishing-console__receipt-row">
                  <span>状态</span>
                  <strong>{{ receipt.status }}</strong>
                </div>
                <div class="publishing-console__receipt-row">
                  <span>说明</span>
                  <strong>{{ receipt.message || "无" }}</strong>
                </div>
                <div class="publishing-console__receipt-row" v-if="receipt.error">
                  <span>错误</span>
                  <strong>{{ receipt.error }}</strong>
                </div>
              </div>
            </section>
          </template>

          <div v-else class="publishing-console__detail-empty">
            <span class="material-symbols-outlined publishing-console__empty-icon">assignment</span>
            <h2>选择一个发布计划查看预检和提交链路</h2>
            <p>这里会显示绑定、阻断和回执，不再只是一张列表。</p>
          </div>
        </section>
      </main>

      <div v-if="showAddPlan" class="publishing-console__drawer" @click.self="showAddPlan = false">
        <section class="publishing-console__drawer-panel">
          <div class="publishing-console__drawer-head">
            <div>
              <p class="publishing-console__eyebrow">新建计划</p>
              <h2>创建发布计划</h2>
            </div>
            <button class="publishing-console__icon-button" type="button" @click="showAddPlan = false">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <div class="publishing-console__drawer-body">
            <label class="publishing-console__field">
              <span>计划标题</span>
              <input v-model="addForm.title" type="text" placeholder="例如：TikTok 周更视频发布" />
            </label>

            <label class="publishing-console__field">
              <span>账号名称</span>
              <input v-model="addForm.accountName" type="text" placeholder="账号昵称或 ID" />
            </label>

            <label class="publishing-console__field">
              <span>账号 ID</span>
              <input v-model="addForm.accountId" type="text" placeholder="account-1" />
            </label>

            <label class="publishing-console__field">
              <span>项目 ID</span>
              <input v-model="addForm.projectId" type="text" :placeholder="currentProjectIdPlaceholder" />
            </label>

            <label class="publishing-console__field">
              <span>视频素材 ID</span>
              <input v-model="addForm.videoAssetId" type="text" placeholder="asset-1" />
            </label>

            <label class="publishing-console__field">
              <span>定时发布</span>
              <input v-model="addForm.scheduledAt" type="datetime-local" />
            </label>

            <div class="publishing-console__drawer-actions">
              <button class="publishing-console__secondary" type="button" @click="showAddPlan = false">
                取消
              </button>
              <button class="publishing-console__primary" type="button" :disabled="isBusy" @click="handleCreatePlan">
                保存计划
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import { useProjectStore } from "@/stores/project";
import { usePublishingStore } from "@/stores/publishing";
import type { PublishPlanCreateInput, PublishPlanDto, PrecheckItemResult, PrecheckResultDto } from "@/types/runtime";

type PublishPlanView = PublishPlanDto & {
  accountLabel: string;
  projectLabel: string;
  scheduledAtLabel: string;
  videoAssetLabel: string;
};

type StatusFilterValue = "all" | "draft" | "ready" | "submitting" | "published" | "failed" | "cancelled";

const publishingStore = usePublishingStore();
const projectStore = useProjectStore();
const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();

const selectedPlanId = ref<string | null>(null);
const statusFilter = ref<StatusFilterValue>("all");
const showAddPlan = ref(false);
const addForm = ref({
  title: "",
  accountName: "",
  accountId: "",
  projectId: "",
  videoAssetId: "",
  scheduledAt: ""
});

const plans = computed<PublishPlanView[]>(() =>
  publishingStore.plans.map((plan) => ({
    ...plan,
    accountLabel: plan.account_name || plan.account_id || "未绑定",
    projectLabel: plan.project_id || "未绑定",
    scheduledAtLabel: plan.scheduled_at ? formatDateTime(plan.scheduled_at) : "立即发布",
    videoAssetLabel: plan.video_asset_id || "未绑定"
  }))
);

const currentProjectLabel = computed(
  () => projectStore.currentProject?.projectName || projectStore.currentProject?.projectId || "未选择"
);
const currentProjectIdPlaceholder = computed(
  () => projectStore.currentProject?.projectId || "project-1"
);
const licenseLabel = computed(() => (licenseStore.active ? "授权已激活" : "授权未激活"));
const configSyncLabel = computed(() => {
  if (configBusStore.status === "saving") {
    return "同步中";
  }
  if (configBusStore.status === "error") {
    return "同步异常";
  }
  return configBusStore.runtimeStatus === "online" ? "在线" : "离线";
});

const workflowStateLabel = computed(() => {
  switch (publishingStore.workflowState) {
    case "checking":
      return "预检中";
    case "submitting":
      return "提交中";
    case "blocked":
      return "已阻断";
    case "error":
      return "异常";
    case "ready":
      return "就绪";
    default:
      return "空闲";
  }
});

const statusFilters: Array<{ label: string; value: StatusFilterValue }> = [
  { label: "全部", value: "all" },
  { label: "草稿", value: "draft" },
  { label: "就绪", value: "ready" },
  { label: "提交中", value: "submitting" },
  { label: "已发布", value: "published" },
  { label: "失败", value: "failed" },
  { label: "已取消", value: "cancelled" }
];

const filteredPlans = computed(() => {
  if (statusFilter.value === "all") {
    return plans.value;
  }
  return plans.value.filter((plan) => plan.status === statusFilter.value);
});

const selectedPlan = computed(() =>
  plans.value.find((plan) => plan.id === selectedPlanId.value) ?? null
);

const draftPlanCount = computed(() => plans.value.filter((plan) => plan.status === "draft").length);
const blockedPlanCount = computed(() =>
  plans.value.filter((plan) => isPlanBlocked(plan) || plan.status === "failed").length
);
const isLoading = computed(() => publishingStore.loading);
const isEmpty = computed(() => publishingStore.viewState === "empty" && !isLoading.value);
const isBusy = computed(
  () => isLoading.value || publishingStore.workflowState === "checking" || publishingStore.workflowState === "submitting"
);
const isActionDisabled = computed(
  () => !selectedPlan.value || isBusy.value || isPlanBlocked(selectedPlan.value)
);
const isSubmitDisabled = computed(
  () =>
    !selectedPlan.value ||
    isBusy.value ||
    selectedPlan.value.status === "published" ||
    selectedPlan.value.status === "cancelled" ||
    Boolean(selectedPlanBlockReason.value)
);

const precheckResult = computed<PrecheckResultDto | null>(() => publishingStore.precheckResult);
const precheckItems = computed(() => precheckResult.value?.items ?? []);
const receipt = computed(() =>
  publishingStore.submitResult
    ? {
        status: publishingStore.submitResult.status,
        message: publishingStore.submitResult.message,
        error: publishingStore.error ?? null
      }
    : publishingStore.error
      ? {
          status: "failed",
          message: "",
          error: publishingStore.error
        }
      : null
);
const receiptLabel = computed(() =>
  receipt.value ? receipt.value.status : publishingStore.workflowState === "submitting" ? "提交中" : "未提交"
);

const precheckSummaryLabel = computed(() => {
  if (!precheckResult.value) {
    return "未执行";
  }

  const passed = precheckItems.value.filter((item) => item.result === "passed").length;
  const failed = precheckItems.value.filter((item) => item.result === "failed").length;
  return `${passed} 通过 / ${failed} 阻断`;
});

const selectedPlanBlockReason = computed(() => {
  if (!selectedPlan.value) {
    return "未选择计划";
  }
  if (selectedPlan.value.status === "published") {
    return "计划已经发布";
  }
  if (selectedPlan.value.status === "cancelled") {
    return "计划已经取消";
  }
  if (!selectedPlan.value.account_id && !selectedPlan.value.account_name) {
    return "账号尚未绑定";
  }
  if (!selectedPlan.value.project_id) {
    return "项目尚未绑定";
  }
  if (!selectedPlan.value.video_asset_id) {
    return "视频素材尚未绑定";
  }
  if (precheckResult.value?.has_errors) {
    return "预检结果存在阻断项";
  }
  if (publishingStore.workflowState === "blocked") {
    return "Runtime 已标记为阻断";
  }
  return "可继续提交";
});

onMounted(() => {
  void publishingStore.loadPlans();
});

watch(
  () => plans.value.map((plan) => plan.id).join("|"),
  () => {
    if (!selectedPlanId.value && plans.value.length > 0) {
      selectedPlanId.value = plans.value[0].id;
    }
  },
  { immediate: true }
);

watch(
  () => selectedPlanId.value,
  (planId) => {
    if (planId && !publishingStore.precheckResult) {
      // 维持当前预检结果即可，不主动制造额外请求。
    }
  }
);

function isPlanBlocked(plan: PublishPlanView): boolean {
  return (
    !plan.account_id ||
    !plan.project_id ||
    !plan.video_asset_id ||
    plan.status === "failed" ||
    Boolean(plan.error_message)
  );
}

function planStatusTone(plan: PublishPlanView): string {
  if (plan.status === "published") {
    return "is-success";
  }
  if (plan.status === "failed") {
    return "is-error";
  }
  if (plan.status === "submitting") {
    return "is-running";
  }
  if (isPlanBlocked(plan)) {
    return "is-blocked";
  }
  return "is-muted";
}

function planStatusLabel(plan: PublishPlanView): string {
  if (plan.status === "draft") {
    return "草稿";
  }
  if (plan.status === "ready") {
    return "可提交";
  }
  if (plan.status === "submitting") {
    return "提交中";
  }
  if (plan.status === "published") {
    return "已发布";
  }
  if (plan.status === "cancelled") {
    return "已取消";
  }
  if (plan.status === "failed") {
    return "失败";
  }
  return plan.status;
}

function precheckTone(result: PrecheckItemResult["result"]): string {
  if (result === "passed") {
    return "is-success";
  }
  if (result === "failed") {
    return "is-error";
  }
  if (result === "pending") {
    return "is-muted";
  }
  return "is-blocked";
}

function checkIcon(result: PrecheckItemResult["result"]): string {
  if (result === "passed") {
    return "check_circle";
  }
  if (result === "failed") {
    return "cancel";
  }
  return "radio_button_unchecked";
}

async function handlePrecheck(): Promise<void> {
  if (!selectedPlan.value || isBusy.value) {
    return;
  }

  await publishingStore.precheck(selectedPlan.value.id);
}

async function handleSubmit(): Promise<void> {
  if (!selectedPlan.value || isSubmitDisabled.value) {
    return;
  }

  await publishingStore.submit(selectedPlan.value.id);
}

async function handleCancel(): Promise<void> {
  if (!selectedPlan.value || isBusy.value) {
    return;
  }

  await publishingStore.cancel(selectedPlan.value.id);
}

async function handleCreatePlan(): Promise<void> {
  if (!addForm.value.title.trim()) {
    return;
  }

  const input: PublishPlanCreateInput = {
    title: addForm.value.title.trim(),
    account_name: addForm.value.accountName.trim() || null,
    account_id: addForm.value.accountId.trim() || null,
    project_id: addForm.value.projectId.trim() || null,
    video_asset_id: addForm.value.videoAssetId.trim() || null,
    scheduled_at: addForm.value.scheduledAt || null
  };

  const plan = await publishingStore.addPlan(input);
  if (!plan) {
    return;
  }

  selectedPlanId.value = plan.id;
  addForm.value = {
    title: "",
    accountName: "",
    accountId: "",
    projectId: projectStore.currentProject?.projectId || "",
    videoAssetId: "",
    scheduledAt: ""
  };
  showAddPlan.value = false;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return `${date.toLocaleDateString("zh-CN")} ${date.toLocaleTimeString("zh-CN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit"
  })}`;
}

watch(
  () => projectStore.currentProject?.projectId,
  (projectId) => {
    if (!addForm.value.projectId && projectId) {
      addForm.value.projectId = projectId;
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.publishing-console {
  display: grid;
  gap: 16px;
  min-height: 100%;
  padding: 20px 24px 24px;
}

.publishing-console__header,
.publishing-console__workspace-head,
.publishing-console__lane,
.publishing-console__rail-toolbar {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.publishing-console__header {
  display: grid;
  gap: 16px;
  padding: 18px 20px;
}

.publishing-console__headline {
  display: grid;
  gap: 8px;
  max-width: 860px;
}

.publishing-console__eyebrow {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.publishing-console__headline h1,
.publishing-console__workspace-head h2,
.publishing-console__drawer-head h2,
.publishing-console__empty h2,
.publishing-console__detail-empty h2 {
  margin: 0;
}

.publishing-console__summary {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.publishing-console__summary--compact {
  max-width: 780px;
}

.publishing-console__metrics {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.publishing-console__metric,
.publishing-console__state-tile {
  display: grid;
  gap: 4px;
  padding: 14px 16px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
}

.publishing-console__metric span,
.publishing-console__state-tile span,
.publishing-console__plan-meta,
.publishing-console__lane-head span,
.publishing-console__context-chip {
  color: var(--text-secondary);
  font-size: 12px;
}

.publishing-console__metric strong,
.publishing-console__state-tile strong {
  font-size: 18px;
  line-height: 1.2;
}

.publishing-console__context {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.publishing-console__context-chip {
  padding: 6px 10px;
  border: 1px solid var(--border-default);
  border-radius: 999px;
  background: color-mix(in srgb, var(--surface-secondary) 90%, transparent);
}

.publishing-console__banner {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  align-items: center;
  padding: 12px 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
}

.publishing-console__banner--error {
  color: var(--status-error);
  border-color: color-mix(in srgb, var(--status-error) 30%, var(--border-default));
}

.publishing-console__banner--loading {
  border-color: color-mix(in srgb, var(--brand-primary) 24%, var(--border-default));
}

.publishing-console__banner--blocked {
  border-color: color-mix(in srgb, var(--status-warning) 30%, var(--border-default));
  color: var(--status-warning);
}

.publishing-console__status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.5;
}

.publishing-console__status-pill.is-success {
  background: color-mix(in srgb, var(--status-success) 16%, transparent);
  color: var(--status-success);
}

.publishing-console__status-pill.is-error {
  background: color-mix(in srgb, var(--status-error) 18%, transparent);
  color: var(--status-error);
}

.publishing-console__status-pill.is-blocked {
  background: color-mix(in srgb, var(--status-warning) 18%, transparent);
  color: var(--status-warning);
}

.publishing-console__status-pill.is-running {
  background: color-mix(in srgb, var(--brand-primary) 18%, transparent);
  color: var(--brand-primary);
}

.publishing-console__status-pill.is-muted {
  background: color-mix(in srgb, var(--text-muted) 18%, transparent);
  color: var(--text-muted);
}

.publishing-console__body {
  display: grid;
  grid-template-columns: minmax(320px, 380px) minmax(0, 1fr);
  gap: 16px;
  min-height: 0;
}

.publishing-console__rail {
  display: grid;
  gap: 12px;
  align-content: start;
}

.publishing-console__rail-toolbar {
  display: grid;
  gap: 12px;
  padding: 16px;
}

.publishing-console__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.publishing-console__chip,
.publishing-console__primary,
.publishing-console__secondary,
.publishing-console__ghost,
.publishing-console__icon-button {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  cursor: pointer;
  font: inherit;
  transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease, transform 80ms ease;
}

.publishing-console__chip {
  padding: 6px 10px;
  background: transparent;
  color: var(--text-secondary);
}

.publishing-console__chip--active {
  background: color-mix(in srgb, var(--brand-primary) 12%, transparent);
  border-color: color-mix(in srgb, var(--brand-primary) 28%, var(--border-default));
  color: var(--brand-primary);
}

.publishing-console__primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 14px;
  background: var(--brand-primary);
  color: #000;
  font-weight: 700;
}

.publishing-console__secondary,
.publishing-console__ghost {
  min-height: 32px;
  padding: 0 12px;
  background: transparent;
  color: var(--text-primary);
}

.publishing-console__secondary:disabled,
.publishing-console__ghost:disabled,
.publishing-console__primary:disabled,
.publishing-console__icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.publishing-console__plan-list {
  display: grid;
  gap: 10px;
}

.publishing-console__plan {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
  text-align: left;
  color: var(--text-primary);
}

.publishing-console__plan--active {
  border-color: color-mix(in srgb, var(--brand-primary) 34%, var(--border-default));
  background: color-mix(in srgb, var(--brand-primary) 8%, var(--surface-secondary));
}

.publishing-console__plan--blocked {
  border-color: color-mix(in srgb, var(--status-warning) 30%, var(--border-default));
}

.publishing-console__plan-row,
.publishing-console__workspace-head,
.publishing-console__lane-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.publishing-console__plan-title {
  display: grid;
  gap: 4px;
}

.publishing-console__plan-title strong {
  font-size: 14px;
}

.publishing-console__plan-title span {
  color: var(--text-secondary);
  font-size: 12px;
}

.publishing-console__plan-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.publishing-console__workspace {
  display: grid;
  gap: 14px;
  align-content: start;
}

.publishing-console__workspace-head {
  padding: 16px 18px;
}

.publishing-console__workspace-actions {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.publishing-console__state-row {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.publishing-console__lane {
  display: grid;
  gap: 12px;
  padding: 16px 18px;
}

.publishing-console__lane-head h3 {
  margin: 0;
  font-size: 14px;
}

.publishing-console__binding-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.publishing-console__binding-row,
.publishing-console__receipt-row,
.publishing-console__check {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-primary) 92%, transparent);
}

.publishing-console__binding-row span,
.publishing-console__receipt-row span {
  color: var(--text-secondary);
  font-size: 12px;
}

.publishing-console__check-list {
  display: grid;
  gap: 10px;
}

.publishing-console__check {
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: 12px;
}

.publishing-console__check.passed {
  border-color: color-mix(in srgb, var(--status-success) 24%, var(--border-default));
}

.publishing-console__check.failed {
  border-color: color-mix(in srgb, var(--status-error) 24%, var(--border-default));
}

.publishing-console__check.pending {
  border-color: color-mix(in srgb, var(--text-muted) 22%, var(--border-default));
}

.publishing-console__check-icon {
  font-size: 18px;
  color: var(--brand-primary);
}

.publishing-console__check.failed .publishing-console__check-icon {
  color: var(--status-error);
}

.publishing-console__check.pending .publishing-console__check-icon {
  color: var(--text-muted);
}

.publishing-console__check-copy {
  display: grid;
  gap: 4px;
}

.publishing-console__check-copy p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.publishing-console__receipt {
  display: grid;
  gap: 10px;
}

.publishing-console__empty,
.publishing-console__detail-empty {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 36px 24px;
  border: 1px dashed var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  text-align: center;
}

.publishing-console__empty--inline {
  padding: 24px 18px;
}

.publishing-console__empty-icon {
  font-size: 40px;
  color: var(--brand-primary);
}

.publishing-console__drawer {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  justify-content: flex-end;
  background: rgba(0, 0, 0, 0.52);
}

.publishing-console__drawer-panel {
  display: grid;
  grid-template-rows: auto 1fr;
  width: min(460px, 100%);
  height: 100%;
  background: var(--bg-elevated);
  border-left: 1px solid var(--border-default);
}

.publishing-console__drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 18px 14px;
  border-bottom: 1px solid var(--border-default);
}

.publishing-console__drawer-body {
  display: grid;
  gap: 14px;
  padding: 16px 18px 18px;
  overflow-y: auto;
}

.publishing-console__field {
  display: grid;
  gap: 8px;
}

.publishing-console__field span {
  color: var(--text-secondary);
  font-size: 12px;
}

.publishing-console__field input,
.publishing-console__field select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-primary);
  font: inherit;
}

.publishing-console__drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 6px;
}

.publishing-console__icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  color: var(--text-secondary);
}

@media (max-width: 1180px) {
  .publishing-console__body {
    grid-template-columns: 1fr;
  }

  .publishing-console__metrics,
  .publishing-console__state-row,
  .publishing-console__binding-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .publishing-console {
    padding-inline: 16px;
  }

  .publishing-console__metrics,
  .publishing-console__state-row,
  .publishing-console__binding-grid {
    grid-template-columns: 1fr;
  }

  .publishing-console__plan-row,
  .publishing-console__workspace-head,
  .publishing-console__lane-head,
  .publishing-console__check {
    align-items: flex-start;
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
</style>
