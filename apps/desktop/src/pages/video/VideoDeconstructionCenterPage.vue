<template>
  <ProjectContextGuard>
    <div class="page-container">
      <header class="page-header">
        <div class="page-header__crumb">首页 / 视频拆解</div>
        <div class="page-header__row">
          <div>
            <h1 class="page-header__title">视频拆解中心</h1>
            <div class="page-header__subtitle">导入素材并提取其结构，一键同步至文案中心与分镜规划。</div>
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

      <div v-if="isFfprobeUnavailable" class="ffprobe-alert">
        <div class="ffprobe-alert__content">
          <span class="material-symbols-outlined">warning</span>
          <div class="ffprobe-alert__text">
            <strong>未检测到 FFprobe 可执行文件</strong>
            <p>影响范围：时长 / 分辨率 / 码率字段暂无法解析。请确保系统已安装 FFprobe。</p>
          </div>
        </div>
        <div class="ffprobe-alert__actions">
          <Button variant="secondary" size="sm" @click="handleViewSetupGuide">查看修复指引</Button>
          <Button variant="primary" size="sm" @click="handleRescan">重新扫描</Button>
        </div>
      </div>

      <div class="video-workspace">
        <div class="video-main">
          <div class="section-header">
            <h3>项目拆解列表</h3>
            <Chip size="sm">{{ videoImportStore.videos.length }} 个素材</Chip>
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
                :active="selectedVideoId === video.id"
                @click="selectVideo(video.id)"
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
                       {{ video.status === "ready" ? "解析就绪" : "导入中" }}
                    </Chip>
                  </div>
                  
                  <div class="video-card__metrics">
                    <span class="metric-item"><span class="material-symbols-outlined">schedule</span>{{ formatDuration(video.durationSeconds) }}</span>
                    <span class="metric-item"><span class="material-symbols-outlined">hard_drive</span>{{ formatFileSize(video.fileSizeBytes) }}</span>
                  </div>

                  <!-- 拆解状态摘要 -->
                  <div v-if="videoImportStore.videoStages[video.id]" class="video-card__stages-summary">
                    <div class="stage-mini-list">
                      <div 
                        v-for="stage in videoImportStore.videoStages[video.id]" 
                        :key="stage.stageId"
                        class="stage-mini-item"
                        :data-status="stage.status"
                        :title="`${stage.label}: ${stage.status}`"
                      ></div>
                    </div>
                  </div>

                  <div v-if="video.errorMessage" class="video-card__error">
                    <span class="material-symbols-outlined">error</span>
                    <span>{{ video.errorMessage }}</span>
                  </div>
                </div>
                
                <div class="video-card__footer">
                   <div class="footer-actions">
                     <Button 
                       variant="secondary" 
                       size="sm" 
                       @click.stop="videoImportStore.removeVideo(video.id)"
                       :disabled="videoImportStore.status === 'applying'"
                     >
                       移除
                     </Button>
                     <Button 
                       variant="brand" 
                       size="sm" 
                       @click.stop="handleApplyExtraction(video.id)"
                       :running="isApplying(video.id)"
                       :disabled="videoImportStore.status === 'applying' || video.status !== 'ready'"
                     >
                       应用至项目
                     </Button>
                   </div>
                </div>
              </Card>
            </transition-group>
          </div>
        </div>

        <aside class="video-rail">
           <!-- 视频详情与阶段进度面板 -->
           <Card v-if="selectedVideo" class="rail-card detail-panel">
              <div class="rail-card__header">
                <h3>视频详情</h3>
                <Button variant="ghost" size="sm" @click="selectedVideoId = null">
                  <span class="material-symbols-outlined">close</span>
                </Button>
              </div>
              <div class="rail-card__body">
                <div class="detail-info">
                  <div class="detail-row">
                    <span>文件名</span>
                    <strong>{{ selectedVideo.fileName }}</strong>
                  </div>
                  <div class="detail-row">
                    <span>状态</span>
                    <Chip :variant="selectedVideo.status === 'ready' ? 'success' : 'info'" size="sm">
                       {{ selectedVideo.status === "ready" ? "解析就绪" : "处理中" }}
                    </Chip>
                  </div>
                </div>

                <div class="stages-section">
                  <h4>拆解阶段进度</h4>
                  <div class="stages-list">
                    <div v-for="stage in selectedVideoStages" :key="stage.stageId" class="stage-item">
                      <div class="stage-item__header">
                        <div class="stage-item__label">
                          <span class="material-symbols-outlined" :data-status="stage.status">
                            {{ getStageIcon(stage.status) }}
                          </span>
                          <span>{{ stage.label }}</span>
                        </div>
                        <div class="stage-item__status" :data-status="stage.status">
                          {{ formatStageStatus(stage.status) }}
                        </div>
                      </div>

                      <div v-if="stage.status === 'running' || stage.status === 'queued'" class="stage-item__progress">
                        <div class="progress-bar">
                          <div class="progress-fill" :style="{ width: `${stage.progressPct}%` }"></div>
                        </div>
                        <span class="progress-text">{{ stage.progressPct }}%</span>
                      </div>

                      <div v-if="stage.errorMessage" class="stage-item__error">
                        <p>{{ stage.errorMessage }}</p>
                        <div v-if="stage.nextAction" class="next-action">
                          建议：{{ stage.nextAction }}
                        </div>
                      </div>

                      <div class="stage-item__actions">
                        <Button 
                          v-if="stage.canRerun" 
                          variant="secondary" 
                          size="sm" 
                          @click="handleRerunStage(selectedVideo.id, stage.stageId)"
                        >
                          <template #leading><span class="material-symbols-outlined">refresh</span></template>
                          重新运行
                        </Button>
                        <Button 
                          v-if="stage.status === 'provider_required'" 
                          variant="primary" 
                          size="sm" 
                          @click="handleConfigureProvider"
                        >
                          <template #leading><span class="material-symbols-outlined">settings</span></template>
                          配置 Provider
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
           </Card>

           <Card v-else class="rail-card">
              <div class="rail-card__header">
                <h3>项目策划同步</h3>
              </div>
              <div class="rail-card__body">
                 <p>点击「应用至项目」后，该素材拆解出的脚本和分镜将覆盖当前项目的策划面板。</p>
                 
                 <div class="rail-metric">
                    <span>当前脚本版本</span>
                    <strong>v{{ projectStore.currentProject?.currentScriptVersion ?? 0 }}</strong>
                 </div>
                 <div class="rail-metric">
                    <span>当前分镜版本</span>
                    <strong>v{{ projectStore.currentProject?.currentStoryboardVersion ?? 0 }}</strong>
                 </div>

                 <div class="sync-hint">
                    <span class="material-symbols-outlined">info</span>
                    <p>素材拆解完成后，后端将自动同步转录文本与视觉摘要。</p>
                 </div>
              </div>
           </Card>
           
           <Card v-if="!selectedVideo" class="rail-card mt-4">
              <div class="rail-card__header">
                <h3>拆解流说明</h3>
              </div>
              <div class="rail-card__body">
                 <ul class="step-list">
                    <li><span class="step-num">1</span> 导入本地 MP4 素材</li>
                    <li><span class="step-num">2</span> 自动触发 AI 语音转录</li>
                    <li><span class="step-num">3</span> 识别视觉转场与分段</li>
                    <li><span class="step-num">4</span> 提取脚本结构与分镜描述</li>
                 </ul>
              </div>
           </Card>
        </aside>
      </div>
    </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

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
const router = useRouter();

