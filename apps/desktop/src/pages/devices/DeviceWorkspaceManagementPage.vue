<template>
  <div class="page-container h-full">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 账号与设备</div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">设备与工作区管理</h1>
          <div class="page-header__subtitle">页面只管理 Runtime 返回的真实工作区对象、健康检查和本地路径，不包装高风险能力，也不伪造浏览器实例。</div>
        </div>
        <div class="page-header__actions">
          <Button variant="secondary" @click="handleReload" :disabled="deviceWorkspacesStore.loading">
            <template #leading><span class="material-symbols-outlined">refresh</span></template>
            重新拉取
          </Button>
          <Button variant="primary" @click="isCreating = true" :disabled="deviceWorkspacesStore.loading">
            <template #leading><span class="material-symbols-outlined">add</span></template>
            新建工作区
          </Button>
        </div>
      </div>
    </header>

    <div v-if="deviceWorkspacesStore.error" class="dashboard-alert" data-tone="danger">
      <span class="material-symbols-outlined">error</span>
      <span>{{ deviceWorkspacesStore.error }}</span>
    </div>
    <div v-else-if="deviceWorkspacesStore.loading" class="dashboard-alert" data-tone="brand">
      <span class="material-symbols-outlined spinning">sync</span>
      <span>正在读取真实工作区对象和健康状态...</span>
    </div>
    <div v-else-if="workspaces.length === 0" class="dashboard-alert" data-tone="warning">
      <span class="material-symbols-outlined">warning</span>
      <span>Runtime 暂时没有返回工作区对象。页面不会伪造设备在线率或浏览器实例。</span>
    </div>

    <div class="summary-grid">
      <Card class="summary-card">
        <span class="sc-label">工作区总数</span>
        <strong class="sc-val">{{ workspaces.length }}</strong>
        <p class="sc-hint">Runtime 返回的真实工作区</p>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">当前选中</span>
        <strong class="sc-val">{{ selectedWorkspace ? selectedWorkspace.name : "未选中" }}</strong>
        <p class="sc-hint">{{ selectedWorkspace ? selectedWorkspace.status : "请选择左侧工作区继续查看" }}</p>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">最近检查</span>
        <strong class="sc-val">{{ deviceWorkspacesStore.lastHealthCheck ? statusLabel(deviceWorkspacesStore.lastHealthCheck.status) : "未检查" }}</strong>
        <p class="sc-hint">{{ deviceWorkspacesStore.lastHealthCheck ? deviceWorkspacesStore.lastHealthCheck.checked_at : "暂无健康检查记录" }}</p>
      </Card>
      <Card class="summary-card">
        <span class="sc-label">真实边界</span>
        <strong class="sc-val">浏览器实例 / 执行绑定</strong>
        <p class="sc-hint">仅保留空态和 blocked 说明，不伪造数据</p>
      </Card>
    </div>

    <div class="workspace-grid">
      <aside class="workspace-rail">
        <Card class="rail-card">
          <div class="rail-card__header">
            <h3>工作区列表</h3>
          </div>
          <div class="rail-card__body">
            <div class="search-box">
              <span class="material-symbols-outlined">search</span>
              <input v-model="searchQuery" type="search" placeholder="搜索工作区名称或路径" />
            </div>
            <p class="rail-card__hint">
              工作区对象只包含名称、根路径、状态、错误数和最近使用时间，不包含浏览器实例假数据。
            </p>
          </div>
        </Card>

        <Card class="rail-card flex-1">
          <div class="rail-card__header">
            <h3>{{ workspaces.length }} 个真实工作区</h3>
            <Chip size="sm" variant="brand">{{ visibleWorkspaces.length }}</Chip>
          </div>
          <div class="rail-card__body no-padding scroll-area">
            <div v-if="deviceWorkspacesStore.loading" class="empty-state">
              <span class="material-symbols-outlined spinning">sync</span>
              <strong>正在加载工作区</strong>
              <p>同步 Runtime 中的真实工作区对象。</p>
            </div>
            <div v-else-if="visibleWorkspaces.length === 0" class="empty-state">
              <span class="material-symbols-outlined">lan_off</span>
              <strong>没有符合条件的工作区</strong>
              <p>可以清空搜索，或先创建一个真实工作区对象。</p>
            </div>
            <div v-else class="workspace-list">
              <button
                v-for="workspace in visibleWorkspaces"
                :key="workspace.id"
                class="workspace-card"
                :class="{ 'is-selected': selectedWorkspaceId === workspace.id }"
                @click="selectWorkspace(workspace)"
              >
                <div class="wc-dot" :class="workspace.status" />
                <div class="wc-content">
                  <strong :title="workspace.name">{{ workspace.name }}</strong>
                  <span :title="workspace.root_path">{{ workspace.root_path }}</span>
                  <span class="wc-time">最后使用：{{ workspace.last_used_at ? formatDateTime(workspace.last_used_at) : "从未" }}</span>
                </div>
                <Chip v-if="workspace.error_count > 0" size="sm" variant="danger">{{ workspace.error_count }}</Chip>
              </button>
            </div>
          </div>
        </Card>
      </aside>

      <main class="workspace-main">
        <Card class="detail-card">
          <div class="detail-card__header">
            <div>
              <h3>{{ selectedWorkspace ? selectedWorkspace.name : "未选中工作区" }}</h3>
              <p class="summary">{{ selectedWorkspace ? "选中后会同步打开右侧详情面板并保留真实健康检查结果。" : "在左侧选择一个工作区，查看根路径、状态和真实健康记录。" }}</p>
            </div>
            <div class="actions" v-if="selectedWorkspace">
              <Button variant="secondary" @click="handleHealthCheck" :disabled="deviceWorkspacesStore.loading">
                <template #leading><span class="material-symbols-outlined">health_and_safety</span></template>
                健康检查
              </Button>
              <Button variant="danger" @click="handleDelete">删除</Button>
            </div>
          </div>

          <div class="detail-card__body" v-if="selectedWorkspace">
            <div class="status-row">
              <div>
                <span class="status-row__label">状态</span>
                <strong>{{ statusLabel(selectedWorkspace.status) }}</strong>
              </div>
              <Chip :variant="statusTone(selectedWorkspace.status)">{{ selectedWorkspace.status }}</Chip>
            </div>

            <dl class="detail-metadata">
              <div><dt>根路径</dt><dd>{{ selectedWorkspace.root_path }}</dd></div>
              <div><dt>错误次数</dt><dd>{{ selectedWorkspace.error_count }}</dd></div>
              <div><dt>创建时间</dt><dd>{{ formatDateTime(selectedWorkspace.created_at) }}</dd></div>
              <div><dt>更新时间</dt><dd>{{ formatDateTime(selectedWorkspace.updated_at) }}</dd></div>
              <div><dt>最近使用</dt><dd>{{ selectedWorkspace.last_used_at ? formatDateTime(selectedWorkspace.last_used_at) : "从未" }}</dd></div>
              <div><dt>工作区 ID</dt><dd>{{ selectedWorkspace.id }}</dd></div>
            </dl>

            <div class="detail-block">
              <div class="detail-block__header">
                <span>浏览器实例</span>
                <Chip size="sm" variant="neutral">empty</Chip>
              </div>
              <p class="detail-empty">当前 Runtime 尚未返回浏览器实例列表。这里仅保留空态，不包装任何伪造实例或假在线状态。</p>
            </div>

            <div class="detail-block detail-block--blocked">
              <div class="detail-block__header">
                <span>执行边界</span>
                <Chip size="sm" variant="warning">blocked</Chip>
              </div>
              <p class="detail-empty">当前 Runtime 尚未返回账号到工作区的执行绑定关系。页面只展示真实工作区对象，不扩展高风险能力。</p>
            </div>

            <div class="detail-actions">
              <Button variant="primary" @click="openSelectedWorkspaceDetail">打开右侧详情</Button>
              <Button variant="ghost" @click="clearSelection">清空选择</Button>
            </div>
          </div>

          <div class="detail-card__body empty-wrapper" v-else>
            <div class="empty-state">
              <span class="material-symbols-outlined">lan</span>
              <strong>未选中工作区</strong>
              <p>在左侧选择一个真实工作区对象，右侧会展示状态、路径和健康记录。</p>
            </div>
          </div>
        </Card>

        <Card class="detail-card soft-card">
          <div class="detail-block__header"><span>当前边界</span></div>
          <p class="detail-note">工作区页不会包装账号自动化、远程浏览器控制或执行环境伪对象，只保留本地真实工作区与健康检查。</p>
        </Card>
      </main>
    </div>

    <!-- Drawer Modal -->
    <transition name="drawer">
      <div v-if="isCreating" class="drawer-overlay" @click="isCreating = false">
        <aside class="drawer-panel" @click.stop>
          <div class="drawer-panel__header">
            <div>
              <p class="drawer-panel__eyebrow">新建工作区</p>
              <h2>创建真实工作区对象</h2>
            </div>
            <button class="drawer-panel__close" @click="isCreating = false">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <div class="drawer-panel__body">
            <form class="drawer-form" @submit.prevent="handleCreate">
              <div class="form-group">
                <label>工作区名称</label>
                <input v-model="form.name" type="text" placeholder="例：PC-01-工作室" class="ui-input-field" required />
              </div>
              <div class="form-group">
                <label>根路径</label>
                <input v-model="form.root_path" type="text" placeholder="C:\\Users\\Admin\\TK-Workspace" class="ui-input-field" required />
              </div>
              <p class="drawer-form__hint">这里只写入真实本地目录，不会自动生成浏览器实例、执行绑定或高风险能力。</p>
              <div class="drawer-actions">
                <Button variant="ghost" @click="isCreating = false">取消</Button>
                <Button variant="primary" type="submit" :disabled="!form.name || !form.root_path || deviceWorkspacesStore.loading">保存工作区</Button>
              </div>
            </form>
          </div>
        </aside>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import { useDeviceWorkspacesStore } from "@/stores/device-workspaces";
