<template>
  <ProjectContextGuard>
    <div class="page-container" data-video-page="deconstruction">
      <input
        ref="videoFileInputRef"
        data-testid="video-file-picker"
        class="visually-hidden-file-input"
        type="file"
        accept="video/mp4,video/quicktime,video/x-matroska,video/webm"
        @change="handleBrowserFileSelected"
      />

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
              data-testid="video-import-button"
              data-action="import-video"
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

      <div v-if="filePickerMessage" class="dashboard-alert" data-tone="warning">
        {{ filePickerMessage }}
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
                    <span class="metric-item"><span class="material-symbols-outlined">straighten</span>{{ formatResolution(video.width, video.height) }}</span>
                    <span class="metric-item"><span class="material-symbols-outlined">hard_drive</span>{{ formatFileSize(video.fileSizeBytes) }}</span>
                  </div>

                  <!-- 拆解状态摘要 -->
                  <div v-if="videoImportStore.videoStages[video.id]" class="video-card__stages-summary">
                    <div class="stage-mini-list">
                      <div 
                        v-for="stage in videoImportStore.videoStages[video.id]" 
                        :key="stage.stageId"
                        class="stage-mini-item"
                        :data-status="getStageDisplayStatus(video.id, stage)"
                        :title="`${stage.label}: ${formatStageDisplayStatus(video.id, stage)}`"
                      ></div>
                    </div>
                  </div>

                  <div v-if="video.errorMessage" class="video-card__error">
                    <span class="material-symbols-outlined">error</span>
                    <span>{{ formatVideoErrorMessage(video.errorMessage) }}</span>
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
                       variant="primary"
                       size="sm"
                       @click.stop="handleDeconstructVideo(video.id)"
                       :running="isDeconstructing(video.id)"
                       :disabled="videoImportStore.status === 'deconstructing' || video.status !== 'ready'"
                     >
                       {{ hasResult(video.id) ? "重新拆解" : "开始拆解" }}
                     </Button>
                     <Button
                       variant="brand"
                       size="sm"
                       @click.stop="handleApplyExtraction(video.id)"
                       :running="isApplying(video.id)"
                       :disabled="videoImportStore.status === 'applying' || !hasStructureResult(video.id)"
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
           <Card v-if="selectedVideo" class="rail-card result-panel">
              <div class="rail-card__header">
                <div>
                  <h3>提取结果</h3>
                  <p>{{ selectedVideo.fileName }}</p>
                </div>
                <Button variant="ghost" size="sm" @click="selectedVideoId = null">
                  <span class="material-symbols-outlined">close</span>
                </Button>
              </div>
              <div class="rail-card__body">
                <AssetPreview :asset="mapToAsset(selectedVideo)" variant="card" />

                <div class="result-actions">
                  <Button
                    variant="primary"
                    size="sm"
                    :running="isDeconstructing(selectedVideo.id)"
                    :disabled="videoImportStore.status === 'deconstructing' || selectedVideo.status !== 'ready'"
                    @click="handleDeconstructVideo(selectedVideo.id)"
                  >
                    <template #leading><span class="material-symbols-outlined">auto_awesome</span></template>
                    {{ hasResult(selectedVideo.id) ? "重新拆解" : "开始拆解" }}
                  </Button>
                  <Button
                    variant="brand"
                    size="sm"
                    :running="isApplying(selectedVideo.id)"
                    :disabled="videoImportStore.status === 'applying' || !hasStructureResult(selectedVideo.id)"
                    @click="handleApplyExtraction(selectedVideo.id)"
                  >
                    <template #leading><span class="material-symbols-outlined">ios_share</span></template>
                    应用至项目
                  </Button>
                </div>

                <VideoResultView
                  v-model:active-tab="activeResultTab"
                  :tabs="resultTabs"
                  :script-lines="selectedTranscriptLines"
                  :script-empty-title="selectedScriptEmptyTitle"
                  :script-empty-description="selectedScriptEmptyDescription"
                  :needs-provider-configuration="selectedNeedsProviderConfiguration"
                  :keyframes="selectedKeyframes"
                  :structure-tags="selectedStructureTags"
                  :structure-blocks="selectedStructureBlocks"
                  :can-copy-script="Boolean(selectedTranscriptText)"
                  :can-copy-structure="Boolean(selectedStructureClipboardText)"
                  @copy-script="copySelectedTranscript"
                  @copy-structure="copySelectedStructure"
                  @configure-provider="handleConfigureProvider"
                />

                <div v-if="selectedVideoStages.length > 0" class="compact-stages">
                  <div
                    v-for="stage in selectedVideoStages"
                    :key="stage.stageId"
                    class="compact-stage"
                    :data-status="getStageDisplayStatus(selectedVideo.id, stage)"
                  >
                    <span class="material-symbols-outlined">{{ getStageIcon(getStageDisplayStatus(selectedVideo.id, stage)) }}</span>
                    <strong>{{ stage.label }}</strong>
                    <small>{{ formatStageDisplayStatus(selectedVideo.id, stage) }}</small>
                    <Button
                      v-if="canRerunStageFromPanel(selectedVideo.id, stage)"
                      variant="ghost"
                      size="sm"
                      @click="handleRerunStage(selectedVideo.id, stage.stageId)"
                    >
                      重试
                    </Button>
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
                    <p>素材拆解完成后，后端将同步视频解析出的脚本文案、视觉摘要和内容结构。</p>
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
                    <li><span class="step-num">2</span> 点击开始拆解</li>
                    <li><span class="step-num">3</span> 调用视频解析模型生成画面与语音时间轴</li>
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
import { computed, inject, onMounted, ref, watch } from "vue";
import { routerKey } from "vue-router";
import type { Router } from "vue-router";

