<template>
  <ProjectContextGuard>
    <div class="page-container h-full">
      <header class="page-header">
        <div class="page-header__crumb">首页 / 执行与治理</div>
        <div class="page-header__row">
          <div>
            <h1 class="page-header__title">发布中心</h1>
            <div class="page-header__subtitle">消费账号、计划和预检状态。未绑定的项目或失败的预检会被标成阻断，不会伪装成已完成。</div>
          </div>
        </div>
      </header>

      <div class="publishing-context">
        <Chip variant="default" size="sm">当前项目: {{ currentProjectLabel }}</Chip>
        <Chip variant="default" size="sm">同步状态: {{ configSyncLabel }}</Chip>
        <Chip variant="default" size="sm">{{ licenseLabel }}</Chip>
      </div>

      <div v-if="publishingStore.error" class="dashboard-alert" data-tone="danger">
        <span class="material-symbols-outlined">error</span>
        <span>{{ publishingStore.error }}</span>
      </div>
      <div v-else-if="publishingStore.loading" class="dashboard-alert" data-tone="brand">
        <span class="material-symbols-outlined spinning">sync</span>
        <span>正在读取发布计划...</span>
      </div>
      <div v-else-if="publishingStore.workflowState === 'blocked'" class="dashboard-alert" data-tone="warning">
        <span class="material-symbols-outlined">warning</span>
        <span><strong>当前计划被阻断：</strong>{{ selectedPlanBlockReason }}</span>
      </div>

      <div class="summary-grid">
        <Card class="summary-card">
          <span class="sc-label">计划总数</span>
          <strong class="sc-val">{{ plans.length }}</strong>
        </Card>
        <Card class="summary-card">
          <span class="sc-label">待预检</span>
          <strong class="sc-val">{{ draftPlanCount }}</strong>
        </Card>
        <Card class="summary-card">
          <span class="sc-label">已阻断</span>
          <strong class="sc-val">{{ blockedPlanCount }}</strong>
        </Card>
        <Card class="summary-card">
          <span class="sc-label">工作状态</span>
          <strong class="sc-val">{{ workflowStateLabel }}</strong>
        </Card>
      </div>

      <div class="workspace-grid">
        <aside class="workspace-rail">
          <Card class="rail-card h-full">
            <div class="rail-card__header flex-col align-start gap-3">
              <div style="display: flex; justify-content: space-between; width: 100%;">
                <h3>发布计划列表</h3>
                <Button variant="primary" size="sm" @click="showAddPlan = true">
                  <template #leading><span class="material-symbols-outlined">add</span></template>
                  新建发布计划
                </Button>
              </div>

              <div class="filter-chips">
                <Chip
                  v-for="item in statusFilters"
                  :key="item.value"
                  :variant="statusFilter === item.value ? 'brand' : 'default'"
                  clickable
                  @click="statusFilter = item.value"
                >
                  {{ item.label }}
                </Chip>
              </div>
            </div>

            <div class="rail-card__body no-padding scroll-area">
              <div v-if="isEmpty" class="empty-state">
                <span class="material-symbols-outlined">rocket_launch</span>
                <strong>还没有发布计划</strong>
                <p>创建一个计划后，可以在这里执行预检、提交和取消。</p>
              </div>
              <div v-else class="task-list">
                <button
                  v-for="plan in filteredPlans"
                  :key="plan.id"
                  class="task-card"
                  :class="{
                    'is-selected': selectedPlanId === plan.id,
                    'is-blocked': isPlanBlocked(plan)
                  }"
                  @click="selectedPlanId = plan.id"
                >
                  <div class="tc-head">
                    <div class="tc-title">
                      <strong>{{ plan.title || "未命名计划" }}</strong>
                      <span>{{ plan.status }}</span>
                    </div>
                    <Chip size="sm" :variant="planStatusTone(plan)">{{ planStatusLabel(plan) }}</Chip>
                  </div>
                  <div class="tc-meta">
                    <span>账号: {{ plan.accountLabel }}</span>
                    <span>项目: {{ plan.projectLabel }}</span>
                  </div>
                  <div class="tc-meta">
                    <span>视频: {{ plan.videoAssetLabel }}</span>
                    <span>定时: {{ plan.scheduledAtLabel }}</span>
                  </div>
                </button>
              </div>
            </div>
          </Card>
        </aside>

        <main class="workspace-main">
          <Card class="detail-card h-full scroll-area" v-if="selectedPlan">
            <div class="detail-card__header">
              <div>
                <p class="eyebrow">当前计划</p>
                <h3>{{ selectedPlan.title || "未命名计划" }}</h3>
                <p class="summary">账号 {{ selectedPlan.accountLabel }}，项目 {{ selectedPlan.projectLabel }}，视频 {{ selectedPlan.videoAssetLabel }}。</p>
              </div>
              <div class="actions">
                <Chip :variant="planStatusTone(selectedPlan)">{{ planStatusLabel(selectedPlan) }}</Chip>
                <Button variant="secondary" :disabled="isActionDisabled" @click="handlePrecheck">执行预检</Button>
                <Button variant="primary" :disabled="isSubmitDisabled" @click="handleSubmit">提交发布</Button>
                <Button variant="danger" :disabled="isBusy" @click="handleCancel">取消计划</Button>
              </div>
            </div>

            <div class="detail-card__body">
              <div class="metric-grid cols-4">
                <div class="metric-card">
                  <span>绑定账号</span>
                  <strong>{{ selectedPlan.accountLabel }}</strong>
                </div>
                <div class="metric-card">
                  <span>绑定项目</span>
                  <strong>{{ selectedPlan.projectLabel }}</strong>
                </div>
                <div class="metric-card">
                  <span>预检结果</span>
                  <strong>{{ precheckSummaryLabel }}</strong>
                </div>
                <div class="metric-card">
                  <span>阻断语义</span>
                  <strong>{{ selectedPlanBlockReason }}</strong>
                </div>
              </div>

              <div class="lane">
                <div class="lane-head">
                  <h4>发布绑定</h4>
                  <Chip size="sm">{{ selectedPlan.status }}</Chip>
                </div>
                <div class="config-grid cols-2">
                  <div class="cfg-row"><span>账号 ID</span><strong>{{ selectedPlan.account_id || "未绑定" }}</strong></div>
                  <div class="cfg-row"><span>账号名称</span><strong>{{ selectedPlan.account_name || "未绑定" }}</strong></div>
                  <div class="cfg-row"><span>项目 ID</span><strong>{{ selectedPlan.project_id || "未绑定" }}</strong></div>
                  <div class="cfg-row"><span>视频素材 ID</span><strong>{{ selectedPlan.video_asset_id || "未绑定" }}</strong></div>
                  <div class="cfg-row"><span>定时发布</span><strong>{{ selectedPlan.scheduled_at ? formatDateTime(selectedPlan.scheduled_at) : "立即发布" }}</strong></div>
                </div>
              </div>

              <div class="lane">
                <div class="lane-head">
                  <h4>预检结果</h4>
                  <Chip size="sm">{{ precheckItems.length }} 项</Chip>
                </div>
                <div v-if="precheckItems.length === 0" class="lane-empty">还没有执行预检，先点“执行预检”读取真实结果。</div>
                <div v-else class="check-list">
                  <div v-for="item in precheckItems" :key="item.code" class="check-item" :class="item.result">
                    <span class="material-symbols-outlined check-icon">{{ checkIcon(item.result) }}</span>
                    <div class="check-content">
                      <strong>{{ item.label }}</strong>
                      <p>{{ item.message || "无额外说明" }}</p>
                    </div>
                    <Chip size="sm" :variant="precheckTone(item.result)">{{ item.result }}</Chip>
                  </div>
                </div>
              </div>

              <div class="lane">
                <div class="lane-head">
                  <h4>提交回执</h4>
                  <Chip size="sm">{{ receiptLabel }}</Chip>
                </div>
                <div v-if="receipt === null" class="lane-empty">提交后，这里会显示 Runtime 返回的真实回执。</div>
                <div v-else class="config-grid">
                  <div class="cfg-row"><span>状态</span><strong>{{ receipt.status }}</strong></div>
                  <div class="cfg-row"><span>说明</span><strong>{{ receipt.message || "无" }}</strong></div>
                  <div class="cfg-row" v-if="receipt.error"><span>错误</span><strong>{{ receipt.error }}</strong></div>
                </div>
              </div>
            </div>
          </Card>
          
          <Card class="detail-card empty-wrapper" v-else>
            <div class="empty-state">
              <span class="material-symbols-outlined">assignment</span>
              <strong>选择一个发布计划查看预检和提交链路</strong>
              <p>这里会显示绑定、阻断和回执，不再只是一张列表。</p>
            </div>
          </Card>
        </main>
      </div>

      <!-- Drawer Modal -->
      <transition name="drawer">
        <div v-if="showAddPlan" class="drawer-overlay" @click.self="showAddPlan = false">
          <aside class="drawer-panel" @click.stop>
            <div class="drawer-panel__header">
              <div>
                <p class="drawer-panel__eyebrow">新建计划</p>
                <h2>创建发布计划</h2>
              </div>
              <button class="drawer-panel__close" @click="showAddPlan = false">
                <span class="material-symbols-outlined">close</span>
              </button>
            </div>
            <div class="drawer-panel__body">
              <form class="drawer-form" @submit.prevent="handleCreatePlan">
                <div class="form-group">
                  <label>计划标题</label>
                  <input v-model="addForm.title" type="text" placeholder="例如：TikTok 周更视频发布" class="ui-input-field" required />
                </div>
                <div class="form-group">
                  <label>账号名称</label>
                  <input v-model="addForm.accountName" type="text" placeholder="账号昵称或 ID" class="ui-input-field" />
                </div>
                <div class="form-group">
                  <label>账号 ID</label>
                  <input v-model="addForm.accountId" type="text" placeholder="account-1" class="ui-input-field" />
                </div>
                <div class="form-group">
                  <label>项目 ID</label>
                  <input v-model="addForm.projectId" type="text" :placeholder="currentProjectIdPlaceholder" class="ui-input-field" />
                </div>
                <div class="form-group">
                  <label>视频素材 ID</label>
                  <input v-model="addForm.videoAssetId" type="text" placeholder="asset-1" class="ui-input-field" />
                </div>
                <div class="form-group">
                  <label>定时发布</label>
                  <input v-model="addForm.scheduledAt" type="datetime-local" class="ui-input-field" />
                </div>
                <div class="drawer-actions">
                  <Button variant="ghost" @click="showAddPlan = false">取消</Button>
                  <Button variant="primary" type="submit" :disabled="isBusy">保存计划</Button>
                </div>
              </form>
            </div>
          </aside>
        </div>
      </transition>
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

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

