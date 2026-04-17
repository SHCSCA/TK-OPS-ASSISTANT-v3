<template>
  <ProjectContextGuard>
    <section class="video-page" data-video-page="deconstruction">
      <header class="hero">
        <div class="hero__copy">
          <span class="hero__kicker">M06 视频拆解中心</span>
          <h1>导入真实视频，拆出可回流的素材基线。</h1>
          <p>
            这里只保留真实导入、元信息读取、任务反馈和明确阻断说明。
            转写、切段和 AI 结构拆解未接通时，不伪造完成结果。
          </p>
          <div class="hero__meta">
            <span class="pill pill--brand">{{ currentProjectName }}</span>
            <span class="pill" :data-state="pageStateTone">{{ pageStateLabel }}</span>
            <span class="pill">{{ videoImportStore.videos.length }} 个视频记录</span>
          </div>
        </div>

        <div class="hero__actions">
          <button
            class="action-button action-button--primary"
            data-action="import-video"
            data-testid="video-import-button"
            :disabled="importDisabled"
            type="button"
            @click="handleImportVideo"
          >
            {{ importButtonLabel }}
          </button>
          <button
            class="action-button action-button--secondary"
            data-testid="video-refresh-button"
            :disabled="!currentProjectId || videoImportStore.status === 'loading'"
            type="button"
            @click="refreshVideos"
          >
            {{ videoImportStore.status === "loading" ? "刷新中" : "刷新列表" }}
          </button>
        </div>
      </header>

      <section class="state-banner" :data-state="stateBannerTone">
        <div class="state-banner__body">
          <strong>{{ stateBannerTitle }}</strong>
          <p>{{ stateBannerCopy }}</p>
        </div>
        <div class="state-banner__tags">
          <span>导入链路：{{ importLinkLabel }}</span>
          <span>任务反馈：{{ taskFeedbackLabel }}</span>
          <span>阻断说明：{{ blockedLabel }}</span>
        </div>
      </section>

      <section class="workspace-grid">
        <div class="workspace-grid__main">
          <div class="section-head">
            <div>
              <p class="section-head__kicker">导入列表</p>
              <h2>{{ listTitle }}</h2>
            </div>
            <span class="section-chip">{{ videoImportStore.videos.length }} 条记录</span>
          </div>

          <div v-if="videoImportStore.status === 'loading'" class="state-surface state-surface--loading">
            <strong>正在读取当前项目的视频记录。</strong>
            <p>导入列表会在 Runtime 返回后展开，未完成前不展示伪造解析结果。</p>
          </div>

          <div v-else-if="videoImportStore.status === 'error'" class="state-surface state-surface--error">
            <strong>视频拆解列表读取失败。</strong>
            <p>{{ videoErrorSummary }}</p>
            <button class="action-button action-button--secondary" type="button" @click="refreshVideos">
              重新加载
            </button>
          </div>

          <div v-else-if="videoImportStore.videos.length === 0" class="state-surface state-surface--empty">
            <strong>当前项目还没有导入视频。</strong>
            <p>
              先把本地视频纳入当前项目，后续的元信息、任务队列和拆解链路才会按真实数据展开。
            </p>
            <button
              class="action-button action-button--primary"
              :disabled="importDisabled"
              type="button"
              @click="handleImportVideo"
            >
              {{ importButtonLabel }}
            </button>
          </div>

          <div v-else class="video-grid">
            <article
              v-for="video in videoImportStore.videos"
              :key="video.id"
              class="video-card"
              :class="{ 'video-card--selected': video.id === selectedVideoId }"
              role="button"
              tabindex="0"
              @click="selectVideo(video.id)"
              @keydown.enter.prevent="selectVideo(video.id)"
              @keydown.space.prevent="selectVideo(video.id)"
            >
              <div class="video-card__top">
                <div class="video-card__title-block">
                  <p class="video-card__eyebrow">{{ video.codec ?? "codec 待识别" }}</p>
                  <h3>{{ video.fileName }}</h3>
                </div>
                <span class="status-chip" :data-state="videoTone(video)">{{ videoStateLabel(video) }}</span>
              </div>

              <p class="video-card__path">{{ video.filePath }}</p>

              <dl class="video-card__meta">
                <div>
                  <dt>时长</dt>
                  <dd>{{ formatDuration(video.durationSeconds) }}</dd>
                </div>
                <div>
                  <dt>分辨率</dt>
                  <dd>{{ formatResolution(video.width, video.height) }}</dd>
                </div>
                <div>
                  <dt>帧率</dt>
                  <dd>{{ formatFrameRate(video.frameRate) }}</dd>
                </div>
                <div>
                  <dt>体积</dt>
                  <dd>{{ formatFileSize(video.fileSizeBytes) }}</dd>
                </div>
              </dl>

              <div v-if="taskForVideo(video.id)" class="task-panel">
                <div class="task-panel__row">
                  <span>{{ taskLabel(video.id) }}</span>
                  <strong>{{ taskForVideo(video.id)?.progress ?? 0 }}%</strong>
                </div>
                <div class="task-panel__bar" :aria-label="taskLabel(video.id)">
                  <span :style="taskProgressStyle(video.id)"></span>
                </div>
                <p>{{ taskMessage(video.id) }}</p>
              </div>

              <p v-else-if="video.status === 'imported'" class="video-card__hint">
                已写入项目资产，但转写、切段和 AI 结构拆解仍处于显式阻断状态。
              </p>

              <p v-if="video.errorMessage" class="video-card__error">
                {{ video.errorMessage }}
              </p>
            </article>
          </div>
        </div>

        <aside class="workspace-grid__rail">
          <section class="info-panel">
            <div class="section-head">
              <div>
                <p class="section-head__kicker">当前聚焦</p>
                <h2>{{ selectedVideo?.fileName ?? "暂无选中视频" }}</h2>
              </div>
              <span class="section-chip">{{ selectedVideo ? videoStateLabel(selectedVideo) : "empty" }}</span>
            </div>

            <template v-if="selectedVideo">
              <dl class="detail-list">
                <div>
                  <dt>项目路径</dt>
                  <dd>{{ selectedVideo.filePath }}</dd>
                </div>
                <div>
                  <dt>文件识别</dt>
                  <dd>{{ selectedVideo.codec ?? "等待识别" }}</dd>
                </div>
                <div>
                  <dt>导入时间</dt>
                  <dd>{{ formatDateTime(selectedVideo.createdAt) }}</dd>
                </div>
                <div>
                  <dt>任务状态</dt>
                  <dd>{{ taskLabel(selectedVideo.id) }}</dd>
                </div>
              </dl>

              <div class="blocked-note">
                <strong>{{ selectedVideoBlockedTitle }}</strong>
                <p>{{ selectedVideoBlockedCopy }}</p>
              </div>
            </template>

            <div v-else class="state-surface state-surface--empty state-surface--compact">
              <strong>还没有可查看的视频记录。</strong>
              <p>导入后会自动把最新记录放到这里，便于继续看任务反馈和阻断说明。</p>
            </div>
          </section>

          <section class="info-panel">
            <div class="section-head">
              <div>
                <p class="section-head__kicker">拆解链路</p>
                <h2>从导入到阻断的真实步骤</h2>
              </div>
            </div>

            <ol class="roadmap">
              <li>
                <strong>导入本地视频</strong>
                <span>真实文件路径写入 Runtime，不生成假素材。</span>
              </li>
              <li>
                <strong>读取元信息</strong>
                <span>分辨率、帧率、时长和体积都来自已返回的导入记录。</span>
              </li>
              <li>
                <strong>队列反馈</strong>
                <span>任务进度仅展示 TaskBus 回传内容，不手工补进度。</span>
              </li>
              <li>
                <strong>后续拆解</strong>
                <span>转写、切段和结构拆解未接通时，保持显式阻断说明。</span>
              </li>
            </ol>
          </section>
        </aside>
      </section>
    </section>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { useProjectStore } from "@/stores/project";
