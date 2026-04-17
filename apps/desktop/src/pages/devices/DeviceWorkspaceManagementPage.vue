<template>
  <section class="device-workspace-page">
    <header class="device-workspace-page__hero">
      <div class="device-workspace-page__hero-copy">
        <p class="device-workspace-page__eyebrow">设备与工作区 · 真实边界</p>
        <h1>设备与工作区管理</h1>
        <p>
          页面只管理 Runtime 返回的真实工作区对象、健康检查和本地路径，不包装高风险能力，也不伪造浏览器实例。
        </p>
      </div>

      <div class="device-workspace-page__hero-actions">
        <button class="device-workspace-page__button" type="button" @click="handleReload" :disabled="deviceWorkspacesStore.loading">
          <span class="material-symbols-outlined">refresh</span>
          重新拉取
        </button>
        <button class="device-workspace-page__button device-workspace-page__button--brand" type="button" @click="isCreating = true" :disabled="deviceWorkspacesStore.loading">
          <span class="material-symbols-outlined">add</span>
          新建工作区
        </button>
      </div>
    </header>

    <p v-if="deviceWorkspacesStore.error" class="device-workspace-page__banner device-workspace-page__banner--error">
      {{ deviceWorkspacesStore.error }}
    </p>
    <p v-else-if="deviceWorkspacesStore.loading" class="device-workspace-page__banner">
      正在读取真实工作区对象和健康状态。
    </p>
    <p v-else-if="workspaces.length === 0" class="device-workspace-page__banner device-workspace-page__banner--blocked">
      Runtime 暂时没有返回工作区对象。页面不会伪造设备在线率或浏览器实例。
    </p>

    <section class="device-workspace-page__summary">
      <article class="summary-card">
        <span>工作区总数</span>
        <strong>{{ workspaces.length }}</strong>
        <p>Runtime 返回的真实工作区</p>
      </article>
      <article class="summary-card">
        <span>当前选中</span>
        <strong>{{ selectedWorkspace ? selectedWorkspace.name : "未选中" }}</strong>
        <p>{{ selectedWorkspace ? selectedWorkspace.status : "请选择左侧工作区继续查看" }}</p>
      </article>
      <article class="summary-card">
        <span>最近检查</span>
        <strong>{{ deviceWorkspacesStore.lastHealthCheck ? statusLabel(deviceWorkspacesStore.lastHealthCheck.status) : "未检查" }}</strong>
        <p>{{ deviceWorkspacesStore.lastHealthCheck ? deviceWorkspacesStore.lastHealthCheck.checked_at : "暂无健康检查记录" }}</p>
      </article>
      <article class="summary-card">
        <span>真实边界</span>
        <strong>浏览器实例 / 执行绑定</strong>
        <p>仅保留空态和 blocked 说明，不伪造数据</p>
      </article>
    </section>

    <main class="device-workspace-page__body">
      <aside class="device-workspace-page__rail">
        <section class="rail-card">
          <div class="rail-card__header">
            <div>
              <p class="rail-card__eyebrow">工作区列表</p>
              <h2>{{ workspaces.length }} 个真实工作区</h2>
            </div>
          </div>

          <div class="search-box">
            <span class="material-symbols-outlined">search</span>
            <input v-model="searchQuery" type="search" placeholder="搜索工作区名称或路径" />
          </div>

          <p class="rail-card__hint">
            工作区对象只包含名称、根路径、状态、错误数和最近使用时间，不包含浏览器实例假数据。
          </p>
        </section>

        <section class="rail-card rail-card--list">
          <div v-if="deviceWorkspacesStore.loading" class="state-card">
            <span class="material-symbols-outlined state-card__spinner">sync</span>
            <strong>正在加载工作区</strong>
            <p>同步 Runtime 中的真实工作区对象。</p>
          </div>

          <div v-else-if="visibleWorkspaces.length === 0" class="state-card state-card--empty">
            <span class="material-symbols-outlined">lan_off</span>
            <strong>没有符合条件的工作区</strong>
            <p>可以清空搜索，或先创建一个真实工作区对象。</p>
          </div>

          <div v-else class="workspace-list">
            <button
              v-for="workspace in visibleWorkspaces"
              :key="workspace.id"
              :data-testid="`workspace-card-${workspace.id}`"
              class="workspace-card"
              :class="{ 'workspace-card--selected': selectedWorkspaceId === workspace.id }"
              type="button"
              @click="selectWorkspace(workspace)"
            >
              <div class="workspace-card__dot" :class="workspace.status" />
              <div class="workspace-card__content">
                <strong :title="workspace.name">{{ workspace.name }}</strong>
                <span :title="workspace.root_path">{{ workspace.root_path }}</span>
                <span>最后使用：{{ workspace.last_used_at ? formatDateTime(workspace.last_used_at) : "从未" }}</span>
              </div>
              <span v-if="workspace.error_count > 0" class="workspace-card__badge">{{ workspace.error_count }}</span>
            </button>
          </div>
        </section>
      </aside>

      <section class="device-workspace-page__detail">
        <article class="detail-card">
          <div class="detail-card__header">
            <div>
              <p class="detail-card__eyebrow">工作区详情</p>
              <h2>{{ selectedWorkspace ? selectedWorkspace.name : "未选中工作区" }}</h2>
              <p class="detail-card__summary">
                {{ selectedWorkspace ? "选中后会同步打开右侧详情面板并保留真实健康检查结果。" : "在左侧选择一个工作区，查看根路径、状态和真实健康记录。" }}
              </p>
            </div>
            <div v-if="selectedWorkspace" class="detail-card__actions">
              <button class="device-workspace-page__button" type="button" @click="handleHealthCheck" :disabled="deviceWorkspacesStore.loading">
                <span class="material-symbols-outlined">health_and_safety</span>
                健康检查
              </button>
              <button class="device-workspace-page__button device-workspace-page__button--ghost" type="button" @click="handleDelete">
                删除
              </button>
            </div>
          </div>

          <template v-if="selectedWorkspace">
            <div class="status-row">
              <div>
                <span class="status-row__label">状态</span>
                <strong>{{ statusLabel(selectedWorkspace.status) }}</strong>
              </div>
              <span class="status-row__chip" :data-status="selectedWorkspace.status">{{ selectedWorkspace.status }}</span>
            </div>

            <dl class="detail-metadata">
              <div>
                <dt>根路径</dt>
                <dd>{{ selectedWorkspace.root_path }}</dd>
              </div>
              <div>
                <dt>错误次数</dt>
                <dd>{{ selectedWorkspace.error_count }}</dd>
              </div>
              <div>
                <dt>创建时间</dt>
                <dd>{{ formatDateTime(selectedWorkspace.created_at) }}</dd>
              </div>
              <div>
                <dt>更新时间</dt>
                <dd>{{ formatDateTime(selectedWorkspace.updated_at) }}</dd>
              </div>
              <div>
                <dt>最近使用</dt>
                <dd>{{ selectedWorkspace.last_used_at ? formatDateTime(selectedWorkspace.last_used_at) : "从未" }}</dd>
              </div>
              <div>
                <dt>工作区 ID</dt>
                <dd>{{ selectedWorkspace.id }}</dd>
              </div>
            </dl>

            <section class="detail-block">
              <div class="detail-block__header">
                <span>浏览器实例</span>
                <strong>empty</strong>
              </div>
              <p class="detail-empty">
                当前 Runtime 尚未返回浏览器实例列表。这里仅保留空态，不包装任何伪造实例或假在线状态。
              </p>
            </section>

            <section class="detail-block">
              <div class="detail-block__header">
                <span>执行边界</span>
                <strong>blocked</strong>
              </div>
              <p class="detail-empty">
                当前 Runtime 尚未返回账号到工作区的执行绑定关系。页面只展示真实工作区对象，不扩展高风险能力。
              </p>
            </section>

            <div class="detail-actions">
              <button class="device-workspace-page__button device-workspace-page__button--brand" type="button" @click="openSelectedWorkspaceDetail">
                打开右侧详情
              </button>
              <button class="device-workspace-page__button" type="button" @click="clearSelection">
                清空选择
              </button>
            </div>
          </template>

          <template v-else>
            <div class="detail-empty-state">
              <span class="material-symbols-outlined">lan</span>
              <strong>未选中工作区</strong>
              <p>在左侧选择一个真实工作区对象，右侧会展示状态、路径和健康记录。</p>
            </div>
          </template>
        </article>

        <article class="detail-card detail-card--soft">
          <div class="detail-block__header">
            <span>当前边界</span>
          </div>
          <p class="detail-note">
            工作区页不会包装账号自动化、远程浏览器控制或执行环境伪对象，只保留本地真实工作区与健康检查。
          </p>
        </article>
      </section>
    </main>

    <transition name="drawer">
      <div v-if="isCreating" class="drawer-overlay" @click="isCreating = false">
        <aside class="drawer-panel" @click.stop>
          <div class="drawer-panel__header">
            <div>
              <p class="drawer-panel__eyebrow">新建工作区</p>
              <h2>创建真实工作区对象</h2>
            </div>
            <button class="drawer-panel__close" type="button" @click="isCreating = false">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <form class="drawer-form" @submit.prevent="handleCreate">
            <label class="drawer-form__field">
              <span>工作区名称</span>
              <input v-model="form.name" type="text" placeholder="例：PC-01-工作室" />
            </label>

            <label class="drawer-form__field">
              <span>根路径</span>
              <input v-model="form.root_path" type="text" placeholder="C:\\Users\\Admin\\TK-Workspace" />
            </label>

            <p class="drawer-form__hint">
              这里只写入真实本地目录，不会自动生成浏览器实例、执行绑定或高风险能力。
            </p>

            <div class="drawer-form__actions">
              <button class="device-workspace-page__button" type="button" @click="isCreating = false">取消</button>
              <button class="device-workspace-page__button device-workspace-page__button--brand" type="submit" :disabled="!form.name || !form.root_path || deviceWorkspacesStore.loading">
                保存工作区
              </button>
            </div>
          </form>
        </aside>
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import { useDeviceWorkspacesStore } from "@/stores/device-workspaces";
import type { DeviceWorkspaceDto } from "@/types/runtime";

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
    return (
      workspace.name.toLowerCase().includes(query) ||
      workspace.root_path.toLowerCase().includes(query)
    );
  });
});