type PublishPlanView = PublishPlanDto & { accountLabel: string; projectLabel: string; scheduledAtLabel: string; videoAssetLabel: string; };
type StatusFilterValue = "all" | "draft" | "ready" | "submitting" | "published" | "failed" | "cancelled";

const publishingStore = usePublishingStore();
const projectStore = useProjectStore();
const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();

const selectedPlanId = ref<string | null>(null);
const statusFilter = ref<StatusFilterValue>("all");
const showAddPlan = ref(false);
const addForm = ref({ title: "", accountName: "", accountId: "", projectId: "", videoAssetId: "", scheduledAt: "" });

const plans = computed<PublishPlanView[]>(() =>
  publishingStore.plans.map((plan) => ({
    ...plan,
    accountLabel: plan.account_name || plan.account_id || "未绑定",
    projectLabel: plan.project_id || "未绑定",
    scheduledAtLabel: plan.scheduled_at ? formatDateTime(plan.scheduled_at) : "立即发布",
    videoAssetLabel: plan.video_asset_id || "未绑定"
  }))
);

const currentProjectLabel = computed(() => projectStore.currentProject?.projectName || projectStore.currentProject?.projectId || "未选择");
const currentProjectIdPlaceholder = computed(() => projectStore.currentProject?.projectId || "project-1");
const licenseLabel = computed(() => (licenseStore.active ? "授权已激活" : "授权未激活"));
const configSyncLabel = computed(() => {
  if (configBusStore.status === "saving") return "同步中";
  if (configBusStore.status === "error") return "同步异常";
  return configBusStore.runtimeStatus === "online" ? "在线" : "离线";
});

