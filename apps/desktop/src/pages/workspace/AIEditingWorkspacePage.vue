<template>
  <ProjectContextGuard>
    <div class="page-container h-full">
      <!-- 首屏固定头部：项目、时间线、最近任务、下一步动作 -->
      <header class="page-header">
        <div class="page-header__crumb">首页 / 创作中枢</div>
        <div class="page-header__row">
          <div>
            <h1 class="page-header__title">AI 剪辑工作台</h1>
            <div class="page-header__subtitle">基于真实素材与配置进行自动剪辑和时间线微调。</div>
          </div>
          <div class="page-header__actions">
            <Button variant="secondary" :disabled="!currentProjectId || status === 'loading'" @click="handleRetry">
              <template #leading><span class="material-symbols-outlined">refresh</span></template>
              刷新工作台
            </Button>
            <Button variant="primary" :running="status === 'saving'" :disabled="saveDisabled" @click="handleSave">
              <template #leading><span class="material-symbols-outlined">save</span></template>
              保存时间线
            </Button>
            <Button variant="ai" :running="isGenerating" :disabled="generateDisabled" @click="handleMagicCut">
              <template #leading><span class="material-symbols-outlined">auto_awesome</span></template>
              一键 AI 粗剪
            </Button>
          </div>
        </div>

        <div class="workspace-context-bar">
          <Chip variant="default" size="sm">当前项目: {{ currentProjectName }}</Chip>
          <Chip variant="default" size="sm">时间线: {{ timelineName }}</Chip>
          <Chip variant="default" size="sm">当前选择: {{ selectionLabel }}</Chip>
        </div>
      </header>

      <!-- 统一状态反馈 -->
      <div v-if="!currentProjectId" class="dashboard-alert" data-tone="warning">
        <span class="material-symbols-outlined">warning</span>
        <span>未选择项目：请先在侧边栏或创作总览中选择一个项目。</span>
      </div>
      <div v-else-if="error?.message" class="dashboard-alert" data-tone="danger">
        <span class="material-symbols-outlined">error</span>
        <span>加载或保存失败：{{ error.message }}</span>
      </div>
      <div v-else-if="blockedMessage" class="dashboard-alert" data-tone="warning">
        <span class="material-symbols-outlined">warning</span>
        <span>能力受限：{{ blockedMessage }}</span>
      </div>
      <div v-else-if="activeTask" class="dashboard-alert" data-tone="brand">
        <span class="material-symbols-outlined spinning">sync</span>
        <span>{{ activeTask.message }} ({{ activeTask.progress }}%)</span>
      </div>

      <!-- 空状态引导 -->
      <div v-if="!timeline && currentProjectId && status !== 'loading'" class="empty-state">
        <span class="material-symbols-outlined">movie_edit</span>
        <strong>时间线尚未创建</strong>
        <p>你需要先基于项目的素材库创建一条主时间线，才能进行 AI 剪辑。</p>
        <Button variant="primary" @click="handleCreateDraft" :disabled="status === 'saving'">
          创建主时间线
        </Button>
      </div>

      <div v-if="status === 'loading' && !timeline" class="empty-state">
        <span class="material-symbols-outlined spinning">progress_activity</span>
        <p>正在加载项目工作台环境...</p>
      </div>

      <!-- 同屏协作网格区 -->
      <transition name="workspace-pop" appear>
        <div v-if="timeline" class="workspace-grid scroll-area">
          <!-- 上半部分：素材、预览、检查器 -->
          <div class="workspace-stage">
            <WorkspaceAssetRail 
              class="stage-panel" 
              :selected-clip="selectedClip" 
              :timeline="timeline" 
            />
            <WorkspacePreviewStage
              class="stage-panel preview-panel"
              :blocked-message="blockedMessage"
              :selected-clip="selectedClip"
              :selected-track="selectedTrack"
              :timeline="timeline"
            />
            <WorkspaceInspector
              class="stage-panel"
              :blocked-message="blockedMessage"
              :error-message="error?.message ?? null"
              :selected-clip="selectedClip"
              :selected-track="selectedTrack"
              :status="status"
              :timeline="timeline"
            />
          </div>

          <!-- 下半部分：时间线轨道 -->
          <div class="workspace-timeline-area">
            <WorkspaceTimeline
              :selected-clip-id="selectedClipId"
              :selected-track-id="selectedTrackId"
              :status="status"
              :timeline="timeline"
              :tracks="orderedTracks"
              @select-clip="handleSelectClip"
              @select-track="handleSelectTrack"
            />
          </div>
        </div>
      </transition>
    </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, onMounted, watch } from "vue";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import WorkspaceAssetRail from "@/modules/workspace/WorkspaceAssetRail.vue";