const selectedWorkspace = computed(
  () => deviceWorkspacesStore.workspaces.find((workspace) => workspace.id === selectedWorkspaceId.value) ?? null
);

watch(
  selectedWorkspace,
  (workspace) => {
    if (!workspace) {
      shellUiStore.clearDetailContext("binding");
      shellUiStore.closeDetailPanel();
      return;
    }

    shellUiStore.openDetailWithContext(buildWorkspaceDetailContext(workspace));
  },
  { immediate: true }
);

onMounted(() => {
  void deviceWorkspacesStore.loadWorkspaces();
});

onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("binding");
  shellUiStore.closeDetailPanel();
});

function handleReload() {
  void deviceWorkspacesStore.loadWorkspaces();
}

function selectWorkspace(workspace: DeviceWorkspaceDto) {
  selectedWorkspaceId.value = workspace.id;
}

function clearSelection() {
  selectedWorkspaceId.value = null;
  shellUiStore.clearDetailContext("binding");
  shellUiStore.closeDetailPanel();
}

function openSelectedWorkspaceDetail() {
  if (!selectedWorkspace.value) return;
  shellUiStore.openDetailWithContext(buildWorkspaceDetailContext(selectedWorkspace.value));
}

async function handleCreate(): Promise<void> {
  if (!form.name || !form.root_path) return;
  const workspace = await deviceWorkspacesStore.addWorkspace({
    name: form.name.trim(),
    root_path: form.root_path.trim()
  });
  if (!workspace) return;
  selectedWorkspaceId.value = workspace.id;
  form.name = "";
  form.root_path = "";
  isCreating.value = false;
}