import { useVideoImportStore } from "@/stores/video-import";
import type { TaskInfo } from "@/types/task-events";
import type { ImportedVideo } from "@/types/video";

const projectStore = useProjectStore();
const videoImportStore = useVideoImportStore();
const selectedVideoId = ref<string | null>(null);

const currentProjectId = computed(() => projectStore.currentProject?.projectId ?? "");
const currentProjectName = computed(
  () => projectStore.currentProject?.projectName ?? "当前项目未就绪"
);

const importDisabled = computed(
  () => !currentProjectId.value || videoImportStore.status === "importing"
);

const importButtonLabel = computed(() => {
  if (!currentProjectId.value) return "导入入口已阻断";
  if (videoImportStore.status === "importing") return "导入中";
  return "导入本地视频";
});

const pageStateLabel = computed(() => {
  if (!currentProjectId.value) return "blocked";
  if (videoImportStore.status === "loading") return "loading";
  if (videoImportStore.status === "error") return "error";
  if (videoImportStore.status === "importing") return "ready";
  return "ready";
});

const pageStateTone = computed(() => {
  if (!currentProjectId.value) return "blocked";
  return videoImportStore.status;
});

const stateBannerTone = computed(() => {
  if (!currentProjectId.value) return "blocked";
  if (videoImportStore.status === "loading") return "loading";
  if (videoImportStore.status === "error") return "error";
  return "ready";
});