import AssetPreview from "@/components/assets/AssetPreview.vue";
import { fetchRuntimeMediaDiagnostics } from "@/app/runtime-client";
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { useProjectStore } from "@/stores/project";
import { useTaskBusStore } from "@/stores/task-bus";
import { useVideoImportStore } from "@/stores/video-import";
import type { TaskInfo } from "@/types/task-events";
import type {
  AssetDto,
  ImportedVideo,
  MediaDiagnostics,
  VideoDeconstructionResultDto,
  VideoKeyframeDto,
  VideoSegmentDto,
  VideoStageDto
} from "@/types/runtime";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import VideoResultView from "./components/VideoResultView.vue";
import {
  buildScriptDisplayLines,
  buildStandardStructureBlocks,
  buildStructureTags,
  hasContentStructurePayload,
  serializeStructureBlocks,
  type VideoResultTabId,
  type VideoStructureDisplayBlock
} from "./video-result-presenters";

const projectStore = useProjectStore();
const taskBusStore = useTaskBusStore();
const videoImportStore = useVideoImportStore();
const router = inject<Router | null>(routerKey, null);

const activeApplyingVideoId = ref<string | null>(null);
const activeDeconstructingVideoId = ref<string | null>(null);
const selectedVideoId = ref<string | null>(null);
const activeResultTab = ref<VideoResultTabId>("script");
const videoFileInputRef = ref<HTMLInputElement | null>(null);
const pendingFilePickerResolve = ref<((path: string | null) => void) | null>(null);
const filePickerMessage = ref<string | null>(null);
const mediaDiagnostics = ref<MediaDiagnostics | null>(null);

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

const selectedResult = computed(() => {
  if (!selectedVideoId.value) return null;
  return videoImportStore.results[selectedVideoId.value] ?? null;
});

const selectedTranscript = computed(() => {
  if (!selectedVideoId.value) return null;
  return videoImportStore.transcripts[selectedVideoId.value] ?? null;
});

const selectedTranscriptText = computed(() => {
  const standardText = selectedResult.value?.script?.fullText?.trim();
  if (standardText) return standardText;
  const transcriptText = selectedTranscript.value?.text?.trim();
  if (transcriptText) return transcriptText;
  return selectedSegments.value
    .map((segment) => segment.transcriptText?.trim())
    .filter(Boolean)
    .join("\n");
});

const selectedTranscriptLines = computed(() => {
  return buildScriptDisplayLines(selectedResult.value, selectedTranscriptText.value);
});

const selectedSegments = computed(() => {
  if (!selectedVideoId.value) return [];
  return videoImportStore.segments[selectedVideoId.value] ?? [];
});

const selectedStructure = computed(() => {
  if (!selectedVideoId.value) return null;
  return videoImportStore.structures[selectedVideoId.value] ?? null;
});

const selectedKeyframes = computed(() => {
  const standardKeyframes = selectedResult.value?.keyframes ?? [];
  if (standardKeyframes.length > 0) return standardKeyframes;
  return selectedSegments.value.map(segmentToKeyframe);
});

const selectedHasPersistedResult = computed(() => {
  return selectedVideoId.value ? hasPersistedResultForVideo(selectedVideoId.value) : false;
});