import type { DeviceWorkspaceDto } from "@/types/runtime";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const deviceWorkspacesStore = useDeviceWorkspacesStore();
const shellUiStore = useShellUiStore();
const searchQuery = ref("");
const selectedWorkspaceId = ref<string | null>(null);
const isCreating = ref(false);
const form = reactive({ name: "", root_path: "" });
const workspaces = computed(() => deviceWorkspacesStore.workspaces);

const visibleWorkspaces = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return deviceWorkspacesStore.workspaces;
  return deviceWorkspacesStore.workspaces.filter((workspace) => {
    return workspace.name.toLowerCase().includes(query) || workspace.root_path.toLowerCase().includes(query);
  });
});

const selectedWorkspace = computed(() => deviceWorkspacesStore.workspaces.find((w) => w.id === selectedWorkspaceId.value) ?? null);

watch(selectedWorkspace, (workspace) => {
  if (!workspace) {
    shellUiStore.clearDetailContext("binding");
    shellUiStore.closeDetailPanel();
    return;
  }
  shellUiStore.openDetailWithContext(buildWorkspaceDetailContext(workspace));
}, { immediate: true });

onMounted(() => { void deviceWorkspacesStore.loadWorkspaces(); });
onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("binding");
  shellUiStore.closeDetailPanel();
});