const stateBannerTitle = computed(() => {
  if (!currentProjectId.value) return "当前项目尚未就绪，导入入口被阻断。";
  if (videoImportStore.status === "loading") return "正在读取视频导入记录。";
  if (videoImportStore.status === "error") return "视频导入链路出现错误。";
  return "视频导入与任务反馈已接通。";
});

const stateBannerCopy = computed(() => {
  if (!currentProjectId.value) {
    return "先选择一个真实项目，再把本地视频写入 Runtime。没有项目上下文时，不创建假视频和假拆解结果。";
  }

  if (videoImportStore.status === "loading") {
    return "导入列表正在从 Runtime 拉取，当前只显示加载中的状态。";
  }

  if (videoImportStore.status === "error") {
    return videoErrorSummary.value || "导入列表读取失败，请稍后重试。";
  }

  return "导入记录、TaskBus 反馈和元信息都来自真实返回值；未接通的拆解能力保持显式阻断。";
});

const importLinkLabel = computed(() => {
  if (!currentProjectId.value) return "未绑定项目";
  if (videoImportStore.status === "importing") return "导入执行中";
  if (videoImportStore.status === "error") return "导入失败";
  if (videoImportStore.status === "loading") return "读取中";
  return "已接通";
});

const taskFeedbackLabel = computed(() => {
  const task = selectedTask.value;
  if (!selectedVideo.value) return "暂无聚焦项";
  if (!task && selectedVideo.value.status === "imported") return "仅有导入记录";
  if (!task) return "暂无任务";
  return `${task.status} · ${task.progress}%`;
});

const blockedLabel = computed(() => {
  if (!currentProjectId.value) return "项目上下文缺失";
  if (selectedVideo.value?.status === "imported" && !selectedTask.value) {
    return "后续拆解未接通";
  }
  if (selectedTask.value?.status === "running") return "任务进行中";
  if (selectedTask.value?.status === "failed") return "任务失败";
  return "显式说明";
});

const listTitle = computed(() => {
  if (videoImportStore.status === "loading") return "导入队列";
  if (videoImportStore.status === "error") return "导入队列不可用";
  if (videoImportStore.videos.length === 0) return "等待导入";
  return "导入队列";
});

const videoErrorSummary = computed(() => {
  if (!videoImportStore.error) return "";
  return videoImportStore.error.requestId
    ? `${videoImportStore.error.message}（请求号：${videoImportStore.error.requestId}）`
    : videoImportStore.error.message;
});

const selectedVideo = computed(
  () => videoImportStore.videos.find((video) => video.id === selectedVideoId.value) ?? null
);

const selectedTask = computed(() =>
  selectedVideo.value ? taskForVideo(selectedVideo.value.id) : undefined
);

const selectedVideoBlockedTitle = computed(() => {
  if (!selectedVideo.value) return "没有可查看的阻断说明。";
  if (selectedTask.value?.status === "running") return "任务正在推进，但拆解链路仍未完全接通。";
  if (selectedTask.value?.status === "failed") return "任务失败，后续步骤保持阻断。";
  if (selectedVideo.value.status === "ready") return "元信息读取完成，后续拆解仍需真实链路接入。";
  return "导入已完成，但转写、切段和 AI 结构拆解仍处于阻断状态。";
});

const selectedVideoBlockedCopy = computed(() => {
  if (!selectedVideo.value) return "选择左侧某条记录后，这里会给出链路说明。";
  if (selectedTask.value?.status === "running") {
    return selectedTask.value.message || "TaskBus 正在回传导入进度，先不要把未完成内容当作拆解结果。";
  }
  if (selectedTask.value?.status === "failed") {
    return selectedTask.value.message || "真实任务失败已记录在队列中，可以稍后重试。";
  }
  if (selectedVideo.value.status === "ready") {
    return "当前只有文件元信息可用，转写、切段和结构拆解的真实结果尚未接通。";
  }
  return "导入记录存在，但仍不能把未落地能力包装成 AI 完成结果。";
});