const selectedResultIsIncomplete = computed(() => {
  return Boolean(selectedResult.value && !hasStandardResultContent(selectedResult.value));
});

const selectedNeedsProviderConfiguration = computed(() => {
  if (selectedHasPersistedResult.value || videoImportStore.status !== "error") return false;
  return selectedVideoStages.value.some((stage) => stage.status === "provider_required" && stage.isCurrent);
});

const selectedScriptEmptyTitle = computed(() => {
  if (selectedResultIsIncomplete.value) return "解析结果不完整";
  if (selectedNeedsProviderConfiguration.value) return "视频解析模型未就绪";
  if (selectedHasPersistedResult.value) return "当前结果暂无脚本文案";
  return "等待开始拆解";
});

const selectedScriptEmptyDescription = computed(() => {
  if (selectedResultIsIncomplete.value) {
    return "当前模型没有返回可用的脚本文案、视频关键帧或内容结构，请确认模型支持视频输入后重新拆解。";
  }
  if (selectedNeedsProviderConfiguration.value) {
    return "当前视频解析模型不可用，请配置一个支持视频输入的多模态模型，例如 Doubao-Seed-2.0-pro。";
  }
  if (selectedHasPersistedResult.value) {
    return "当前拆解结果没有返回可复制的脚本文案，可点击“重新拆解”刷新视频解析结果。";
  }
  if (isDeconstructing(selectedVideoId.value ?? "")) {
    return "正在生成脚本文案、视频关键帧和内容结构，请稍候。";
  }
  return "点击“开始拆解”后，系统会调用视频解析模型生成脚本文案、视频关键帧和内容结构。";
});

const selectedStructureBlocks = computed(() => {
  const standardStructure = selectedResult.value?.contentStructure;
  const standardBlocks = buildStandardStructureBlocks(standardStructure);
  if (standardBlocks.length > 0) {
    return standardBlocks;
  }
  const video = selectedVideo.value;
  const structure = selectedStructure.value;
  if (!video || !structure?.scriptJson) return [];
  try {
    const payload = JSON.parse(structure.scriptJson) as {
      summary?: Record<string, unknown>;
      segments?: Array<{ label?: string | null; transcriptText?: string | null }>;
    };
    const summary = payload.summary ?? {};
    return [
      {
        id: "fallback-summary",
        title: "素材概况",
        body: `${String(summary.fileName ?? video.fileName)}，${formatDuration(video.durationSeconds)}，${formatResolution(video.width, video.height)}。`,
        evidence: ["来自视频基础元数据，仅作为未生成标准结构时的兜底。"],
        tone: "scene" as const
      },
      {
        id: "fallback-script",
        title: "可复用脚本",
        body: selectedTranscriptText.value || "暂未生成可复用脚本文案。",
        evidence: ["优先使用转录文本，便于继续回流脚本工作面。"],
        tone: "proof" as const
      },
      {
        id: "fallback-segments",
        title: "分段结构",
        body: `已识别 ${payload.segments?.length ?? selectedSegments.value.length} 个基础段落，可继续回流到脚本和分镜。`,
        evidence: ["基础段落可作为重新拆解或人工校对的起点。"],
        tone: "value" as const
      }
    ] satisfies VideoStructureDisplayBlock[];
  } catch (error) {
    console.error("解析视频结构结果失败", error);
    return [];
  }
});

const selectedStructureTags = computed(() => {
  return buildStructureTags(selectedResult.value?.contentStructure);
});

const selectedStructureClipboardText = computed(() => {
  return serializeStructureBlocks(selectedStructureBlocks.value);
});

const resultTabs = [
  { id: "script" as const, label: "脚本文案", icon: "description" },
  { id: "keyframes" as const, label: "视频关键帧", icon: "table_chart" },
  { id: "structure" as const, label: "内容结构", icon: "auto_graph" }
];

const isFfprobeUnavailable = computed(() => {
  const status = mediaDiagnostics.value?.ffprobe.status;
  return (
    status === "unavailable" ||
    status === "incompatible" ||
    videoImportStore.error?.details?.error_code === "media.ffprobe_unavailable" ||
    videoImportStore.error?.message?.includes("FFprobe 不可用")
  );
});

