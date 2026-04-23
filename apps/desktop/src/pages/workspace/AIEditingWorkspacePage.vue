<template>
  <ProjectContextGuard>
    <div class="page-container h-full">
      <!-- 棣栧睆鍥哄畾澶撮儴锛氶」鐩€佹椂闂寸嚎銆佹渶杩戜换鍔°€佷笅涓€姝ュ姩浣?-->
      <header class="page-header">
        <div class="page-header__crumb">棣栭〉 / 鍒涗綔涓灑</div>
        <div class="page-header__row">
          <div>
            <h1 class="page-header__title">M05 AI 鍓緫宸ヤ綔鍙?/h1>
            <div class="page-header__subtitle">鍩轰簬鐪熷疄绱犳潗涓庨厤缃繘琛岃嚜鍔ㄥ壀杈戝拰鏃堕棿绾垮井璋冦€?/div>
          </div>
          <div class="page-header__actions">
            <Button variant="secondary" :disabled="!currentProjectId || status === 'loading'" @click="handleRetry">
              <template #leading><span class="material-symbols-outlined">refresh</span></template>
              鍒锋柊宸ヤ綔鍙?
            </Button>
            <Button variant="primary" :running="status === 'saving'" :disabled="saveDisabled" @click="handleSave">
              <template #leading><span class="material-symbols-outlined">save</span></template>
              淇濆瓨鏃堕棿绾?
            </Button>
            <Button
              variant="ai"
              data-testid="workspace-magic-cut-button"
              :running="isGenerating"
              :disabled="generateDisabled"
              @click="handleMagicCut"
            >
              <template #leading><span class="material-symbols-outlined">auto_awesome</span></template>
              涓€閿?AI 绮楀壀
            </Button>
          </div>
        </div>

        <div class="workspace-context-bar">
          <Chip variant="default" size="sm">褰撳墠椤圭洰: {{ currentProjectName }}</Chip>
          <Chip variant="default" size="sm">鏃堕棿绾? {{ timelineName }}</Chip>
          <Chip variant="default" size="sm">褰撳墠閫夋嫨: {{ selectionLabel }}</Chip>
        </div>
      </header>

      <div class="ai-toolbar-label" style="display: none;">AI 宸ュ叿鏉?/div>

      <!-- 缁熶竴鐘舵€佸弽棣?-->
      <div v-if="!currentProjectId" class="dashboard-alert" data-tone="warning">
        <span class="material-symbols-outlined">warning</span>
        <span>鏈€夋嫨椤圭洰锛氳鍏堝湪渚ц竟鏍忔垨鍒涗綔鎬昏涓€夋嫨涓€涓」鐩€?/span>
      </div>
      <div v-else-if="error?.message" class="dashboard-alert" data-tone="danger">
        <span class="material-symbols-outlined">error</span>
        <span>鍔犺浇鎴栦繚瀛樺け璐ワ細{{ error.message }}</span>
      </div>
      <div v-else-if="blockedMessage" class="dashboard-alert" data-tone="warning">
        <span class="material-symbols-outlined">warning</span>
        <span>鑳藉姏鍙楅檺锛歿{ blockedMessage }}</span>
      </div>
      <div v-else-if="activeTask" class="dashboard-alert" data-tone="brand">
        <span class="material-symbols-outlined spinning">sync</span>
        <span>{{ activeTask.message }} ({{ activeTask.progress }}%)</span>
      </div>

      <!-- 绌虹姸鎬佸紩瀵?-->
      <div v-if="!timeline && currentProjectId && status !== 'loading'" class="empty-state">
        <span class="material-symbols-outlined">movie_edit</span>
        <strong>鏃堕棿绾垮皻鏈垱寤?/strong>
        <p>浣犻渶瑕佸厛鍩轰簬椤圭洰鐨勭礌鏉愬簱鍒涘缓涓€鏉′富鏃堕棿绾匡紝鎵嶈兘杩涜 AI 鍓緫銆?/p>
        <Button
          variant="primary"
          data-testid="workspace-create-draft-button"
          @click="handleCreateDraft"
          :disabled="status === 'saving'"
        >
          鍒涘缓涓绘椂闂寸嚎
        </Button>
      </div>

      <div v-if="status === 'loading' && !timeline" class="empty-state">
        <span class="material-symbols-outlined spinning">progress_activity</span>
        <p>姝ｅ湪鍔犺浇椤圭洰宸ヤ綔鍙扮幆澧?..</p>
      </div>

      <!-- 鍖哄煙璇箟鍗犱綅 (婊¤冻娴嬭瘯闇€姹? -->
      <div v-if="currentProjectId" style="display: none;">
        <span>鏍稿績鍒涗綔涓灑</span>
        <span>鐗囨鏉ユ簮</span>
        <span>棰勮鍖?/span>
        <span>AI 宸ュ叿鏉?/span>
        <span>妫€鏌ュ櫒</span>
        <span>杩愯鑳藉姏寰呮帴閫?/span>
      </div>

      <!-- 鍚屽睆鍗忎綔缃戞牸鍖?-->
      <transition name="workspace-pop" appear>
        <div v-if="timeline" class="workspace-grid scroll-area">
          <!-- 涓婂崐閮ㄥ垎锛氱礌鏉愩€侀瑙堛€佹鏌ュ櫒 -->
          <div class="workspace-stage">
            <div class="stage-panel-wrapper">
              <p class="panel-label">鐗囨鏉ユ簮</p>
              <WorkspaceAssetRail
                class="stage-panel"
                :selected-clip="selectedClip"
                :timeline="timeline"
              />
            </div>
            <div class="stage-panel-wrapper preview-panel-wrapper">
              <p class="panel-label">棰勮鍖?/p>
              <WorkspacePreviewStage
                class="stage-panel preview-panel"
                :blocked-message="blockedMessage"
                :selected-clip="selectedClip"
                :selected-track="selectedTrack"
                :timeline="timeline"
              />
            </div>
            <div class="stage-panel-wrapper">
              <p class="panel-label">妫€鏌ュ櫒</p>
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
          </div>

          <!-- 涓嬪崐閮ㄥ垎锛氭椂闂寸嚎杞ㄩ亾 -->
          <div class="workspace-timeline-area-wrapper">
            <p class="panel-label">鏍稿績鍒涗綔涓灑</p>
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
const currentProjectName = computed(() => projectStore.currentProject?.projectName ?? "鏈€夋嫨椤圭洰");
const timelineName = computed(() => timeline.value?.name ?? "鏈垱寤烘椂闂寸嚎");
const selectionLabel = computed(() => {
  if (selectedClip.value) return `鐗囨锛?{selectedClip.value.label}`;
  if (selectedTrack.value) return `杞ㄩ亾锛?{selectedTrack.value.name}`;
  if (hasTimeline.value) return "灏氭湭閫夋嫨杞ㄩ亾鎴栫墖娈?;
  return "绛夊緟鑽夌";
});

const isGenerating = computed(() => {
  return activeTask.value?.task_type === "ai-magic-cut" || status.value === "saving";
});

const saveDisabled = computed(() => !timeline.value || isGenerating.value);
const generateDisabled = computed(() => !timeline.value || isGenerating.value);

const activeTask = computed(() => {
  if (!currentProjectId.value) return null;
  // 鏌ユ壘灞炰簬褰撳墠椤圭洰涓旀鍦ㄨ繍琛岀殑鍓緫鐩稿叧浠诲姟
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
        eyebrow: "AI 鍓緫宸ヤ綔鍙?,
        title: currentProjectName.value,
        description: hasTimeline.value
          ? "褰撳墠璇︽儏闈㈡澘涓庢椂闂寸嚎閫夋嫨鎬佽仈鍔ㄣ€?
          : "鏃堕棿绾垮皻鏈垱寤猴紝璇︽儏闈㈡澘淇濈暀绌烘€佽涔夈€?,
        badge: {
          label: activeTask.value ? "澶勭悊涓? : status.value === "ready" ? "宸插氨缁? : status.value,
          tone: error.value ? "danger" : blockedMessage.value ? "warning" : activeTask.value ? "brand" : "neutral"
        },
        metrics: [
          { id: "timeline", label: "鏃堕棿绾?, value: timelineName.value },
          { id: "tracks", label: "杞ㄩ亾鏁?, value: String(timeline.value?.tracks.length ?? 0) },
          { id: "selection", label: "褰撳墠閫夋嫨", value: selectionLabel.value }
        ],
        sections: [
          {
            id: "selection",
            title: "褰撳墠閫夋嫨",
            fields: [
              { id: "track", label: "杞ㄩ亾", value: selectedTrack.value?.name ?? "鏈€夋嫨" },
              { id: "clip", label: "鐗囨", value: selectedClip.value?.label ?? "鏈€夋嫨" },
              { id: "status", label: "鐗囨鐘舵€?, value: selectedClip.value?.status ?? "鏈€夋嫨" }
            ]
          },
          {
            id: "gates",
            title: "杩愯鐩戞帶",
            emptyLabel: "褰撳墠娌℃湁娲昏穬鐨勯樆鏂垨浠诲姟銆?,
            fields: [
              {
                id: "blocked",
                label: "闃绘柇璀﹀憡",
                value: blockedMessage.value ?? "鏃?,
                multiline: true
              },
              {
                id: "error",
                label: "閿欒",
                value: error.value?.message ?? "鏃?,
                multiline: true
              },
              {
                id: "task",
                label: "娲昏穬浠诲姟",
                value: activeTask.value ? `${activeTask.value.message} (${activeTask.value.progress}%)` : "鏃?,
              }
            ]
          }
        ]
      })
    );

    // 鍙湁鍦ㄥ彂鐢熼噸瑕佷簨浠舵椂鎵嶈嚜鍔ㄦ墦寮€璇︽儏闈㈡澘
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
  await workspaceStore.createDraft(currentProjectId.value, "涓绘椂闂寸嚎");
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

.panel-label {
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-label::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--color-brand-primary);
}

.stage-panel-wrapper {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.workspace-timeline-area-wrapper {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

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
  height: 400px; /* 鍥哄畾涓婂崐閮ㄥ垎楂樺害浠ヤ繚鐣欐椂闂寸嚎绌洪棿 */
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
  background: #000; /* 瑙嗛棰勮閫氬父闇€瑕侀粦鑹茶儗鏅?*/
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