watch(
  () => videoImportStore.videos.map((video) => video.id).join("|"),
  () => {
    if (!videoImportStore.videos.length) {
      selectedVideoId.value = null;
      return;
    }

    if (!selectedVideoId.value || !videoImportStore.videos.some((video) => video.id === selectedVideoId.value)) {
      selectedVideoId.value = videoImportStore.videos[0]?.id ?? null;
    }
  },
  { immediate: true }
);

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
  if (!currentProjectId.value || videoImportStore.status === "importing") {
    return;
  }

  const filePath = await pickVideoFilePath();
  if (!filePath) {
    return;
  }

  const video = await videoImportStore.importVideoFile(currentProjectId.value, filePath);
  if (video) {
    selectedVideoId.value = video.id;
  }
}

async function refreshVideos(): Promise<void> {
  if (!currentProjectId.value) {
    return;
  }

  await videoImportStore.loadVideos(currentProjectId.value);
}

async function pickVideoFilePath(): Promise<string> {
  try {
    const dialog = await import("@tauri-apps/plugin-dialog");
    const selected = await dialog.open({
      filters: [
        {
          extensions: ["mp4", "mov", "mkv", "webm"],
          name: "Video"
        }
      ],
      multiple: false
    });

    return typeof selected === "string" ? selected.trim() : "";
  } catch {
    return window.prompt("请输入本地视频文件路径")?.trim() ?? "";
  }
}

function selectVideo(videoId: string): void {
  selectedVideoId.value = videoId;
}

function taskForVideo(videoId: string): TaskInfo | undefined {
  return videoImportStore.taskForVideo(videoId);
}

function taskLabel(videoId: string): string {
  const task = taskForVideo(videoId);
  if (!task) {
    return "仅有导入记录";
  }

  if (task.status === "running") return "任务进行中";
  if (task.status === "succeeded") return "任务完成";
  if (task.status === "failed") return "任务失败";
  if (task.status === "cancelled") return "任务已取消";
  return "排队中";
}

function taskMessage(videoId: string): string {
  const task = taskForVideo(videoId);
  if (!task) {
    return "导入记录已写入，但后续拆解链路仍未落地。";
  }

  return task.message || "TaskBus 已返回状态，但没有额外说明。";
}

function taskProgressStyle(videoId: string): Record<string, string> {
  const progress = Math.min(100, Math.max(0, taskForVideo(videoId)?.progress ?? 0));
  return { width: `${progress}%` };
}

function videoStateLabel(video: ImportedVideo): string {
  const task = taskForVideo(video.id);
  if (task) {
    return task.status === "running" ? "解析中" : task.status === "failed" ? "失败" : "任务反馈";
  }
  return video.status === "ready" ? "已就绪" : "已导入";
}

function videoTone(video: ImportedVideo): string {
  const task = taskForVideo(video.id);
  if (task?.status === "running") return "loading";
  if (task?.status === "failed" || video.errorMessage) return "error";
  if (video.status === "ready") return "ready";
  return "blocked";
}

function formatDuration(value: number | null): string {
  return value === null ? "时长待识别" : `${value.toFixed(1)} 秒`;
}

function formatResolution(width: number | null, height: number | null): string {
  return width && height ? `${width} × ${height}` : "分辨率待识别";
}

function formatFrameRate(value: number | null): string {
  return value === null ? "帧率待识别" : `${value} fps`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    hour12: false,
    timeStyle: "short"
  }).format(date);
}
</script>

<style scoped>
.video-page {
  display: grid;
  gap: 16px;
  min-height: 100%;
  padding: 28px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 9%, transparent), transparent 36%),
    var(--bg-base);
  color: var(--text-primary);
}

.hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 24px 24px 20px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
}