const workflowStateLabel = computed(() => {
  switch (publishingStore.workflowState) {
    case "checking": return "预检中";
    case "submitting": return "提交中";
    case "blocked": return "已阻断";
    case "error": return "异常";
    case "ready": return "就绪";
    default: return "空闲";
  }
});

const statusFilters: Array<{ label: string; value: StatusFilterValue }> = [
  { label: "全部", value: "all" }, { label: "草稿", value: "draft" }, { label: "就绪", value: "ready" },
  { label: "提交中", value: "submitting" }, { label: "已发布", value: "published" },
  { label: "失败", value: "failed" }, { label: "已取消", value: "cancelled" }
];

const filteredPlans = computed(() => {
  if (statusFilter.value === "all") return plans.value;
  return plans.value.filter((plan) => plan.status === statusFilter.value);
});

const selectedPlan = computed(() => plans.value.find((plan) => plan.id === selectedPlanId.value) ?? null);
const draftPlanCount = computed(() => plans.value.filter((plan) => plan.status === "draft").length);
const blockedPlanCount = computed(() => plans.value.filter((plan) => isPlanBlocked(plan) || plan.status === "failed").length);
const isLoading = computed(() => publishingStore.loading);
const isEmpty = computed(() => publishingStore.viewState === "empty" && !isLoading.value);
const isBusy = computed(() => isLoading.value || publishingStore.workflowState === "checking" || publishingStore.workflowState === "submitting");
const isActionDisabled = computed(() => !selectedPlan.value || isBusy.value || isPlanBlocked(selectedPlan.value));
const isSubmitDisabled = computed(() => !selectedPlan.value || isBusy.value || selectedPlan.value.status === "published" || selectedPlan.value.status === "cancelled" || Boolean(selectedPlanBlockReason.value));

