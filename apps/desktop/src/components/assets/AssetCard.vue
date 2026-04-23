<template>
  <button
    class="asset-card"
    :class="{ 
      'asset-card--selected': isSelected,
      'asset-card--invalid': isInvalid,
      'asset-card--generating': isGenerating
    }"
    :data-testid="`asset-card-${asset.id}`"
    type="button"
    :disabled="isInvalid || isGenerating"
    @click="$emit('select', asset.id)"
    :draggable="!isInvalid && !isGenerating"
  >
    <div v-if="isInvalid" class="asset-card__overlay">
      <span class="material-symbols-outlined">broken_image</span>
      <span>资产文件已失效</span>
    </div>
    <div v-else-if="isGenerating" class="asset-card__overlay">
      <span class="material-symbols-outlined asset-spin">sync</span>
      <span>生成中</span>
    </div>

    <span v-if="isSelected" class="asset-card__selected-dot" aria-hidden="true" />

    <AssetPreview :asset="asset" />

    <header class="asset-card__header">
      <div class="asset-card__badges">
        <span class="asset-card__type">{{ typeLabel(asset.type) }}</span>
        <span v-if="asset.source" class="asset-card__source-badge">{{ asset.source === 'local' ? '本地' : asset.source }}</span>
      </div>
      <strong class="asset-card__name" :title="asset.name">{{ asset.name }}</strong>
      <span class="asset-card__path" :title="asset.filePath || '未记录路径'">
        {{ asset.filePath || "未记录路径" }}
      </span>
    </header>

    <div class="asset-card__meta">
      <span>{{ formatSize(asset.fileSizeBytes) }}</span>
      <span>{{ durationLabel(asset.durationMs) }}</span>
    </div>

    <div class="asset-card__footer">
      <span class="asset-card__project">
        {{ asset.projectId || "未归入项目" }}
      </span>
      <span v-if="tags.length" class="asset-card__tags">
        <span v-for="tag in tags" :key="tag">{{ tag }}</span>
      </span>
    </div>
  </button>
</template>

<script setup lang="ts">
import { computed } from "vue";
import AssetPreview from "@/components/assets/AssetPreview.vue";
import type { AssetDto } from "@/types/runtime";

const props = defineProps<{
  asset: AssetDto;
  isSelected: boolean;
  tags: string[];
}>();

defineEmits<{
  select: [assetId: string];
}>();

const isGenerating = computed(() => props.asset.source !== 'local' && !props.asset.fileSizeBytes && !props.asset.filePath);
const isInvalid = computed(() => !isGenerating.value && !props.asset.filePath);

function typeLabel(type: string) {
  switch (type) {
    case "video":
      return "视频";
    case "image":
      return "图片";
    case "audio":
      return "音频";
    case "document":
      return "文档";
    default:
      return type || "未知";
  }
}

function formatSize(bytes: number | null) {
  if (bytes === null) return "未记录";
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function durationLabel(durationMs: number | null) {
  if (durationMs === null) return "未记录时长";
  const totalSeconds = Math.max(0, Math.round(durationMs / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}
</script>

<style scoped>
.asset-card {
  background: color-mix(in srgb, var(--color-bg-surface, var(--surface-secondary)) 88%, transparent);
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  color: var(--color-text-primary, var(--text-primary));
  display: grid;
  gap: 10px;
  min-height: 258px;
  overflow: hidden;
  padding: 12px;
  position: relative;
  text-align: left;
  transition:
    background var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-spring),
    transform var(--motion-fast) var(--ease-spring);
}

.asset-card:hover,
.asset-card--selected {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 9%, var(--color-bg-surface, var(--surface-secondary)));
  border-color: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 70%, var(--border-default));
  box-shadow: 0 14px 32px color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 13%, transparent);
  transform: translateY(-2px);
}

.asset-card:active {
  transform: scale(0.98) translateY(0);
  transition-duration: var(--motion-instant);
}

.asset-card--selected::after {
  background: var(--color-brand-primary, var(--brand-primary));
  border-radius: 999px;
  content: "";
  height: 7px;
  position: absolute;
  right: 12px;
  top: 12px;
  width: 7px;
}

.asset-card__selected-dot {
  position: absolute;
  inset: 10px auto auto 10px;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--color-brand-primary, var(--brand-primary));
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 18%, transparent);
  z-index: 1;
}

.asset-card__header,
.asset-card__footer {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.asset-card__type {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
}

.asset-card__name {
  font-size: 15px;
  font-weight: 800;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-card__path,
.asset-card__project {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
}

.asset-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.asset-card__tags span {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 22%, transparent);
  border-radius: 999px;
  color: var(--color-text-primary, var(--text-primary));
  font-size: 11px;
  padding: 2px 8px;
}

.asset-card__footer {
  margin-top: auto;
}

.asset-card__project {
  font-size: 11px;
}

.asset-card--invalid {
  opacity: 0.6;
  border-color: var(--color-danger, #ff4d4f);
  cursor: not-allowed;
}
.asset-card--invalid:hover {
  background: var(--color-bg-surface);
  transform: none;
  box-shadow: none;
}

.asset-card--generating {
  opacity: 0.8;
  cursor: wait;
}
.asset-card--generating:hover {
  transform: none;
  box-shadow: none;
}

.asset-card__overlay {
  position: absolute;
  inset: 0;
  background: color-mix(in srgb, var(--color-bg-surface) 80%, transparent);
  backdrop-filter: blur(2px);
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: bold;
}
.asset-card--invalid .asset-card__overlay {
  color: var(--color-danger, #ff4d4f);
  background: color-mix(in srgb, var(--color-bg-surface) 60%, transparent);
}

.asset-card__badges {
  display: flex;
  align-items: center;
  gap: 8px;
}

.asset-card__source-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--color-bg-muted);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.asset-spin {
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Reduced Motion 降级由 :root[data-reduced-motion="true"] 的 --motion-* 变量统一控制 */
</style>