onMounted(() => {
  videoImportStore.initializeWebSocket();
  void refreshMediaDiagnostics();
  if (currentProjectId.value && videoImportStore.videos.length === 0) {
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

  filePickerMessage.value = null;
  const filePath = await pickVideoFilePath();
  if (filePath === null) return;
  if (!filePath) {
    filePickerMessage.value = "已打开文件选择器，但当前运行环境没有返回完整本地路径。请在桌面端使用原生选择器，或检查 Tauri 文件选择插件。";
    return;
  }

  const video = await videoImportStore.importVideoFile(currentProjectId.value, filePath);
  if (video) {
    selectedVideoId.value = video.id;
    void videoImportStore.loadVideoStages(video.id);
  }
}

async function handleDeconstructVideo(videoId: string): Promise<void> {
  activeDeconstructingVideoId.value = videoId;
  selectedVideoId.value = videoId;
  try {
    await videoImportStore.deconstructVideoFile(videoId);
  } finally {
    activeDeconstructingVideoId.value = null;
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
  await refreshMediaDiagnostics();
  await videoImportStore.reScanRuntime();
}

function handleViewSetupGuide(): void {
  // 跳转到系统设置的诊断锚点，引导用户检查 FFprobe 可用性
  if (!router) return;
  void router.push({ path: "/settings/ai-system", query: { section: "diagnostics", reason: "ffprobe" } });
}

function isApplying(videoId: string): boolean {
  return videoImportStore.status === 'applying' && activeApplyingVideoId.value === videoId;
}

function isDeconstructing(videoId: string): boolean {
  return videoImportStore.status === "deconstructing" && activeDeconstructingVideoId.value === videoId;
}

function hasResult(videoId: string): boolean {
  return hasPersistedResultForVideo(videoId);
}

function hasStructureResult(videoId: string): boolean {
  return videoImportStore.structures[videoId]?.status === "succeeded";
}

function selectVideo(videoId: string): void {
  selectedVideoId.value = videoId;
  void videoImportStore.loadVideoResult(videoId);
}

async function handleRerunStage(videoId: string, stageId: string): Promise<void> {
  await videoImportStore.rerunStage(videoId, stageId);
}

async function copySelectedTranscript(): Promise<void> {
  if (!selectedTranscriptText.value) return;
  await navigator.clipboard?.writeText(selectedTranscriptText.value);
}

async function copySelectedStructure(): Promise<void> {
  if (!selectedStructureClipboardText.value) return;
  await navigator.clipboard?.writeText(selectedStructureClipboardText.value);
}

function handleConfigureProvider(): void {
  if (!router) return;
  void router.push({ path: "/settings/ai-system", query: { section: "providers" } });
}

function segmentToKeyframe(segment: VideoSegmentDto): VideoKeyframeDto {
  const metadata = parseSegmentMetadata(segment.metadataJson);
  return {
    index: segment.segmentIndex,
    startMs: segment.startMs,
    endMs: segment.endMs,
    visual: metadata.visual ?? "",
    speech: segment.transcriptText ?? metadata.speech ?? "",
    onscreenText: metadata.onscreenText ?? "",
    shotType: metadata.shotType ?? "",
    camera: metadata.camera ?? "",
    intent: segment.label ?? metadata.intent ?? ""
  };
}

function parseSegmentMetadata(metadataJson: string | null): Partial<VideoKeyframeDto> {
  if (!metadataJson) return {};
  try {
    const payload = JSON.parse(metadataJson) as Record<string, unknown>;
    return {
      visual: typeof payload.visual === "string" ? payload.visual : undefined,
      speech: typeof payload.speech === "string" ? payload.speech : undefined,
      onscreenText: typeof payload.onscreenText === "string" ? payload.onscreenText : undefined,
      shotType: typeof payload.shotType === "string" ? payload.shotType : undefined,
      camera: typeof payload.camera === "string" ? payload.camera : undefined,
      intent: typeof payload.intent === "string" ? payload.intent : undefined
    };
  } catch (error) {
    console.error("解析视频片段元数据失败", error);
    return {};
  }
}

function formatVideoErrorMessage(message: string): string {
  if (isHistoricalFfprobeFailure(message)) {
    return "上次导入时 FFprobe 不可用。当前检测已正常，请重新运行导入阶段刷新视频元数据。";
  }
  return message;
}

function formatStageErrorMessage(stage: VideoStageDto): string {
  if (stage.errorMessage && isHistoricalFfprobeFailure(stage.errorMessage)) {
    return "上次导入时 FFprobe 不可用，视频元数据没有成功写入。";
  }
  return stage.errorMessage ?? "";
}

function formatStageNextAction(stage: VideoStageDto): string {
  if (stage.errorCode === "media.ffprobe_unavailable" && isMediaDiagnosticReady.value) {
    return "FFprobe 当前已可用，请点击“重新运行”刷新本视频元数据。";
  }
  return stage.nextAction ?? "";
}

function hasPersistedResultForVideo(videoId: string): boolean {
  const result = videoImportStore.results[videoId];
  if (result) {
    return Boolean(
      result.script?.fullText?.trim() ||
      result.script?.lines?.length ||
      result.keyframes?.length ||
      result.structure.status === "succeeded"
    );
  }
  const transcriptText = videoImportStore.transcripts[videoId]?.text?.trim();
  const segments = videoImportStore.segments[videoId] ?? [];
  const hasSegmentText = segments.some((segment) => Boolean(segment.transcriptText?.trim()));
  const structure = videoImportStore.structures[videoId];
  return Boolean(transcriptText || hasSegmentText || segments.length > 0 || structure?.status === "succeeded");
}

function hasStandardResultContent(result: VideoDeconstructionResultDto): boolean {
  return Boolean(
    result.script?.fullText?.trim() ||
    result.script?.lines?.some((line) => line.text.trim()) ||
    result.keyframes?.some((keyframe) => keyframe.visual || keyframe.speech || keyframe.onscreenText) ||
    hasContentStructurePayload(result.contentStructure)
  );
}

function isStaleProviderStage(videoId: string, stage: VideoStageDto): boolean {
  return stage.status === "provider_required" && hasPersistedResultForVideo(videoId);
}

function getStageDisplayStatus(videoId: string, stage: VideoStageDto): string {
  return isStaleProviderStage(videoId, stage) ? "succeeded" : stage.status;
}

function formatStageDisplayStatus(videoId: string, stage: VideoStageDto): string {
  if (isStaleProviderStage(videoId, stage)) return "历史已覆盖";
  return formatStageStatus(stage.status);
}

function canRerunStageFromPanel(videoId: string, stage: VideoStageDto): boolean {
  return stage.canRerun && stage.status !== "succeeded" && !isStaleProviderStage(videoId, stage);
}

const isMediaDiagnosticReady = computed(() => mediaDiagnostics.value?.ffprobe.status === "ready");

function isHistoricalFfprobeFailure(message: string): boolean {
  return isMediaDiagnosticReady.value && message.includes("FFprobe 不可用");
}

async function refreshMediaDiagnostics(): Promise<void> {
  try {
    mediaDiagnostics.value = await fetchRuntimeMediaDiagnostics();
  } catch (error) {
    console.error("刷新媒体诊断失败", error);
  }
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
    case 'provider_required': return '需配置视频解析模型';
    case 'blocked': return '已阻塞';
    default: return status;
  }
}

async function pickVideoFilePath(): Promise<string | null> {
  const tauriPath = await pickVideoWithTauriDialog();
  if (tauriPath) return tauriPath;
  return pickVideoWithBrowserInput();
}

async function pickVideoWithTauriDialog(): Promise<string | null> {
  try {
    const dialog = await import("@tauri-apps/plugin-dialog");
    const selected = await dialog.open({
      multiple: false,
      filters: [{ name: "Video", extensions: ["mp4", "mov", "mkv", "webm"] }]
    });
    if (typeof selected === "string") return selected;
    if (Array.isArray(selected)) return selected[0] ?? null;
    return null;
  } catch {
    return null;
  }
}

function pickVideoWithBrowserInput(): Promise<string | null> {
  const input = videoFileInputRef.value;
  if (!input) return Promise.resolve("");

  pendingFilePickerResolve.value?.(null);
  return new Promise((resolve) => {
    pendingFilePickerResolve.value = resolve;
    input.value = "";
    input.click();
  });
}

function handleBrowserFileSelected(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  const path = resolveBrowserSelectedFilePath(file);
  resolvePendingFilePicker(file ? path : null);
  input.value = "";
}

function resolvePendingFilePicker(path: string | null): void {
  pendingFilePickerResolve.value?.(path);
  pendingFilePickerResolve.value = null;
}

function resolveBrowserSelectedFilePath(file: File | undefined): string {
  if (!file) return "";
  const fileWithPath = file as File & { path?: string; webkitRelativePath?: string };
  return (fileWithPath.path ?? fileWithPath.webkitRelativePath ?? "").trim();
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

function formatResolution(width: number | null, height: number | null): string {
  if (!width || !height) {
    return "分辨率待识别";
  }
  return `${width} × ${height}`;
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

<style scoped src="./video-deconstruction-center.css"></style>
