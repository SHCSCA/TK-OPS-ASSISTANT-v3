<template>
  <div class="page-container h-full">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 账号与设备</div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">设备与工作区管理</h1>
          <div class="page-header__subtitle">页面只管理 Runtime 返回的真实工作区对象、浏览器实例、健康检查和本地路径，不包装高风险能力。</div>
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
        <p class="sc-hint">来自 Runtime 的真实对象与绑定状态</p>
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
              工作区对象、浏览器实例与健康摘要均来自 Runtime，不补任何伪在线数据。
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
                :class="{
                  'is-selected': selectedWorkspaceId === workspace.id,
                  'workspace-card--selected': selectedWorkspaceId === workspace.id
                }"
                :data-testid="`workspace-card-${workspace.id}`"
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
                <Chip size="sm" variant="neutral">{{ deviceWorkspacesStore.browserInstances.length }} 个</Chip>
              </div>
              <div v-if="deviceWorkspacesStore.instancesLoading" class="detail-empty">正在读取浏览器实例...</div>
              <div v-else-if="deviceWorkspacesStore.browserInstances.length === 0" class="detail-empty">当前工作区还没有浏览器实例，页面不会伪造实例或假在线状态。</div>
              <div v-else class="instance-list">
                <div v-for="instance in deviceWorkspacesStore.browserInstances" :key="instance.id" class="instance-card">
                  <div class="ic-info">
                    <strong>{{ instance.name }}</strong>
                    <span>{{ instance.profilePath }}</span>
                  </div>
                  <Chip size="sm" :variant="statusTone(instance.status)">{{ instance.status }}</Chip>
                </div>
              </div>
              <Button variant="secondary" @click="isCreatingInstance = true">新建浏览器实例</Button>
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

    <!-- Drawer Modal for Workspace -->
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

    <!-- Drawer Modal for Instance -->
    <transition name="drawer">
      <div v-if="isCreatingInstance" class="drawer-overlay" @click="isCreatingInstance = false">
        <aside class="drawer-panel" @click.stop>
          <div class="drawer-panel__header">
            <div>
              <p class="drawer-panel__eyebrow">新建实例</p>
              <h2>创建浏览器实例</h2>
            </div>
            <button class="drawer-panel__close" @click="isCreatingInstance = false">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <div class="drawer-panel__body">
            <form class="drawer-form" @submit.prevent="handleCreateInstance">
              <div class="form-group">
                <label>实例名称</label>
                <input v-model="instanceForm.name" type="text" placeholder="例：Profile-01" class="ui-input-field" required />
              </div>
              <div class="form-group">
                <label>Profile 路径</label>
                <input v-model="instanceForm.profilePath" type="text" placeholder="Data/Profile-01" class="ui-input-field" required />
              </div>
              <div class="drawer-actions">
                <Button variant="ghost" @click="isCreatingInstance = false">取消</Button>
                <Button variant="primary" type="submit" :disabled="!selectedWorkspace || !instanceForm.name || !instanceForm.profilePath">保存实例</Button>
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
const isCreatingInstance = ref(false);
const form = reactive({ name: "", root_path: "" });
const instanceForm = reactive({ name: "", profilePath: "" });
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
    deviceWorkspacesStore.browserInstances = [];
    return;
  }
  shellUiStore.openDetailWithContext(buildWorkspaceDetailContext(workspace));
  void deviceWorkspacesStore.loadBrowserInstances(workspace.id);
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

async function handleCreateInstance() {
  if (!selectedWorkspace.value || !instanceForm.name || !instanceForm.profilePath) return;
  const instance = await deviceWorkspacesStore.addBrowserInstance(selectedWorkspace.value.id, {
    name: instanceForm.name.trim(),
    profilePath: instanceForm.profilePath.trim()
  });
  if (!instance) return;
  instanceForm.name = "";
  instanceForm.profilePath = "";
  isCreatingInstance.value = false;
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
      { id: "browser-instances", title: "浏览器实例", emptyLabel: "浏览器实例列表由 Runtime 嵌套路由返回，页面不伪造实例。" },
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

<style scoped src="./DeviceWorkspaceManagementPage.css"></style>