const precheckResult = computed<PrecheckResultDto | null>(() => publishingStore.precheckResult);
const precheckItems = computed(() => precheckResult.value?.items ?? []);
const receipt = computed(() =>
  publishingStore.submitResult ? { status: publishingStore.submitResult.status, message: publishingStore.submitResult.message, error: publishingStore.error ?? null } : publishingStore.error ? { status: "failed", message: "", error: publishingStore.error } : null
);
const receiptLabel = computed(() => receipt.value ? receipt.value.status : publishingStore.workflowState === "submitting" ? "提交中" : "未提交");

const precheckSummaryLabel = computed(() => {
  if (!precheckResult.value) return "未执行";
  const passed = precheckItems.value.filter((item) => item.result === "passed").length;
  const failed = precheckItems.value.filter((item) => item.result === "failed").length;
  return `${passed} 通过 / ${failed} 阻断`;
});

const selectedPlanBlockReason = computed(() => {
  if (!selectedPlan.value) return "未选择计划";
  if (selectedPlan.value.status === "published") return "计划已经发布";
  if (selectedPlan.value.status === "cancelled") return "计划已经取消";
  if (!selectedPlan.value.account_id && !selectedPlan.value.account_name) return "账号尚未绑定";
  if (!selectedPlan.value.project_id) return "项目尚未绑定";
  if (!selectedPlan.value.video_asset_id) return "视频素材尚未绑定";
  if (precheckResult.value?.has_errors) return "预检结果存在阻断项";
  if (publishingStore.workflowState === "blocked") return "Runtime 已标记为阻断";
  return "可继续提交";
});

onMounted(() => { void publishingStore.loadPlans(); });

watch(() => plans.value.map((plan) => plan.id).join("|"), () => {
  if (!selectedPlanId.value && plans.value.length > 0) selectedPlanId.value = plans.value[0].id;
}, { immediate: true });

function isPlanBlocked(plan: PublishPlanView) {
  return !plan.account_id || !plan.project_id || !plan.video_asset_id || plan.status === "failed" || Boolean(plan.error_message);
}

function planStatusTone(plan: PublishPlanView) {
  if (plan.status === "published") return "success";
  if (plan.status === "failed") return "danger";
  if (plan.status === "submitting") return "brand";
  if (isPlanBlocked(plan)) return "warning";
  return "neutral";
}

function planStatusLabel(plan: PublishPlanView) {
  if (plan.status === "draft") return "草稿";
  if (plan.status === "ready") return "可提交";
  if (plan.status === "submitting") return "提交中";
  if (plan.status === "published") return "已发布";
  if (plan.status === "cancelled") return "已取消";
  if (plan.status === "failed") return "失败";
  return plan.status;
}

function precheckTone(result: PrecheckItemResult["result"]) {
  if (result === "passed") return "success";
  if (result === "failed") return "danger";
  if (result === "pending") return "neutral";
  return "warning";
}

