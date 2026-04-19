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
      :src="previewUrl.startsWith('http') || previewUrl.startsWith('asset') ? previewUrl + '#t=0.001' : previewUrl"
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

const previewKind = computed(() => {
  if (props.asset.type === "image") return "image";
  
  if (props.asset.thumbnailPath) {
    const thumbLower = props.asset.thumbnailPath.toLowerCase();
    const isVideoExt = /\.(mp4|mov|mkv|webm|avi|flv|wmv)$/.test(thumbLower);
    if (!isVideoExt) return "image";
  }
  
  if (props.asset.type === "video") return "video";
  if (props.asset.type === "document") return "document";
  return "fallback";
});

const previewUrl = ref("");

async function resolvePreviewUrl(path: string) {
  if (!path || path === "null" || path === "undefined") return "";
  if (/^(asset|blob|data|https?):/i.test(path)) return path;
  
  try {
    const { convertFileSrc } = await import(/* @vite-ignore */ "@tauri-apps/api/core");
    const url = convertFileSrc(path);
    return url;
  } catch {
    return "";
  }
}

watch(() => props.asset.id, async () => {
  const path = previewKind.value === "image" && props.asset.thumbnailPath ? props.asset.thumbnailPath : props.asset.filePath;
  previewUrl.value = await resolvePreviewUrl(path || "");
}, { immediate: true });

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
    case "video": return "视频";
    case "image": return "图片";
    case "document": return "文档";
    default: return "文件";
  }
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
    case "audio": return "音频资产";
    default: return "文件资产";
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
    // ignore
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
  textPreviewStatus.value = "loading";

  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Error: ${response.status}`);
    const content = await response.text();
    if (requestId !== textPreviewRequestId) return;
    textPreview.value = content.length > UTF8_TEXT_PREVIEW_LIMIT ? content.slice(0, UTF8_TEXT_PREVIEW_LIMIT) + "\n..." : content;
    textPreviewStatus.value = "ready";
  } catch {
    if (requestId !== textPreviewRequestId) return;
    textPreviewStatus.value = "error";
    textPreviewError.value = "无法读取文档";
  }
}

function resetTextPreview() {
  textPreviewRequestId += 1;
  textPreview.value = "";
  textPreviewStatus.value = "idle";
}
</script>

<style scoped>
.asset-preview {
  align-items: center;
  aspect-ratio: 16 / 10;
  background:
    linear-gradient(
      135deg,
      color-mix(in srgb, var(--color-bg-muted) 84%, transparent),
      var(--color-bg-surface)
    );
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
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
  background: var(--color-bg-surface);
  pointer-events: none;
}

.asset-preview__text,
.asset-preview__document,
.asset-preview__fallback {
  background: var(--color-bg-canvas);
  height: 100%;
  width: 100%;
}

.asset-preview__text {
  color: var(--color-text-primary);
  display: flex;
  overflow: hidden;
  padding: 12px;
}

.asset-preview__text span {
  align-self: center;
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 1.6;
  text-align: center;
  width: 100%;
}

.asset-preview__text pre {
  font: 12px/1.55 var(--font-family-mono);
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
  background: var(--color-bg-active);
  border: 1px solid var(--color-brand-primary);
  border-radius: var(--radius-sm);
  color: var(--color-brand-primary);
  font-size: 11px;
  font-weight: 800;
  justify-self: start;
  padding: 2px 8px;
}

.asset-preview__document strong,
.asset-preview__fallback strong {
  align-self: end;
  color: var(--color-text-primary);
  font-size: 13px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.asset-preview__document em {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-style: normal;
}

.asset-preview__document small,
.asset-preview__fallback small {
  color: var(--color-text-tertiary);
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
  background: var(--color-bg-overlay);
  backdrop-filter: blur(8px);
  color: var(--color-text-on-brand);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0;
}
</style>
