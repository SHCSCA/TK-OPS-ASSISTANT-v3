<template>
  <div class="asset-preview" :class="[`asset-preview--${variant}`, `asset-preview--${previewKind}`]">
    <span class="asset-preview__badge">{{ previewBadge }}</span>

    <img
      v-if="previewKind === 'image' && previewUrl"
      :alt="asset.name"
      :data-testid="`asset-preview-image-${asset.id}`"
      :src="previewUrl"
    />

    <video
      v-else-if="previewKind === 'video' && previewUrl"
      :data-testid="`asset-preview-video-${asset.id}`"
      :src="previewUrl"
      muted
      playsinline
      preload="metadata"
      @mouseenter="playPreview"
      @mouseleave="resetPreview"
    />

    <div
      v-else-if="previewKind === 'document' && previewUrl && isUtf8TextDocument"
      class="asset-preview__text"
      :data-testid="`asset-preview-text-${asset.id}`"
    >
      <span v-if="textPreviewStatus === 'loading'">正在读取 UTF-8 文档</span>
      <pre v-else-if="textPreviewStatus === 'ready'">{{ textPreview }}</pre>
      <span v-else>{{ textPreviewError }}</span>
    </div>

    <iframe
      v-else-if="previewKind === 'document' && previewUrl && isEmbeddableDocument"
      :data-testid="`asset-preview-document-${asset.id}`"
      :src="previewUrl"
      :title="`${asset.name} 文档预览`"
    />

    <div
      v-else-if="previewKind === 'document'"
      class="asset-preview__document"
      :data-testid="`asset-preview-document-sheet-${asset.id}`"
    >
      <span>{{ fileExtension }}</span>
      <strong>{{ asset.name }}</strong>
      <em>暂不支持预览</em>
      <small>{{ asset.filePath || "未记录路径" }}</small>
    </div>

    <div v-else class="asset-preview__fallback">
      <span>{{ fallbackLabel }}</span>
      <strong>{{ asset.name }}</strong>
      <small>{{ asset.filePath || "未记录路径" }}</small>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { convertFileSrc, isTauri } from "@tauri-apps/api/core";

import type { AssetDto } from "@/types/runtime";

const UTF8_TEXT_PREVIEW_LIMIT = 2400;

const props = withDefaults(
  defineProps<{
    asset: AssetDto;
    variant?: "card" | "detail";
  }>(),
  {
    variant: "card"
  }
);

const previewSource = computed(() => props.asset.thumbnailPath || props.asset.filePath || "");
const previewUrl = computed(() => toPreviewUrl(previewSource.value));
const textPreview = ref("");
const textPreviewStatus = ref<"idle" | "loading" | "ready" | "error">("idle");
const textPreviewError = ref("无法读取 UTF-8 文档预览");
let textPreviewRequestId = 0;

const fileExtension = computed(() => {
  const name = props.asset.name || props.asset.filePath || "";
  const extension = name.includes(".") ? name.split(".").pop() : "";
  return extension ? extension.toUpperCase() : "DOC";
});

const previewBadge = computed(() => {
  switch (previewKind.value) {
    case "video":
      return "视频";
    case "image":
      return "图片";
    case "document":
      return "文档";
    default:
      return "文件";
  }
});

const previewKind = computed(() => {
  if (props.asset.thumbnailPath) return "image";
  if (props.asset.type === "video") return "video";
  if (props.asset.type === "image") return "image";
  if (props.asset.type === "document") return "document";
  return "fallback";
});

const isEmbeddableDocument = computed(() => {
  const lowerName = (props.asset.filePath || props.asset.name).toLowerCase();
  return /\.pdf$/.test(lowerName);
});

const isUtf8TextDocument = computed(() => {
  const lowerName = (props.asset.filePath || props.asset.name).toLowerCase();
  return /\.(txt|md|json|csv|srt)$/.test(lowerName);
});

const fallbackLabel = computed(() => {
  switch (props.asset.type) {
    case "audio":
      return "音频资产";
    default:
      return "文件资产";
  }
});

watch(
  () => ({
    isTextDocument: isUtf8TextDocument.value,
    kind: previewKind.value,
    url: previewUrl.value
  }),
  ({ isTextDocument, kind, url }) => {
    if (kind !== "document" || !isTextDocument || !url) {
      resetTextPreview();
      return;
    }
    void loadUtf8TextPreview(url);
  },
  { immediate: true }
);