function checkIcon(result: PrecheckItemResult["result"]) {
  if (result === "passed") return "check_circle";
  if (result === "failed") return "cancel";
  return "radio_button_unchecked";
}

async function handlePrecheck() {
  if (!selectedPlan.value || isBusy.value) return;
  await publishingStore.precheck(selectedPlan.value.id);
}

async function handleSubmit() {
  if (!selectedPlan.value || isSubmitDisabled.value) return;
  await publishingStore.submit(selectedPlan.value.id);
}

async function handleCancel() {
  if (!selectedPlan.value || isBusy.value) return;
  await publishingStore.cancel(selectedPlan.value.id);
}

async function handleCreatePlan() {
  if (!addForm.value.title.trim()) return;
  const input: PublishPlanCreateInput = {
    title: addForm.value.title.trim(), account_name: addForm.value.accountName.trim() || null, account_id: addForm.value.accountId.trim() || null,
    project_id: addForm.value.projectId.trim() || null, video_asset_id: addForm.value.videoAssetId.trim() || null, scheduled_at: addForm.value.scheduledAt || null
  };
  const plan = await publishingStore.addPlan(input);
  if (!plan) return;
  selectedPlanId.value = plan.id;
  addForm.value = { title: "", accountName: "", accountId: "", projectId: projectStore.currentProject?.projectId || "", videoAssetId: "", scheduledAt: "" };
  showAddPlan.value = false;
}

function formatDateTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : `${date.toLocaleDateString("zh-CN")} ${date.toLocaleTimeString("zh-CN", { hour12: false, hour: "2-digit", minute: "2-digit" })}`;
}

watch(() => projectStore.currentProject?.projectId, (projectId) => {
  if (!addForm.value.projectId && projectId) addForm.value.projectId = projectId;
}, { immediate: true });
</script>

<style scoped>
.page-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-8) var(--space-8);
  display: flex;
  flex-direction: column;
}

.page-header {
  display: grid;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.page-header__crumb {
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.page-header__row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.page-header__title {
  font: var(--font-display-md);
  letter-spacing: var(--ls-display-md);
  color: var(--color-text-primary);
  margin: 0 0 4px 0;
}

.page-header__subtitle {
  font: var(--font-body-md);
  letter-spacing: var(--ls-body-md);
  color: var(--color-text-secondary);
}

.publishing-context {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: var(--space-4);
}

.dashboard-alert {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-muted);
  line-height: 1.6;
  margin-bottom: var(--space-4);
  font: var(--font-body-sm);
  display: flex;
  align-items: center;
  gap: 8px;
}

.dashboard-alert[data-tone="danger"] { border-color: rgba(255, 90, 99, 0.20); background: rgba(255, 90, 99, 0.08); color: var(--color-danger); }
.dashboard-alert[data-tone="warning"] { border-color: rgba(245, 183, 64, 0.20); background: rgba(245, 183, 64, 0.08); color: var(--color-warning); }
.dashboard-alert[data-tone="brand"] { border-color: rgba(0, 188, 212, 0.20); background: rgba(0, 188, 212, 0.08); color: var(--color-brand-primary); }

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.summary-card {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sc-label {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.sc-val {
  font: var(--font-title-md);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(320px, 360px) minmax(0, 1fr);
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
}

.workspace-rail {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-height: 0;
}

.rail-card {
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.h-full { height: 100%; }

.rail-card__header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
}

.rail-card__header h3 {
  margin: 0;
  font: var(--font-title-md);
  color: var(--color-text-primary);
}

.flex-col { display: flex; flex-direction: column; }
.align-start { align-items: flex-start; }
.gap-3 { gap: var(--space-3); }

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.rail-card__body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  background: var(--color-bg-canvas);
}

.rail-card__body.no-padding { padding: 0; }
.scroll-area { overflow-y: auto; }

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-10) var(--space-4);
  color: var(--color-text-tertiary);
  gap: 8px;
}

.empty-state .material-symbols-outlined {
  font-size: 32px;
  color: var(--color-text-secondary);
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.task-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: var(--space-4);
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--color-border-subtle);
  cursor: pointer;
  text-align: left;
  transition: background-color var(--motion-fast) var(--ease-standard);
}

.task-card:hover { background: var(--color-bg-hover); }