import WorkspaceInspector from "@/modules/workspace/WorkspaceInspector.vue";
import WorkspacePreviewStage from "@/modules/workspace/WorkspacePreviewStage.vue";
import WorkspaceTimeline from "@/modules/workspace/WorkspaceTimeline.vue";
import { useEditingWorkspaceStore } from "@/stores/editing-workspace";
import { useProjectStore } from "@/stores/project";
import { useTaskBusStore } from "@/stores/task-bus";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";

import Button from "@/components/ui/Button/Button.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const projectStore = useProjectStore();
const shellUiStore = useShellUiStore();
const workspaceStore = useEditingWorkspaceStore();
const taskBusStore = useTaskBusStore();

const {
  blockedMessage,
  error,
  hasTimeline,
  orderedTracks,
  selectedClip,
  selectedClipId,
  selectedTrack,
  selectedTrackId,
  status,
  timeline
} = storeToRefs(workspaceStore);

const currentProjectId = computed(() => projectStore.currentProject?.projectId ?? "");
const currentProjectName = computed(() => projectStore.currentProject?.projectName ?? "未选择项目");
const timelineName = computed(() => timeline.value?.name ?? "未创建时间线");
const selectionLabel = computed(() => {
  if (selectedClip.value) return `片段：${selectedClip.value.label}`;
  if (selectedTrack.value) return `轨道：${selectedTrack.value.name}`;
  if (hasTimeline.value) return "尚未选择轨道或片段";
  return "等待草稿";
});

const isGenerating = computed(() => {
  return activeTask.value?.task_type === "ai-magic-cut" || status.value === "saving";
});

const saveDisabled = computed(() => !timeline.value || isGenerating.value);
const generateDisabled = computed(() => !timeline.value || isGenerating.value);

const activeTask = computed(() => {
  if (!currentProjectId.value) return null;
  // 查找属于当前项目且正在运行的剪辑相关任务
  for (const [id, task] of taskBusStore.tasks.entries()) {
    if (task.projectId === currentProjectId.value && (task.status === "running" || task.status === "queued" || task.status === "pending")) {
      return task;
    }
  }
  return null;
});

onMounted(() => {
  taskBusStore.connect();
});

watch(
  currentProjectId,
  (projectId) => {
    if (projectId) {
      void workspaceStore.load(projectId);
    }
  },
  { immediate: true }
);