async function handleHealthCheck(): Promise<void> {
  if (!selectedWorkspace.value) return;
  await deviceWorkspacesStore.checkHealth(selectedWorkspace.value.id);
}

async function handleDelete(): Promise<void> {
  if (!selectedWorkspace.value) return;
  if (!window.confirm(`确认删除工作区“${selectedWorkspace.value.name}”吗？`)) return;
  const deletedId = selectedWorkspace.value.id;
  await deviceWorkspacesStore.removeWorkspace(deletedId);
  if (selectedWorkspaceId.value === deletedId) {
    clearSelection();
  }
}

function buildWorkspaceDetailContext(workspace: DeviceWorkspaceDto) {
  return createRouteDetailContext("binding", {
    icon: "lan",
    eyebrow: "工作区详情",
    title: workspace.name,
    description: "只展示 Runtime 返回的真实工作区对象、状态和健康检查记录。",
    badge: {
      label: statusLabel(workspace.status),
      tone: workspace.status === "online" || workspace.status === "running" ? "success" : workspace.status === "error" ? "danger" : "neutral"
    },
    metrics: [
      { id: "errors", label: "错误次数", value: String(workspace.error_count), hint: "真实字段" },
      { id: "status", label: "状态", value: statusLabel(workspace.status), hint: "来自 Runtime" },
      { id: "last-used", label: "最近使用", value: workspace.last_used_at ? formatDateTime(workspace.last_used_at) : "从未", hint: "真实时间" }
    ],
    sections: [
      {
        id: "workspace",
        title: "工作区信息",
        fields: [
          { id: "name", label: "名称", value: workspace.name },
          { id: "root", label: "根路径", value: workspace.root_path, mono: true, multiline: true },
          { id: "status", label: "状态", value: statusLabel(workspace.status) },
          { id: "errors", label: "错误次数", value: String(workspace.error_count) },
          { id: "created", label: "创建时间", value: formatDateTime(workspace.created_at), mono: true },
          { id: "updated", label: "更新时间", value: formatDateTime(workspace.updated_at), mono: true }
        ]
      },
      {
        id: "browser-instances",
        title: "浏览器实例",
        emptyLabel: "Runtime 暂时没有返回浏览器实例列表，保持空态，不伪造实例。"
      },
      {
        id: "binding",
        title: "执行绑定",
        emptyLabel: "Runtime 暂时没有返回执行绑定关系，页面只保留真实工作区对象。"
      }
    ],
    actions: [
      { id: "health-check", label: "健康检查", icon: "health_and_safety", tone: "brand" },
      { id: "clear", label: "清空选择", icon: "close", tone: "neutral" }
    ]
  });
}

