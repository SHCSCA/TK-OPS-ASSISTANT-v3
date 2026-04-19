<template>
  <ProjectContextGuard>
    <div class="page-container">
      <header class="page-header">
        <div class="page-header__crumb">首页 / 视频拆解</div>
        <div class="page-header__row">
          <div>
            <h1 class="page-header__title">视频拆解中心</h1>
            <div class="page-header__subtitle">导入现有视频，建立可拆解的素材基线，获取基础元信息。</div>
          </div>
          <div class="page-header__actions">
            <Button
              variant="primary"
              :running="videoImportStore.status === 'importing'"
              :disabled="!currentProjectId || videoImportStore.status === 'importing'"
              @click="handleImportVideo"
            >
              <template #leading><span class="material-symbols-outlined">add</span></template>
              {{ videoImportStore.status === "importing" ? "导入中..." : "导入本地视频" }}
            </Button>
          </div>
        </div>
      </header>

      <div v-if="videoImportStore.error" class="dashboard-alert" data-tone="danger">
        {{ videoErrorSummary }}
      </div>

      <div class="video-workspace">
        <div class="video-main">
          <div class="section-header">
            <h3>项目素材列表</h3>
            <Chip size="sm">{{ videoImportStore.videos.length }} 个视频</Chip>
          </div>

          <div v-if="videoImportStore.status === 'loading'" class="empty-state">
            <span class="material-symbols-outlined spinning">progress_activity</span>
            <p>正在加载项目视频列表...</p>
          </div>
          <div v-else-if="videoImportStore.videos.length === 0" class="empty-state">
            <span class="material-symbols-outlined">video_file</span>
            <strong>还没有导入视频</strong>
            <p>点击右上角“导入本地视频”，先把现有素材纳入当前项目。</p>
          </div>
          <div v-else class="video-grid">
            <transition-group name="video-list">
              <Card
                v-for="video in videoImportStore.videos"
                :key="video.id"
                class="video-card"
                :interactive="true"
              >
                <!-- Real Preview Component -->
                <AssetPreview :asset="mapToAsset(video)" variant="card" />

                <div class="video-card__body">
                  <div class="video-card__header">
                    <div class="video-card__title">
                       <Chip size="sm" variant="default">{{ video.codec ?? "codec 待识别" }}</Chip>
                       <h4 :title="video.fileName">{{ video.fileName }}</h4>
                    </div>
                    <Chip :variant="video.status === 'ready' ? 'success' : 'info'" size="sm">
                       {{ video.status === "ready" ? "元信息就绪" : "已导入" }}
                    </Chip>
                  </div>
                  
                  <div class="video-card__metrics">
                    <span class="metric-item"><span class="material-symbols-outlined">schedule</span>{{ formatDuration(video.durationSeconds) }}</span>
                    <span class="metric-item"><span class="material-symbols-outlined">aspect_ratio</span>{{ formatResolution(video.width, video.height) }}</span>
                    <span class="metric-item"><span class="material-symbols-outlined">speed</span>{{ formatFrameRate(video.frameRate) }}</span>
                    <span class="metric-item"><span class="material-symbols-outlined">hard_drive</span>{{ formatFileSize(video.fileSizeBytes) }}</span>
                  </div>

                  <div v-if="taskForVideo(video.id)" class="video-card__task">
                    <div class="task-info">
                      <span>{{ taskForVideo(video.id)?.message || taskStatusLabel(video.id) }}</span>
                      <strong>{{ taskForVideo(video.id)?.progress ?? 0 }}%</strong>
                    </div>
                    <div class="task-progress-bg">
                      <div class="task-progress-fill" :style="taskProgressStyle(video.id)"></div>
                    </div>
                  </div>

                  <div v-if="video.errorMessage" class="video-card__error">
                    <span class="material-symbols-outlined">error</span>
                    <span>{{ video.errorMessage }}</span>
                  </div>
                </div>
                <div class="video-card__footer">
                   <Button variant="danger" size="sm" @click="videoImportStore.removeVideo(video.id)">删除记录</Button>
                </div>
              </Card>
            </transition-group>
          </div>
        </div>

        <aside class="video-rail">
           <Card class="rail-card">
              <div class="rail-card__header">
                <h3>本轮边界</h3>
              </div>
              <div class="rail-card__body">
                 <p>只做导入与元信息提取。FFprobe 可用时展示时长、分辨率、帧率和编码；不可用时仍保存路径与文件大小，不阻断导入。</p>
                 <div class="rail-metric">
                    <span>当前项目</span>
                    <strong>{{ projectStore.currentProject?.projectName ?? "未选择" }}</strong>
                 </div>
                 <div class="rail-metric">
                    <span>后续回流</span>
                    <strong>转写 / 切段 / 重制</strong>
                 </div>
              </div>
           </Card>
        </aside>
      </div>
    </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";

import AssetPreview from "@/components/assets/AssetPreview.vue";
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { useProjectStore } from "@/stores/project";
import { useTaskBusStore } from "@/stores/task-bus";
import { useVideoImportStore } from "@/stores/video-import";
import type { TaskInfo } from "@/types/task-events";
import type { AssetDto, ImportedVideo } from "@/types/runtime";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const projectStore = useProjectStore();
const taskBusStore = useTaskBusStore();
const videoImportStore = useVideoImportStore();
const taskBusSnapshot = computed(() => ({
  tasks: new Map(taskBusStore.tasks),
  lastEvents: new Map(taskBusStore.lastEvents)
}));

