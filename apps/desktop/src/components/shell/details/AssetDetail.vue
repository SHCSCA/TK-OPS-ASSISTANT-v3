<template>
  <div class="asset-detail">
    <template v-if="selectedAsset">
      <header class="asset-detail__header">
        <div>
          <p>资产详情</p>
          <h2>{{ selectedAsset.name }}</h2>
        </div>
        <button type="button" title="关闭资产详情" @click="closeDetail">
          <span class="material-symbols-outlined">close</span>
        </button>
      </header>

      <section class="detail-section">
        <p class="detail-section__title">资产预览</p>
        <AssetPreview :asset="selectedAsset" variant="detail" />
      </section>

      <section class="detail-section">
        <p class="detail-section__title">属性与元数据</p>
        <dl class="metadata-list">
          <div>
            <dt>类型</dt>
            <dd>{{ typeLabel(selectedAsset.type) }}</dd>
          </div>
          <div>
            <dt>来源</dt>
            <dd>{{ selectedAsset.source }}</dd>
          </div>
          <div>
            <dt>大小</dt>
            <dd>{{ formatSize(selectedAsset.fileSizeBytes) }}</dd>
          </div>
          <div>
            <dt>路径</dt>
            <dd :title="selectedAsset.filePath || '未记录路径'">
              {{ selectedAsset.filePath || "未记录路径" }}
            </dd>
          </div>
          <div>
            <dt>创建时间</dt>
            <dd>{{ formatShanghaiDateTime(selectedAsset.createdAt) }}</dd>
          </div>
          <div>
            <dt>更新时间</dt>
            <dd>{{ formatShanghaiDateTime(selectedAsset.updatedAt) }}</dd>
          </div>
        </dl>
      </section>

      <section v-if="assetTags.length" class="detail-section">
        <p class="detail-section__title">真实标签</p>
        <div class="tag-list">
          <span v-for="tag in assetTags" :key="tag">{{ tag }}</span>
        </div>
      </section>

      <section class="detail-section">
        <div class="reference-title">
          <p class="detail-section__title">引用影响范围</p>
          <strong>{{ store.references.length }}</strong>
        </div>

        <p v-if="store.references.length === 0" class="empty-hint">
          当前资产暂未被项目链路引用，可以安全整理或删除。
        </p>

        <ul v-else class="reference-list">
          <li v-for="reference in store.references" :key="reference.id">
            <span class="material-symbols-outlined">link</span>
            <div>
              <strong>{{ reference.referenceType }}</strong>
              <span>{{ reference.referenceId }}</span>
            </div>
          </li>
        </ul>
      </section>

      <p v-if="store.deleteError" class="asset-detail__error">{{ store.deleteError }}</p>

      <button
        class="asset-detail__delete"
        data-testid="asset-delete-button"
        type="button"
        @click="handleDeleteSelected"
      >
        检查引用并删除
      </button>
    </template>

    <template v-else>
      <section class="detail-section">
        <p class="detail-section__title">资产预览</p>
        <div class="asset-preview-well">
          <span class="material-symbols-outlined">image</span>
          <p>未选中资产</p>
        </div>
      </section>

      <section class="detail-section">
        <p class="detail-section__title">属性与元数据</p>
        <div class="metadata-list">
          <p class="empty-hint">在资产中心选择一个资产，右侧抽屉会展示文件路径、项目引用和可复用标签。</p>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import AssetPreview from "@/components/assets/AssetPreview.vue";
import { useAssetLibraryStore } from "@/stores/asset-library";
import { useShellUiStore } from "@/stores/shell-ui";

const store = useAssetLibraryStore();
const shellUiStore = useShellUiStore();

const selectedAsset = computed(() => store.assets.find((asset) => asset.id === store.selectedId) ?? null);
const assetTags = computed(() => (selectedAsset.value ? store.parseTags(selectedAsset.value) : []));

function closeDetail() {
  void store.select(null);
  shellUiStore.closeDetailPanel();
}

async function handleDeleteSelected() {
  if (!store.selectedId) return;
  const canDelete = await store.prepareDelete(store.selectedId);
  if (canDelete) await store.deleteSelected();
}

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

function formatShanghaiDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    hourCycle: "h23"
  }).formatToParts(date);
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")} ${part("hour")}:${part("minute")}:${part("second")}`;
}
</script>

<style scoped>
.asset-detail {
  display: grid;
  gap: 16px;
}

.asset-detail__header {
  align-items: flex-start;
  display: flex;
  gap: 14px;
  justify-content: space-between;
}

.asset-detail__header p {
  color: var(--brand-primary);
  font-size: 12px;
  font-weight: 800;
  margin: 0 0 6px;
}

.asset-detail__header h2 {
  font-size: 18px;
  line-height: 1.35;
  margin: 0;
  overflow-wrap: anywhere;
}

.asset-detail__header button {
  align-items: center;
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  height: 32px;
  justify-content: center;
  padding: 0;
  width: 32px;
}

.detail-section {
  border-bottom: 1px solid var(--border-default);
  padding: 0 0 16px;
}

.detail-section__title {
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0 0 12px;
}

.asset-preview-well {
  align-items: center;
  aspect-ratio: 16 / 9;
  background: var(--surface-sunken);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
}

.asset-preview-well .material-symbols-outlined {
  color: var(--brand-primary);
  font-size: 48px;
  margin-bottom: 8px;
}

.metadata-list {
  display: grid;
  gap: 10px;
  margin: 0;
}

.metadata-list div {
  display: grid;
  gap: 4px;
}

.metadata-list dt {
  color: var(--text-secondary);
  font-size: 12px;
}

.metadata-list dd {
  font-size: 13px;
  margin: 0;
  overflow-wrap: anywhere;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-list span {
  background: color-mix(in srgb, var(--brand-primary) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--brand-primary) 22%, transparent);
  border-radius: 999px;
  color: var(--text-primary);
  font-size: 11px;
  padding: 2px 8px;
}

.reference-title {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.reference-title strong {
  background: color-mix(in srgb, var(--brand-primary) 14%, transparent);
  border-radius: 999px;
  color: var(--brand-primary);
  padding: 2px 8px;
}

.reference-list {
  display: grid;
  gap: 8px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.reference-list li {
  align-items: center;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  display: flex;
  gap: 10px;
  padding: 10px;
}

.reference-list .material-symbols-outlined {
  color: var(--brand-primary);
  font-size: 18px;
}

.reference-list div {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.reference-list strong,
.reference-list span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reference-list span {
  color: var(--text-secondary);
  font-size: 12px;
}

.empty-hint {
  color: var(--text-tertiary);
  font-size: 13px;
  line-height: 1.7;
  margin: 0;
  padding: 8px 0;
  text-align: left;
}

.asset-detail__error {
  background: color-mix(in srgb, var(--status-error) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--status-error) 35%, transparent);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
  padding: 10px;
}

.asset-detail__delete {
  background: transparent;
  border: 1px solid color-mix(in srgb, var(--status-error) 40%, var(--border-default));
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  cursor: pointer;
  font: inherit;
  font-weight: 800;
  height: 36px;
}
</style>