const activeApplyingVideoId = ref<string | null>(null);
const selectedVideoId = ref<string | null>(null);

const currentProjectId = computed(() => projectStore.currentProject?.projectId ?? "");
const videoErrorSummary = computed(() => {
  if (!videoImportStore.error) return "";
  return videoImportStore.error.requestId
    ? `${videoImportStore.error.message}（${videoImportStore.error.requestId}）`
    : videoImportStore.error.message;
});

const selectedVideo = computed(() => {
  if (!selectedVideoId.value) return null;
  return videoImportStore.videos.find(v => v.id === selectedVideoId.value) || null;
});

const selectedVideoStages = computed(() => {
  if (!selectedVideoId.value) return [];
  return videoImportStore.videoStages[selectedVideoId.value] || [];
});

const isFfprobeUnavailable = computed(() => {
  // Global check: if any video has a stage with media.ffprobe_unavailable
  return Object.values(videoImportStore.videoStages).some(stages => 
    stages.some(s => s.errorCode === 'media.ffprobe_unavailable')
  ) || videoImportStore.error?.details?.error_code === 'media.ffprobe_unavailable' || 
     videoImportStore.error?.message?.includes('FFprobe 不可用');
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

watch(() => videoImportStore.videos, (videos) => {
  // Load stages for videos that don't have them yet
  videos.forEach(v => {
    if (!videoImportStore.videoStages[v.id]) {
      void videoImportStore.loadVideoStages(v.id);
    }
  });
}, { immediate: true });

async function handleImportVideo(): Promise<void> {
  if (!currentProjectId.value) return;

  const filePath = await pickVideoFilePath();
  if (!filePath) return;

  const video = await videoImportStore.importVideoFile(currentProjectId.value, filePath);
  if (video) {
    void videoImportStore.loadVideoStages(video.id);
  }
}

async function handleApplyExtraction(videoId: string): Promise<void> {
  if (!confirm("应用提取结果将覆盖项目当前的脚本和分镜修订版。确定继续吗？")) return;
  
  activeApplyingVideoId.value = videoId;
  try {
    await videoImportStore.applyExtraction(videoId);
    // Optional: provide success feedback
  } finally {
    activeApplyingVideoId.value = null;
  }
}

async function handleRescan(): Promise<void> {
  await videoImportStore.reScanRuntime();
}

function handleViewSetupGuide(): void {
  // 跳转到系统设置的诊断锚点，引导用户检查 FFprobe 可用性
  void router.push({ path: "/settings/ai-system", query: { section: "diagnostics", reason: "ffprobe" } });
}

function isApplying(videoId: string): boolean {
  return videoImportStore.status === 'applying' && activeApplyingVideoId.value === videoId;
}

function selectVideo(videoId: string): void {
  selectedVideoId.value = videoId;
  void videoImportStore.loadVideoStages(videoId);
}

async function handleRerunStage(videoId: string, stageId: string): Promise<void> {
  await videoImportStore.rerunStage(videoId, stageId);
}

function handleConfigureProvider(): void {
  // 跳转到 AI Provider 配置抽屉，由设置页根据 query 自动展开
  void router.push({ path: "/settings/ai-system", query: { section: "providers" } });
}

function getStageIcon(status: string): string {
  switch (status) {
    case 'succeeded': return 'check_circle';
    case 'failed':
    case 'failed_degraded': return 'error';
    case 'running': return 'sync';
    case 'queued': return 'schedule';
    case 'provider_required': return 'account_circle';
    case 'blocked': return 'block';
    default: return 'help_outline';
  }
}

function formatStageStatus(status: string): string {
  switch (status) {
    case 'succeeded': return '已完成';
    case 'failed': return '已失败';
    case 'failed_degraded': return '降级完成';
    case 'running': return '运行中';
    case 'queued': return '队列中';
    case 'provider_required': return '需配置 Provider';
    case 'blocked': return '已阻塞';
    default: return status;
  }
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
  if (value === null) return "时长待识别";
  const mins = Math.floor(value / 60);
  const secs = Math.round(value % 60);
  return mins > 0 ? `${mins}分${secs}秒` : `${secs}秒`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

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

.ffprobe-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  background: #FFFBE6;
  border: 1px solid #FFE58F;
  border-radius: var(--radius-md);
  margin-bottom: var(--space-6);
  color: #856404;
}

.ffprobe-alert__content {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.ffprobe-alert__content .material-symbols-outlined {
  color: #FAAD14;
  font-size: 24px;
}

.ffprobe-alert__text strong {
  display: block;
  font: var(--font-title-sm);
  margin-bottom: 2px;
}

.ffprobe-alert__text p {
  margin: 0;
  font: var(--font-body-sm);
}

.ffprobe-alert__actions {
  display: flex;
  gap: var(--space-3);
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
  padding: var(--space-2);
  background: var(--color-bg-muted);
  border-radius: var(--radius-sm);
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
}

.footer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
}

.video-card[active="true"] {
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 1px var(--color-brand-primary), var(--shadow-md);
}

.video-card__stages-summary {
  margin-top: 4px;
}

.stage-mini-list {
  display: flex;
  gap: 4px;
}

.stage-mini-item {
  width: 12px;
  height: 4px;
  border-radius: 2px;
  background: var(--color-bg-muted);
}

.stage-mini-item[data-status="succeeded"] { background: var(--color-success); }
.stage-mini-item[data-status="running"] { background: var(--color-brand-primary); animation: pulse 1.5s infinite; }
.stage-mini-item[data-status="failed"], .stage-mini-item[data-status="failed_degraded"] { background: var(--color-danger); }
.stage-mini-item[data-status="queued"] { background: var(--color-text-tertiary); }
.stage-mini-item[data-status="provider_required"] { background: var(--color-warning); }

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

.detail-panel {
  position: sticky;
  top: var(--space-4);
  max-height: calc(100vh - 120px);
  overflow-y: auto;
}

.detail-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font: var(--font-body-sm);
}

.detail-row span {
  color: var(--color-text-secondary);
}

.stages-section {
  margin-top: var(--space-4);
}

.stages-section h4 {
  margin: 0 0 var(--space-3) 0;
  font: var(--font-title-sm);
  color: var(--color-text-primary);
}

.stages-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.stage-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
}