async function playPreview(event: MouseEvent) {
  if (props.variant !== "card") return;
  const video = event.currentTarget as HTMLVideoElement;
  try {
    await video.play();
  } catch {
    // 鼠标悬停预览不应打断主流程，播放失败时保留首帧。
  }
}

function resetPreview(event: MouseEvent) {
  if (props.variant !== "card") return;
  const video = event.currentTarget as HTMLVideoElement;
  video.pause();
  video.currentTime = 0;
}

async function loadUtf8TextPreview(url: string) {
  const requestId = ++textPreviewRequestId;
  textPreview.value = "";
  textPreviewError.value = "无法读取 UTF-8 文档预览";
  textPreviewStatus.value = "loading";

  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`读取失败：${response.status}`);
    const content = await response.text();
    if (requestId !== textPreviewRequestId) return;
    textPreview.value = limitTextPreview(content);
    textPreviewStatus.value = "ready";
  } catch {
    if (requestId !== textPreviewRequestId) return;
    textPreviewStatus.value = "error";
    textPreviewError.value = "无法按 UTF-8 读取该文档";
  }
}

function resetTextPreview() {
  textPreviewRequestId += 1;
  textPreview.value = "";
  textPreviewStatus.value = "idle";
  textPreviewError.value = "无法读取 UTF-8 文档预览";
}

function limitTextPreview(content: string) {
  if (content.length <= UTF8_TEXT_PREVIEW_LIMIT) return content;
  return `${content.slice(0, UTF8_TEXT_PREVIEW_LIMIT)}\n...`;
}

function toPreviewUrl(filePath: string): string {
  if (!filePath) return "";
  if (/^(asset|blob|data|https?):/i.test(filePath)) return filePath;
  try {
    return isTauri() ? convertFileSrc(filePath) : "";
  } catch {
    return "";
  }
}
</script>

<style scoped>
.asset-preview {
  align-items: center;
  aspect-ratio: 16 / 10;
  background:
    linear-gradient(
      135deg,
      color-mix(in srgb, var(--color-bg-muted, var(--surface-sunken)) 84%, transparent),
      var(--color-bg-surface, var(--surface-tertiary))
    );
  border: 1px solid color-mix(in srgb, var(--color-border-default, var(--border-default)) 82%, transparent);
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary, var(--text-tertiary));
  display: flex;
  justify-content: center;
  overflow: hidden;
  position: relative;
}

.asset-preview--detail {
  aspect-ratio: 16 / 9;
}

.asset-preview img,
.asset-preview video,
.asset-preview iframe {
  border: 0;
  height: 100%;
  object-fit: cover;
  width: 100%;
}

.asset-preview iframe {
  background: var(--color-bg-surface, var(--surface-primary));
  pointer-events: none;
}

.asset-preview__text,
.asset-preview__document,
.asset-preview__fallback {
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--color-bg-surface, var(--surface-primary)) 96%, transparent),
      var(--color-bg-surface, var(--surface-secondary))
    );
  height: 100%;
  width: 100%;
}

.asset-preview__text {
  color: var(--color-text-primary, var(--text-primary));
  display: flex;
  overflow: hidden;
  padding: 12px;
}

.asset-preview__text span {
  align-self: center;
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
  line-height: 1.6;
  text-align: center;
  width: 100%;
}

.asset-preview__text pre {
  font: 12px/1.55 ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
  margin: 0;
  overflow: hidden;
  text-align: left;
  white-space: pre-wrap;
  width: 100%;
  word-break: break-word;
}

.asset-preview__document,
.asset-preview__fallback {
  display: grid;
  gap: 6px;
  padding: 14px;
}

.asset-preview__document span,
.asset-preview__fallback span {
  align-self: start;
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 35%, transparent);
  border-radius: var(--radius-sm);
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 11px;
  font-weight: 800;
  justify-self: start;
  padding: 2px 8px;
}

.asset-preview__document strong,
.asset-preview__fallback strong {
  align-self: end;
  color: var(--color-text-primary, var(--text-primary));
  font-size: 13px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.asset-preview__document em {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
  font-style: normal;
}

.asset-preview__document small,
.asset-preview__fallback small {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-preview__badge {
  position: absolute;
  left: 10px;
  top: 10px;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-bg-overlay, rgba(0, 0, 0, 0.42)) 50%, transparent);
  backdrop-filter: blur(8px);
  color: var(--color-text-on-brand, #fff);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0;
}

/* Reduced Motion 降级由 :root[data-reduced-motion="true"] 的 --motion-* 变量统一控制 */
</style>