.task-card.is-selected {
  background: color-mix(in srgb, var(--color-brand-primary) 8%, var(--color-bg-surface));
  border-left: 3px solid var(--color-brand-primary);
  padding-left: calc(var(--space-4) - 3px);
}

.task-card.is-blocked { border-color: rgba(245, 183, 64, 0.3); }

.tc-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.tc-title {
  display: flex;
  flex-direction: column;
}

.tc-title strong { font: var(--font-title-sm); color: var(--color-text-primary); }
.tc-title span { font: var(--font-caption); color: var(--color-text-secondary); }

.tc-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.workspace-main {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.detail-card {
  padding: 0;
  display: flex;
  flex-direction: column;
}

.detail-card__header {
  padding: var(--space-5);
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.eyebrow {
  margin: 0 0 4px 0;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.detail-card__header h3 {
  margin: 0 0 4px 0;
  font: var(--font-title-lg);
  color: var(--color-text-primary);
}

.summary {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail-card__body {
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  overflow-y: auto;
}

.metric-grid {
  display: grid;
  gap: 10px;
}

.cols-4 { grid-template-columns: repeat(4, 1fr); }
.cols-2 { grid-template-columns: repeat(2, 1fr); }

.metric-card {
  padding: var(--space-4);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-card span { font: var(--font-caption); color: var(--color-text-tertiary); }
.metric-card strong { font: var(--font-body-md); color: var(--color-text-primary); }

.lane {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.lane-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.lane-head h4 {
  margin: 0;
  font: var(--font-title-sm);
  color: var(--color-text-primary);
}

.lane-empty {
  padding: var(--space-4);
  text-align: center;
  color: var(--color-text-tertiary);
  font: var(--font-body-sm);
  background: var(--color-bg-muted);
  border-radius: var(--radius-sm);
}

.config-grid { display: flex; flex-direction: column; gap: 8px; }
.config-grid.cols-2 { display: grid; grid-template-columns: 1fr 1fr; }
.cfg-row { display: flex; flex-direction: column; gap: 4px; padding: 12px; background: var(--color-bg-muted); border-radius: var(--radius-sm); }
.cfg-row span { font: var(--font-caption); color: var(--color-text-tertiary); }
.cfg-row strong { font: var(--font-body-md); color: var(--color-text-primary); }

.check-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: var(--space-3);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  background: var(--color-bg-canvas);
}

.check-item.passed { border-color: rgba(34, 211, 154, 0.4); }
.check-item.failed { border-color: rgba(255, 90, 99, 0.4); }

.check-icon { font-size: 18px; color: var(--color-brand-primary); }
.check-item.failed .check-icon { color: var(--color-danger); }

.check-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.check-content strong { font: var(--font-body-sm); color: var(--color-text-primary); }
.check-content p { margin: 0; font: var(--font-caption); color: var(--color-text-secondary); }

.empty-wrapper { flex: 1; justify-content: center; }

.drawer-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-bg-overlay);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: 420px;
  background: var(--color-bg-surface);
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.drawer-panel__header {
  padding: var(--space-5);
  border-bottom: 1px solid var(--color-border-subtle);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.drawer-panel__eyebrow {
  margin: 0 0 4px 0;
  font: var(--font-caption);
  color: var(--color-brand-primary);
  text-transform: uppercase;
}

.drawer-panel__header h2 { margin: 0; font: var(--font-title-lg); color: var(--color-text-primary); }

.drawer-panel__close {
  background: transparent;
  border: none;
  color: var(--color-text-tertiary);
  cursor: pointer;
  padding: 4px;
}

.drawer-panel__body {
  padding: var(--space-6);
  flex: 1;
  overflow-y: auto;
}

.drawer-form { display: flex; flex-direction: column; gap: var(--space-4); }
.form-group { display: flex; flex-direction: column; gap: 8px; }
.form-group label { font: var(--font-caption); color: var(--color-text-secondary); }

.ui-input-field {
  height: 38px;
  padding: 0 12px;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
  font: var(--font-body-md);
  outline: none;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.drawer-enter-active, .drawer-leave-active { transition: opacity 160ms ease; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }

@media (max-width: 1200px) {
  .workspace-grid { grid-template-columns: 1fr; }
  .metric-grid.cols-4 { grid-template-columns: repeat(2, 1fr); }
  .config-grid.cols-2 { grid-template-columns: 1fr; }
}
</style>