watch(
  [currentProjectName, timeline, selectedTrack, selectedClip, status, blockedMessage, error, activeTask],
  () => {
    shellUiStore.setDetailContext(
      createRouteDetailContext("asset", {
        icon: "movie_edit",
        eyebrow: "AI 剪辑工作台",
        title: currentProjectName.value,
        description: hasTimeline.value
          ? "当前详情面板与时间线选择态联动。"
          : "时间线尚未创建，详情面板保留空态语义。",
        badge: {
          label: activeTask.value ? "处理中" : status.value === "ready" ? "已就绪" : status.value,
          tone: error.value ? "danger" : blockedMessage.value ? "warning" : activeTask.value ? "brand" : "neutral"
        },
        metrics: [
          { id: "timeline", label: "时间线", value: timelineName.value },
          { id: "tracks", label: "轨道数", value: String(timeline.value?.tracks.length ?? 0) },
          { id: "selection", label: "当前选择", value: selectionLabel.value }
        ],
        sections: [
          {
            id: "selection",
            title: "当前选择",
            fields: [
              { id: "track", label: "轨道", value: selectedTrack.value?.name ?? "未选择" },
              { id: "clip", label: "片段", value: selectedClip.value?.label ?? "未选择" },
              { id: "status", label: "片段状态", value: selectedClip.value?.status ?? "未选择" }
            ]
          },
          {
            id: "gates",
            title: "运行监控",
            emptyLabel: "当前没有活跃的阻断或任务。",
            fields: [
              {
                id: "blocked",
                label: "阻断警告",
                value: blockedMessage.value ?? "无",
                multiline: true
              },
              {
                id: "error",
                label: "错误",
                value: error.value?.message ?? "无",
                multiline: true
              },
              {
                id: "task",
                label: "活跃任务",
                value: activeTask.value ? `${activeTask.value.message} (${activeTask.value.progress}%)` : "无",
              }
            ]
          }
        ]
      })
    );

    // 只有在发生重要事件时才自动打开详情面板
    if (error.value || blockedMessage.value) {
      shellUiStore.openDetailPanel();
    }
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("asset");
});

async function handleCreateDraft(): Promise<void> {
  await workspaceStore.createDraft(currentProjectId.value, "主时间线");
}

async function handleSave(): Promise<void> {
  await workspaceStore.saveTimeline();
}

async function handleMagicCut(): Promise<void> {
  await workspaceStore.runMagicCut(currentProjectId.value);
}

async function handleRetry(): Promise<void> {
  if (currentProjectId.value) {
    await workspaceStore.load(currentProjectId.value);
  }
}

function handleSelectTrack(trackId: string): void {
  workspaceStore.selectTrack(trackId);
  shellUiStore.openDetailPanel();
}

function handleSelectClip(payload: { clipId: string; trackId: string }): void {
  workspaceStore.selectTrack(payload.trackId);
  workspaceStore.selectClip(payload.clipId);
  shellUiStore.openDetailPanel();
}
</script>

<style scoped>
.page-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-8) var(--space-8);
  display: flex;
  flex-direction: column;
  min-height: 100%;
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

.workspace-context-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: var(--space-2);
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

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-12) var(--space-6);
  border: 1px dashed var(--color-border-default);
  border-radius: var(--radius-lg);
  background: var(--color-bg-canvas);
  color: var(--color-text-secondary);
  text-align: center;
}

.empty-state .material-symbols-outlined {
  font-size: 32px;
  color: var(--color-text-tertiary);
}

.empty-state strong {
  font: var(--font-title-md);
  color: var(--color-text-primary);
}

.empty-state p {
  margin: 0;
  font: var(--font-body-md);
}

.spinning { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

.workspace-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
}

.workspace-stage {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: 280px minmax(480px, 1fr) 280px;
  height: 400px; /* 固定上半部分高度以保留时间线空间 */
  flex-shrink: 0;
}

.stage-panel {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.preview-panel {
  background: #000; /* 视频预览通常需要黑色背景 */
  border-color: #333;
}

.workspace-timeline-area {
  flex: 1;
  min-height: 240px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.scroll-area {
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-strong) transparent;
}

.scroll-area::-webkit-scrollbar {
  width: 4px;
}
.scroll-area::-webkit-scrollbar-thumb {
  background: var(--color-border-strong);
  border-radius: 99px;
}

.workspace-pop-enter-active {
  transition: opacity var(--motion-slow) var(--ease-standard), transform var(--motion-slow) var(--ease-spring);
}

.workspace-pop-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

@media (max-width: 1400px) {
  .workspace-stage {
    grid-template-columns: 240px minmax(400px, 1fr) 240px;
  }
}

@media (max-width: 1280px) {
  .workspace-stage {
    grid-template-columns: 260px minmax(0, 1fr);
    height: auto;
  }
  .workspace-stage > :last-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 960px) {
  .workspace-stage {
    grid-template-columns: 1fr;
  }
}
</style>