.stage-item__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stage-item__label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font: var(--font-title-xs);
  color: var(--color-text-primary);
}

.stage-item__label .material-symbols-outlined {
  font-size: 18px;
}

.stage-item__label .material-symbols-outlined[data-status="succeeded"] { color: var(--color-success); }
.stage-item__label .material-symbols-outlined[data-status="running"] { color: var(--color-brand-primary); animation: spin 2s linear infinite; }
.stage-item__label .material-symbols-outlined[data-status="failed"], 
.stage-item__label .material-symbols-outlined[data-status="failed_degraded"] { color: var(--color-danger); }

.stage-item__status {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.stage-item__progress {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--color-border-default);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-brand-primary);
}

.progress-text {
  font: var(--font-caption);
  color: var(--color-brand-primary);
  min-width: 32px;
  text-align: right;
}

.stage-item__error {
  font: var(--font-body-xs);
  color: var(--color-danger);
  background: rgba(255, 90, 99, 0.05);
  padding: var(--space-2);
  border-radius: var(--radius-sm);
}

.stage-item__error p { margin: 0; }

.next-action {
  margin-top: 4px;
  font-weight: bold;
}

.stage-item__actions {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-1);
}

.video-rail {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
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

.sync-hint {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3);
  background: color-mix(in srgb, var(--color-brand-primary) 8%, transparent);
  border-radius: var(--radius-md);
  color: var(--color-brand-primary);
}

.sync-hint .material-symbols-outlined {
  font-size: 18px;
}

.sync-hint p {
  margin: 0;
  font: var(--font-caption);
  line-height: 1.4;
}

.step-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.step-list li {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
}

.step-num {
  width: 20px;
  height: 20px;
  border-radius: 99px;
  background: var(--color-brand-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: bold;
}

.mt-4 {
  margin-top: var(--space-4);
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