.hero__copy {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.hero__kicker,
.section-head__kicker {
  color: var(--brand-primary);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0;
}

h1,
h2,
h3,
p,
dl,
dt,
dd,
ol,
li {
  margin: 0;
}

h1 {
  font-size: 32px;
  line-height: 1.15;
}

.hero__copy p,
.state-surface p,
.blocked-note p,
.roadmap span,
.video-card__path,
.video-card__hint,
.video-card__error,
.detail-list dd {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.hero__meta,
.state-banner__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill,
.section-chip,
.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 24px;
  padding: 0 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.pill--brand,
.status-chip[data-state="ready"] {
  border-color: color-mix(in srgb, var(--brand-primary) 36%, transparent);
  background: color-mix(in srgb, var(--brand-primary) 10%, var(--bg-card));
  color: var(--brand-primary);
}

.status-chip[data-state="loading"] {
  border-color: color-mix(in srgb, var(--info) 28%, transparent);
  background: color-mix(in srgb, var(--info) 12%, var(--bg-card));
  color: var(--info);
}

.status-chip[data-state="error"] {
  border-color: color-mix(in srgb, var(--danger) 34%, transparent);
  background: color-mix(in srgb, var(--danger) 10%, var(--bg-card));
  color: var(--danger);
}

.status-chip[data-state="blocked"] {
  border-color: color-mix(in srgb, var(--warning) 30%, transparent);
  background: color-mix(in srgb, var(--warning) 12%, var(--bg-card));
  color: var(--warning);
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.action-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    background-color 160ms ease,
    opacity 160ms ease;
}

.action-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.action-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.action-button--primary {
  background: var(--brand-primary);
  color: #041414;
}

.action-button--secondary {
  border-color: var(--border-default);
  background: var(--bg-card);
  color: var(--text-primary);
}

.state-banner {
  display: grid;
  gap: 12px;
  padding: 16px 18px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
}

.state-banner[data-state="blocked"] {
  border-color: color-mix(in srgb, var(--warning) 32%, transparent);
}

.state-banner[data-state="error"] {
  border-color: color-mix(in srgb, var(--danger) 32%, transparent);
}

.state-banner[data-state="loading"] {
  border-color: color-mix(in srgb, var(--info) 26%, transparent);
}

.state-banner__body {
  display: grid;
  gap: 4px;
}

.state-banner__body strong {
  font-size: 16px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.9fr);
  gap: 16px;
  min-height: 0;
}

.workspace-grid__main,
.workspace-grid__rail {
  display: grid;
  gap: 16px;
  min-width: 0;
  min-height: 0;
}

.workspace-grid__rail {
  align-content: start;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.section-head h2 {
  margin-top: 4px;
  font-size: 18px;
}

.state-surface,
.info-panel,
.video-card {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
}

.state-surface {
  display: grid;
  gap: 8px;
  padding: 20px;
}

.state-surface--loading {
  border-color: color-mix(in srgb, var(--info) 24%, transparent);
}

.state-surface--error {
  border-color: color-mix(in srgb, var(--danger) 30%, transparent);
}

.state-surface--empty {
  border-color: color-mix(in srgb, var(--warning) 24%, transparent);
}

.state-surface--compact {
  padding: 16px;
}

.video-grid {
  display: grid;
  gap: 12px;
}

.video-card {
  display: grid;
  gap: 14px;
  padding: 16px;
  cursor: pointer;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.video-card:hover,
.video-card--selected {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--brand-primary) 40%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--brand-primary) 20%, transparent);
}

.video-card:focus-visible {
  outline: 2px solid var(--brand-primary);
  outline-offset: 2px;
}

.video-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.video-card__title-block {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.video-card__eyebrow {
  color: var(--text-tertiary);
  font-size: 12px;
}

.video-card h3 {
  font-size: 17px;
  line-height: 1.3;
  word-break: break-word;
}

.video-card__path {
  word-break: break-all;
}

.video-card__meta,
.detail-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.video-card__meta div,
.detail-list div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.video-card__meta dt,
.detail-list dt {
  color: var(--text-tertiary);
  font-size: 12px;
}

.video-card__meta dd,
.detail-list dd {
  word-break: break-word;
}

.task-panel {
  display: grid;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--brand-primary) 7%, var(--bg-card));
}

.task-panel__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
}

.task-panel__row strong {
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.task-panel__bar {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--bg-base);
}

.task-panel__bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--brand-primary);
}

.task-panel p {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.video-card__hint,
.video-card__error {
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--bg-card);
}

.video-card__hint {
  border: 1px solid color-mix(in srgb, var(--warning) 24%, transparent);
}

.video-card__error {
  border: 1px solid color-mix(in srgb, var(--danger) 24%, transparent);
}

.info-panel {
  display: grid;
  gap: 14px;
  padding: 16px;
}

.blocked-note {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--warning) 28%, transparent);
  background: color-mix(in srgb, var(--warning) 8%, var(--bg-card));
}

.blocked-note strong {
  font-size: 14px;
}

.roadmap {
  display: grid;
  gap: 10px;
  padding-left: 18px;
}

.roadmap li {
  display: grid;
  gap: 4px;
}

.roadmap strong {
  font-size: 14px;
}

@media (max-width: 1120px) {
  .video-page {
    padding: 20px;
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hero {
    flex-direction: column;
  }

  h1 {
    font-size: 28px;
  }

  .video-card__meta,
  .detail-list {
    grid-template-columns: 1fr;
  }
}
</style>