const currentProjectId = computed(() => projectStore.currentProject?.projectId ?? "");
const videoErrorSummary = computed(() => {
  if (!videoImportStore.error) return "";
  return videoImportStore.error.requestId
    ? `${videoImportStore.error.message}（${videoImportStore.error.requestId}）`
    : videoImportStore.error.message;
});

onMounted(() => {
  videoImportStore.initializeWebSocket();
  if (currentProjectId.value) {
    void videoImportStore.loadVideos(currentProjectId.value);
  }
});

watch(currentProjectId, (projectId) => {
  if (projectId) {
    void videoImportStore.loadVideos(projectId);
  }
});

async function handleImportVideo(): Promise<void> {
  if (!currentProjectId.value) return;

  const filePath = await pickVideoFilePath();
  if (!filePath) return;

  await videoImportStore.importVideoFile(currentProjectId.value, filePath);
}

async function pickVideoFilePath(): Promise<string> {
  try {
    const dialogModuleName = "@tauri-apps/plugin-dialog";
    const dialog = await import(/* @vite-ignore */ dialogModuleName);
    const selected = await dialog.open({
      multiple: false,
      filters: [{ name: "Video", extensions: ["mp4", "mov", "mkv", "webm"] }]
    });
    return typeof selected === "string" ? selected : "";
  } catch {
    return window.prompt("请输入本地视频文件路径")?.trim() ?? "";
  }
}

function formatDuration(value: number | null): string {
  return value === null ? "时长待识别" : `${value} 秒`;
}

function formatResolution(width: number | null, height: number | null): string {
  return width && height ? `${width} × ${height}` : "待识别";
}

function taskForVideo(videoId: string): TaskInfo | undefined {
  const directTask = taskBusSnapshot.value.tasks.get(videoId);
  if (directTask) return directTask;
  return videoImportStore.taskForVideo(videoId);
}

function taskStatusLabel(videoId: string): string {
  const task = taskForVideo(videoId);
  if (!task) return "";
  if (task.status === "failed") return "解析失败";
  if (task.status === "succeeded") return "解析完成";
  if (task.status === "cancelled") return "已取消";
  return "解析中";
}

function taskProgressStyle(videoId: string): Record<string, string> {
  const progress = Math.min(100, Math.max(0, taskForVideo(videoId)?.progress ?? 0));
  return { width: `${progress}%` };
}

function formatFrameRate(value: number | null): string {
  return value === null ? "待识别" : `${value} fps`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** Helper to map ImportedVideo to AssetDto for preview component */
function mapToAsset(v: ImportedVideo): AssetDto {
  return {
    id: v.id,
    name: v.fileName,
    type: "video",
    source: "local",
    filePath: v.filePath,
    fileSizeBytes: v.fileSizeBytes,
    durationMs: v.durationSeconds ? v.durationSeconds * 1000 : null,
    thumbnailPath: null,
    tags: null,
    projectId: v.projectId,
    metadataJson: null,
    createdAt: v.createdAt,
    updatedAt: v.createdAt
  };
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
  margin-bottom: var(--space-6);
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
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-muted);
  line-height: 1.6;
  margin-bottom: var(--space-6);
}

.dashboard-alert[data-tone="danger"] {
  border-color: rgba(255, 90, 99, 0.20);
  background: rgba(255, 90, 99, 0.08);
  color: var(--color-danger);
}

.video-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--space-6);
  align-items: start;
}

.video-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.section-header h3 {
  margin: 0;
  font: var(--font-title-lg);
  color: var(--color-text-primary);
}

.empty-state {
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

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin { 100% { transform: rotate(360deg); } }

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
}

.video-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.video-card:active {
  transform: scale(0.98);
}

/* List Transitions */
.video-list-move,
.video-list-enter-active,
.video-list-leave-active {
  transition: all var(--motion-default) var(--ease-spring);
}
.video-list-enter-from,
.video-list-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
.video-list-leave-active {
  position: absolute;
}

.video-card :deep(.asset-preview) {
  height: 160px;
  border-bottom: 1px solid var(--color-border-subtle);
  border-radius: 0;
}

.video-card__body {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.video-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2);
}

.video-card__title {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  min-width: 0;
}

.video-card__title h4 {
  margin: 0;
  font: var(--font-title-sm);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 100%;
}

.video-card__metrics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.metric-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.metric-item .material-symbols-outlined {
  font-size: 14px;
  color: var(--color-text-tertiary);
}

.video-card__task {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.task-info {
  display: flex;
  justify-content: space-between;
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.task-info strong {
  color: var(--color-brand-primary);
}

.task-progress-bg {
  height: 4px;
  background: var(--color-border-default);
  border-radius: 999px;
  overflow: hidden;
}

.task-progress-fill {
  height: 100%;
  background: var(--color-brand-primary);
  transition: width var(--motion-fast) var(--ease-standard);
}

.video-card__error {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: var(--space-2);
  background: rgba(255, 90, 99, 0.1);
  border-radius: var(--radius-sm);
  color: var(--color-danger);
  font: var(--font-caption);
}

.video-card__error .material-symbols-outlined {
  font-size: 14px;
  margin-top: 1px;
}

.video-card__footer {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
  display: flex;
  justify-content: flex-end;
}

.rail-card {
  display: flex;
  flex-direction: column;
}

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

.rail-card__body {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.rail-card__body p {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.rail-metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-3);
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
}

.rail-metric span {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.rail-metric strong {
  font: var(--font-title-sm);
  color: var(--color-text-primary);
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

@media (max-width: 1024px) {
  .video-workspace {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header__row {
    flex-direction: column;
  }
}
</style>