function statusLabel(status: string): string {
  switch (status) {
    case "online":
      return "在线";
    case "offline":
      return "离线";
    case "running":
      return "运行中";
    case "error":
      return "异常";
    default:
      return status || "未知";
  }
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    hourCycle: "h23"
  }).formatToParts(date);

  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")} ${part("hour")}:${part("minute")}:${part("second")}`;
}
</script>

<style scoped>
.device-workspace-page {
  display: grid;
  gap: 16px;
  min-height: 100%;
  padding: 18px 24px 24px;
}

.device-workspace-page__hero {
  align-items: start;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.device-workspace-page__hero-copy {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.device-workspace-page__eyebrow {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0;
  text-transform: uppercase;
}

.device-workspace-page__hero-copy h1 {
  font-size: 28px;
  line-height: 1.15;
  margin: 0;
}

.device-workspace-page__hero-copy p {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
  line-height: 1.7;
  margin: 0;
  max-width: 800px;
}

.device-workspace-page__hero-actions,
.detail-actions,
.drawer-form__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.device-workspace-page__button {
  align-items: center;
  background: transparent;
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  color: var(--color-text-primary, var(--text-primary));
  cursor: pointer;
  display: inline-flex;
  gap: 6px;
  height: 36px;
  justify-content: center;
  padding: 0 14px;
}

.device-workspace-page__button--brand {
  background: var(--color-brand-primary, var(--brand-primary));
  border-color: var(--color-brand-primary, var(--brand-primary));
  color: var(--color-text-on-brand, #fff);
}

.device-workspace-page__button--ghost {
  background: transparent;
}

.device-workspace-page__button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.device-workspace-page__banner {
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-md);
  background: var(--color-bg-surface, var(--surface-secondary));
  color: var(--color-text-secondary, var(--text-secondary));
  margin: 0;
  padding: 10px 12px;
}

.device-workspace-page__banner--error {
  border-color: color-mix(in srgb, var(--color-danger, var(--status-error)) 32%, var(--color-border-default, var(--border-default)));
  color: var(--color-danger, var(--status-error));
}

.device-workspace-page__banner--blocked {
  border-color: color-mix(in srgb, var(--color-warning, var(--status-warning)) 30%, var(--color-border-default, var(--border-default)));
  color: var(--color-warning, var(--status-warning));
}

.device-workspace-page__summary {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.summary-card {
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-md);
  background: var(--color-bg-surface, var(--surface-secondary));
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 14px;
}

.summary-card span {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.summary-card strong {
  font-size: 15px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-card p {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
  line-height: 1.5;
  margin: 0;
}

.device-workspace-page__body {
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
  min-height: 0;
}

.device-workspace-page__rail,
.device-workspace-page__detail {
  display: grid;
  gap: 12px;
  min-height: 0;
}

.rail-card,
.detail-card {
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-md);
  background: var(--color-bg-surface, var(--surface-secondary));
  display: grid;
  gap: 14px;
  padding: 16px;
}

.detail-card--soft {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 4%, var(--color-bg-surface, var(--surface-secondary)));
}

.rail-card--list {
  gap: 12px;
  min-height: 0;
}

.rail-card__header,
.detail-card__header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.rail-card__eyebrow,
.detail-card__eyebrow {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0 0 4px;
  text-transform: uppercase;
}

.rail-card__header h2,
.detail-card__header h2 {
  margin: 0;
}

.search-box {
  align-items: center;
  background: var(--color-bg-canvas, var(--bg-card));
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  display: flex;
  gap: 8px;
  height: 38px;
  padding: 0 10px;
}

.search-box .material-symbols-outlined {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 18px;
}

.search-box input {
  background: transparent;
  border: none;
  color: var(--color-text-primary, var(--text-primary));
  font-size: 13px;
  min-width: 0;
  outline: none;
  width: 100%;
}

.rail-card__hint,
.detail-note,
.detail-empty {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
  line-height: 1.7;
  margin: 0;
}

.workspace-list {
  display: grid;
  gap: 10px;
  max-height: min(68vh, 760px);
  overflow: auto;
  padding-right: 2px;
}

.workspace-card {
  background: transparent;
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-md);
  color: inherit;
  cursor: pointer;
  display: grid;
  gap: 10px;
  grid-template-columns: auto minmax(0, 1fr) auto;
  padding: 12px;
  text-align: left;
}

.workspace-card--selected {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 8%, var(--color-bg-surface, var(--surface-secondary)));
  border-color: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 55%, var(--color-border-default, var(--border-default)));
}