function handleReload() { void deviceWorkspacesStore.loadWorkspaces(); }
function selectWorkspace(workspace: DeviceWorkspaceDto) { selectedWorkspaceId.value = workspace.id; }
function clearSelection() {
  selectedWorkspaceId.value = null;
  shellUiStore.clearDetailContext("binding");
  shellUiStore.closeDetailPanel();
}

function openSelectedWorkspaceDetail() {
  if (!selectedWorkspace.value) return;
  shellUiStore.openDetailWithContext(buildWorkspaceDetailContext(selectedWorkspace.value));
}

async function handleCreate() {
  if (!form.name || !form.root_path) return;
  const workspace = await deviceWorkspacesStore.addWorkspace({ name: form.name.trim(), root_path: form.root_path.trim() });
  if (!workspace) return;
  selectedWorkspaceId.value = workspace.id;
  form.name = ""; form.root_path = "";
  isCreating.value = false;
}

async function handleHealthCheck() {
  if (!selectedWorkspace.value) return;
  await deviceWorkspacesStore.checkHealth(selectedWorkspace.value.id);
}

async function handleDelete() {
  if (!selectedWorkspace.value) return;
  if (!window.confirm(`确认删除工作区“${selectedWorkspace.value.name}”吗？`)) return;
  const deletedId = selectedWorkspace.value.id;
  await deviceWorkspacesStore.removeWorkspace(deletedId);
  if (selectedWorkspaceId.value === deletedId) clearSelection();
}

function buildWorkspaceDetailContext(workspace: DeviceWorkspaceDto) {
  return createRouteDetailContext("binding", {
    icon: "lan", eyebrow: "工作区详情", title: workspace.name, description: "只展示 Runtime 返回的真实工作区对象、状态和健康检查记录。",
    badge: { label: statusLabel(workspace.status), tone: workspace.status === "online" || workspace.status === "running" ? "success" : workspace.status === "error" ? "danger" : "neutral" },
    metrics: [
      { id: "errors", label: "错误次数", value: String(workspace.error_count), hint: "真实字段" },
      { id: "status", label: "状态", value: statusLabel(workspace.status), hint: "来自 Runtime" },
      { id: "last-used", label: "最近使用", value: workspace.last_used_at ? formatDateTime(workspace.last_used_at) : "从未", hint: "真实时间" }
    ],
    sections: [
      { id: "workspace", title: "工作区信息", fields: [
          { id: "name", label: "名称", value: workspace.name },
          { id: "root", label: "根路径", value: workspace.root_path, mono: true, multiline: true },
          { id: "status", label: "状态", value: statusLabel(workspace.status) },
          { id: "errors", label: "错误次数", value: String(workspace.error_count) },
          { id: "created", label: "创建时间", value: formatDateTime(workspace.created_at), mono: true },
          { id: "updated", label: "更新时间", value: formatDateTime(workspace.updated_at), mono: true }
      ]},
      { id: "browser-instances", title: "浏览器实例", emptyLabel: "Runtime 暂时没有返回浏览器实例列表，保持空态，不伪造实例。" },
      { id: "binding", title: "执行绑定", emptyLabel: "Runtime 暂时没有返回执行绑定关系，页面只保留真实工作区对象。" }
    ],
    actions: [
      { id: "health-check", label: "健康检查", icon: "health_and_safety", tone: "brand" },
      { id: "clear", label: "清空选择", icon: "close", tone: "neutral" }
    ]
  });
}

