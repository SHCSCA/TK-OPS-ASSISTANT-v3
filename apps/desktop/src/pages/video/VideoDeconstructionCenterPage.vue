<template>
  <section class="video-page workspace-page" data-video-page="deconstruction">
    <header class="video-page__hero">
      <div>
        <p class="dashboard-hero__eyebrow">视频拆解中心</p>
        <h1>导入现有视频，建立可拆解的素材基线。</h1>
        <p>
          当前版本先完成本地视频导入、FFprobe 元信息提取和项目内列表展示。
          转写、切段与 AI 结构拆解会在后续版本接入。
        </p>
      </div>
      <button
        class="settings-page__button"
        type="button"
        data-action="import-video"
        :disabled="!currentProjectId || videoImportStore.status === 'importing'"
        @click="handleImportVideo"
      >
        {{ videoImportStore.status === "importing" ? "导入中" : "导入本地视频" }}
      </button>
    </header>

    <p v-if="!currentProjectId" class="settings-page__error">请先在创作总览创建或打开项目。</p>
    <p v-if="videoImportStore.error" class="settings-page__error">{{ videoErrorSummary }}</p>

    <section class="video-page__content">
      <div class="video-page__list">
        <div class="command-panel__title-row">
          <div>
            <p class="detail-panel__label">已导入视频</p>
            <h2>{{ videoImportStore.videos.length ? "项目素材列表" : "等待导入" }}</h2>
          </div>
          <span class="page-chip page-chip--muted">{{ videoImportStore.videos.length }} 个视频</span>
        </div>

        <div v-if="videoImportStore.status === 'loading'" class="empty-state">
          正在加载项目视频列表...
        </div>
        <div v-else-if="videoImportStore.videos.length === 0" class="empty-state empty-state--guide">
          <strong>还没有导入视频。</strong>
          <p>点击“导入本地视频”，先把现有素材纳入当前项目，再继续做转写和结构拆解。</p>
        </div>
        <div v-else class="video-card-grid">
          <article v-for="video in videoImportStore.videos" :key="video.id" class="video-card">
            <div class="video-card__preview">
              <span v-if="video.status === 'ready'">▶ 预览</span>
              <span v-else>解析中...</span>
            </div>
            <div class="video-card__body">
              <div class="command-panel__title-row">
                <div>
                  <p class="detail-panel__label">{{ video.codec ?? "codec 待识别" }}</p>
                  <h3>{{ video.fileName }}</h3>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span :class="['status-dot', video.status === 'ready' ? 'status-dot--ready' : 'status-dot--loading']"></span>
                  <span class="page-chip" :class="video.status === 'ready' ? 'status-pill--online' : 'status-pill--loading'">
                    {{ video.status === "ready" ? "元信息就绪" : "已导入" }}
                  </span>
                </div>
              </div>
              <div class="video-card__metrics">
                <span>{{ formatDuration(video.durationSeconds) }}</span>
                <span :style="getResolutionStyle(video.width)">{{ formatResolution(video.width, video.height) }}</span>
                <span>{{ formatFrameRate(video.frameRate) }}</span>
                <span>{{ formatFileSize(video.fileSizeBytes) }}</span>
              </div>
              <p v-if="video.errorMessage" class="video-card__hint">
                <span class="status-dot status-dot--error"></span>
                {{ video.errorMessage }}
              </p>
              <button class="dashboard-list__action" type="button" @click="videoImportStore.removeVideo(video.id)">
                删除记录
              </button>
            </div>
          </article>
        </div>
      </div>

      <aside class="video-page__aside command-panel">
        <p class="detail-panel__label">本轮边界</p>
        <h2>只做导入与元信息</h2>
        <p>FFprobe 可用时展示时长、分辨率、帧率和编码；不可用时仍保存路径与文件大小，不阻断导入。</p>
        <div class="dashboard-metric">
          <span>当前项目</span>
          <strong>{{ projectStore.currentProject?.projectName ?? "未选择" }}</strong>
        </div>
        <div class="dashboard-metric">
          <span>后续回流</span>
          <strong>转写 / 切段 / 重制</strong>
        </div>
      </aside>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";

import { useProjectStore } from "@/stores/project";
import { useVideoImportStore } from "@/stores/video-import";

const projectStore = useProjectStore();
const videoImportStore = useVideoImportStore();

const currentProjectId = computed(() => projectStore.currentProject?.projectId ?? "");
const videoErrorSummary = computed(() => {
  if (!videoImportStore.error) {
    return "";
  }

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
  if (!currentProjectId.value) {
    return;
  }

  const filePath = await pickVideoFilePath();
  if (!filePath) {
    return;
  }

  await videoImportStore.importVideoFile(currentProjectId.value, filePath);
}

async function pickVideoFilePath(): Promise<string> {
  try {
    const dialogModuleName = "@tauri-apps/plugin-dialog";
    const dialog = await import(/* @vite-ignore */ dialogModuleName);
    const selected = await dialog.open({
      multiple: false,
      filters: [
        {
          name: "Video",
          extensions: ["mp4", "mov", "mkv", "webm"]
        }
      ]
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
  return width && height ? `${width} × ${height}` : "分辨率待识别";
}

function getResolutionStyle(width: number | null): any {
  if (!width) return {};
  if (width >= 3840) return { color: 'var(--brand-primary)', borderColor: 'var(--brand-primary)' }; // 4K
  if (width >= 1920) return { color: 'var(--status-success)' }; // 1080p
  return {};
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
</script>