.workspace-card__dot {
  align-self: start;
  border-radius: 50%;
  height: 10px;
  margin-top: 5px;
  width: 10px;
}

.workspace-card__dot.online {
  background: var(--color-success, #22c55e);
}

.workspace-card__dot.offline {
  background: var(--color-text-tertiary, var(--text-tertiary));
}

.workspace-card__dot.running {
  background: var(--color-info, #3b82f6);
}

.workspace-card__dot.error {
  background: var(--color-danger, var(--status-error));
}

.workspace-card__content {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.workspace-card__content strong {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-card__content span {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-card__badge {
  align-self: start;
  background: color-mix(in srgb, var(--color-danger, var(--status-error)) 12%, transparent);
  border-radius: 999px;
  color: var(--color-danger, var(--status-error));
  font-size: 12px;
  padding: 2px 8px;
}

.status-row {
  align-items: center;
  background: var(--color-bg-canvas, var(--surface-tertiary));
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
}

.status-row__label {
  color: var(--color-text-tertiary, var(--text-tertiary));
  display: block;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin-bottom: 3px;
  text-transform: uppercase;
}

.status-row strong {
  font-size: 15px;
}

.status-row__chip {
  align-self: start;
  border-radius: 999px;
  font-size: 12px;
  padding: 2px 8px;
  text-transform: capitalize;
}

.status-row__chip[data-status="online"],
.status-row__chip[data-status="running"] {
  background: color-mix(in srgb, var(--color-success, var(--status-success)) 12%, transparent);
  color: var(--color-success, var(--status-success));
}

.status-row__chip[data-status="offline"] {
  background: color-mix(in srgb, var(--color-text-tertiary, var(--text-tertiary)) 12%, transparent);
  color: var(--color-text-tertiary, var(--text-tertiary));
}

.status-row__chip[data-status="error"] {
  background: color-mix(in srgb, var(--color-danger, var(--status-error)) 12%, transparent);
  color: var(--color-danger, var(--status-error));
}

.detail-metadata {
  display: grid;
  gap: 12px;
  margin: 0;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.detail-metadata div {
  display: grid;
  gap: 4px;
}

.detail-metadata dt {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
}

.detail-metadata dd {
  font-size: 13px;
  margin: 0;
  overflow-wrap: anywhere;
}

.detail-block {
  border-top: 1px solid var(--color-border-default, var(--border-default));
  display: grid;
  gap: 10px;
  padding-top: 14px;
}

.detail-block__header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.detail-block__header span {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.detail-block__header strong {
  background: color-mix(in srgb, var(--color-danger, var(--status-error)) 12%, transparent);
  border-radius: 999px;
  color: var(--color-danger, var(--status-error));
  font-size: 12px;
  padding: 2px 8px;
}

.detail-empty-state {
  align-items: center;
  display: grid;
  gap: 10px;
  justify-items: center;
  min-height: 320px;
  padding: 24px 12px;
  text-align: center;
}

.detail-empty-state .material-symbols-outlined {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 42px;
}

.detail-empty-state strong {
  font-size: 15px;
}

.drawer-overlay {
  background: color-mix(in srgb, var(--color-bg-overlay, rgba(0, 0, 0, 0.55)) 100%, transparent);
  inset: 0;
  position: fixed;
  z-index: 1300;
}

.drawer-panel {
  background: var(--color-bg-surface, var(--surface-secondary));
  bottom: 0;
  box-shadow: -12px 0 32px rgba(0, 0, 0, 0.22);
  display: grid;
  gap: 16px;
  max-width: 420px;
  overflow: auto;
  padding: 18px;
  position: absolute;
  right: 0;
  top: 0;
  width: min(420px, 100vw);
}

.drawer-panel__header {
  align-items: start;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.drawer-panel__eyebrow {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0 0 4px;
  text-transform: uppercase;
}

.drawer-panel__header h2 {
  margin: 0;
}

.drawer-panel__close {
  align-items: center;
  background: transparent;
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary, var(--text-secondary));
  cursor: pointer;
  display: inline-flex;
  height: 32px;
  justify-content: center;
  width: 32px;
}

.drawer-form {
  display: grid;
  gap: 14px;
}

.drawer-form__field {
  display: grid;
  gap: 6px;
}

.drawer-form__field span {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
}

.drawer-form__field input {
  background: var(--color-bg-canvas, var(--surface-tertiary));
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  color: var(--color-text-primary, var(--text-primary));
  font: inherit;
  min-height: 38px;
  padding: 0 12px;
}

.drawer-form__hint {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
  line-height: 1.7;
  margin: 0;
}

.state-card {
  align-items: center;
  color: var(--color-text-secondary, var(--text-secondary));
  display: flex;
  flex-direction: column;
  gap: 10px;
  justify-content: center;
  min-height: 260px;
  padding: 24px 12px;
  text-align: center;
}

.state-card .material-symbols-outlined {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 44px;
}

.state-card strong {
  color: var(--color-text-primary, var(--text-primary));
  font-size: 15px;
}

.state-card p {
  line-height: 1.7;
  margin: 0;
}

.state-card__spinner {
  animation: spin 1.2s linear infinite;
}

.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 160ms ease;
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1280px) {
  .device-workspace-page__summary,
  .device-workspace-page__body {
    grid-template-columns: 1fr;
  }

  .device-workspace-page__hero {
    flex-direction: column;
  }

  .device-workspace-page__hero-actions {
    justify-content: flex-start;
  }

  .detail-metadata {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .device-workspace-page {
    padding-left: 16px;
    padding-right: 16px;
  }
}
</style>