function statusTone(status: string): "success" | "danger" | "neutral" {
  if (status === "online" || status === "running") return "success";
  if (status === "error") return "danger";
  return "neutral";
}

function statusLabel(status: string) {
  switch (status) {
    case "online": return "在线";
    case "offline": return "离线";
    case "running": return "运行中";
    case "error": return "异常";
    default: return status || "未知";
  }
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false, hourCycle: "h23"
  }).formatToParts(date);
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")} ${part("hour")}:${part("minute")}:${part("second")}`;
}
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

.page-header__actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
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

.sc-hint {
  font: var(--font-caption);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
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

.flex-1 { flex: 1; }

.rail-card__header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.rail-card__header h3 {
  margin: 0;
  font: var(--font-title-md);
  color: var(--color-text-primary);
}

.rail-card__body {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.rail-card__body.no-padding { padding: 0; }
.scroll-area { overflow-y: auto; }

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  padding: 0 10px;
  height: 36px;
}

.search-box input {
  background: transparent;
  border: none;
  color: var(--color-text-primary);
  outline: none;
  flex: 1;
  font: var(--font-body-md);
}

.rail-card__hint {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
}

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

.spinning { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

.workspace-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.workspace-card {
  display: flex;
  gap: 12px;
  padding: var(--space-4);
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--color-border-subtle);
  cursor: pointer;
  text-align: left;
  transition: background-color var(--motion-fast) var(--ease-standard);
  align-items: flex-start;
}

.workspace-card:hover { background: var(--color-bg-hover); }

.workspace-card.is-selected {
  background: color-mix(in srgb, var(--color-brand-primary) 8%, var(--color-bg-surface));
  border-left: 3px solid var(--color-brand-primary);
  padding-left: calc(var(--space-4) - 3px);
}

.wc-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 5px;
  background: var(--color-text-tertiary);
}

.wc-dot.online, .wc-dot.running { background: var(--color-success); }
.wc-dot.error { background: var(--color-danger); }

.wc-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  gap: 4px;
}

.wc-content strong {
  font: var(--font-title-sm);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wc-content span {
  font: var(--font-caption);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wc-time {
  color: var(--color-text-tertiary) !important;
}

.workspace-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
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

.detail-card__body {
  padding: var(--space-6);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.empty-wrapper { flex: 1; justify-content: center; }

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
}

.status-row__label {
  display: block;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  margin-bottom: 2px;
}

.status-row strong {
  font: var(--font-title-md);
  color: var(--color-text-primary);
}

.detail-metadata {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
  margin: 0;
}

.detail-metadata div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-metadata dt {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.detail-metadata dd {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-primary);
}

.detail-block {
  border-top: 1px solid var(--color-border-subtle);
  padding-top: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.detail-block__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.detail-block__header span {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.detail-empty, .detail-note {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
  line-height: 1.6;
}

.detail-block--blocked {
  background: color-mix(in srgb, var(--color-warning) 6%, transparent);
  border: 1px dashed color-mix(in srgb, var(--color-warning) 28%, var(--color-border-default));
  border-radius: var(--radius-md);
  padding: var(--space-4);
}

.detail-actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

.soft-card {
  background: color-mix(in srgb, var(--color-brand-primary) 4%, var(--color-bg-surface));
}

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

.drawer-panel__header h2 {
  margin: 0;
  font: var(--font-title-lg);
  color: var(--color-text-primary);
}

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

.drawer-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

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

.drawer-form__hint {
  margin: 0;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  line-height: 1.6;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.drawer-enter-active, .drawer-leave-active { 
  transition: opacity var(--motion-default) var(--ease-standard); 
}
.drawer-enter-from, .drawer-leave-to { 
  opacity: 0; 
}
.drawer-enter-active .drawer-panel, .drawer-leave-active .drawer-panel { 
  transition: transform var(--motion-default) var(--ease-spring); 
}
.drawer-enter-from .drawer-panel, .drawer-leave-to .drawer-panel { 
  transform: translateX(100%); 
}

@media (max-width: 1200px) {
  .workspace-grid { grid-template-columns: 1fr; }
  .summary-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
