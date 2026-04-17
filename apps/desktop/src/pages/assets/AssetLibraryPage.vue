<template>
  <ProjectContextGuard>
    <section
      class="asset-library"
      data-testid="asset-library"
      @dragenter.prevent="handleDragOver"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <div v-if="isDragging" class="asset-library__drop-layer">
        <span class="material-symbols-outlined">upload_file</span>
        <strong>松开导入到资产中心</strong>
        <span>{{ dragFileCountLabel }}，只记录真实本地文件路径，不生成额外占位素材。</span>
      </div>

      <header class="asset-library__hero">
        <div class="asset-library__hero-copy">
          <p class="asset-library__eyebrow">M09 资产中心 · 真实文件工作面</p>
          <h1>资产中心</h1>
          <p>
            管理导入、筛选、选择和引用检查，所有素材都必须来自真实本地文件或 Runtime 返回的记录。
          </p>
        </div>

        <div class="asset-library__hero-actions">
          <button class="asset-library__hero-action" type="button" @click="handleReload" :disabled="isBusy">
            <span class="material-symbols-outlined">refresh</span>
            重新读取
          </button>
          <button class="asset-library__hero-action asset-library__hero-action--brand" type="button" @click="handleUpload" :disabled="isBusy">
            <span class="material-symbols-outlined">add</span>
            {{ store.importStatus === "importing" ? "导入中" : "导入资产" }}
          </button>
        </div>
      </header>

      <section class="asset-library__summary">
        <article class="summary-card">
          <span>资产总数</span>
          <strong>{{ store.assets.length }}</strong>
          <p>来自 Runtime 的真实资产记录</p>
        </article>
        <article class="summary-card">
          <span>当前结果</span>
          <strong>{{ visibleAssets.length }}</strong>
          <p>按筛选和排序后的结果</p>
        </article>
        <article class="summary-card">
          <span>当前选中</span>
          <strong>{{ selectedAsset ? selectedAsset.name : "未选中" }}</strong>
          <p>{{ selectedAsset ? selectedAsset.source : "请选择一个资产继续查看" }}</p>
        </article>
        <article class="summary-card">
          <span>导入状态</span>
          <strong>{{ importStatusLabel }}</strong>
          <p>{{ importStatusHint }}</p>
        </article>
      </section>

      <AssetToolbar
        :filter-type="store.filter.type"
        :is-importing="isBusy"
        :search-query="searchQuery"
        :sort-mode="sortMode"
        @filter-type="handleFilterType"
        @import="handleUpload"
        @search="handleSearch"
        @sort="handleSort"
      />

      <div
        v-if="visibleNotice"
        class="asset-library__notice"
        :class="`asset-library__notice--${visibleNotice.type}`"
        role="status"
      >
        <span class="material-symbols-outlined">{{ visibleNotice.icon }}</span>
        <span>{{ visibleNotice.text }}</span>
      </div>

      <main class="asset-library__body">
        <section class="asset-library__workspace">
          <AssetWall
            :assets="visibleAssets"
            :error="store.error"
            :parse-tags="store.parseTags"
            :selected-id="store.selectedId"
            :status="store.status"
            @import="handleUpload"
            @retry="handleReload"
            @select="selectAsset"
          />
        </section>

        <aside class="asset-library__inspector">
          <section class="inspector-card">
            <p class="inspector-card__eyebrow">选中资产</p>
            <template v-if="selectedAsset">
              <AssetPreview :asset="selectedAsset" variant="detail" />

              <div class="inspector-card__title-block">
                <h2 :title="selectedAsset.name">{{ selectedAsset.name }}</h2>
                <p>{{ typeLabel(selectedAsset.type) }} · {{ selectedAsset.source }}</p>
              </div>

              <dl class="inspector-metadata">
                <div>
                  <dt>路径</dt>
                  <dd :title="selectedAsset.filePath || '未记录路径'">
                    {{ selectedAsset.filePath || "未记录路径" }}
                  </dd>
                </div>
                <div>
                  <dt>大小</dt>
                  <dd>{{ formatSize(selectedAsset.fileSizeBytes) }}</dd>
                </div>
                <div>
                  <dt>时长</dt>
                  <dd>{{ formatDuration(selectedAsset.durationMs) }}</dd>
                </div>
                <div>
                  <dt>项目</dt>
                  <dd>{{ selectedAsset.projectId || "未归入项目" }}</dd>
                </div>
                <div>
                  <dt>创建</dt>
                  <dd>{{ formatShanghaiDateTime(selectedAsset.createdAt) }}</dd>
                </div>
                <div>
                  <dt>更新</dt>
                  <dd>{{ formatShanghaiDateTime(selectedAsset.updatedAt) }}</dd>
                </div>
              </dl>

              <section class="inspector-block">
                <div class="inspector-block__header">
                  <span>标签</span>
                  <strong>{{ selectedTags.length }}</strong>
                </div>
                <div v-if="selectedTags.length" class="inspector-tags">
                  <span v-for="tag in selectedTags" :key="tag">{{ tag }}</span>
                </div>
                <p v-else class="inspector-empty">Runtime 还没有为该资产返回标签。</p>
              </section>

              <section class="inspector-block">
                <div class="inspector-block__header">
                  <span>引用影响</span>
                  <strong>{{ store.references.length }}</strong>
                </div>
                <p v-if="store.references.length === 0" class="inspector-empty">
                  当前资产暂无引用，删除前依然会先经过 Runtime 引用检查。
                </p>
                <ul v-else class="inspector-references">
                  <li v-for="reference in store.references" :key="reference.id">
                    <span class="material-symbols-outlined">link</span>
                    <div>
                      <strong>{{ reference.referenceType }}</strong>
                      <span>{{ reference.referenceId }}</span>
                    </div>
                  </li>
                </ul>
              </section>

              <div class="inspector-actions">
                <button type="button" class="inspector-actions__button" @click="openSelectedAssetDetail">
                  打开详情面板
                </button>
                <button type="button" class="inspector-actions__button inspector-actions__button--ghost" @click="clearSelection">
                  清空选择
                </button>
              </div>
            </template>

            <template v-else>
              <div class="inspector-empty-state">
                <span class="material-symbols-outlined">ads_click</span>
                <strong>未选中资产</strong>
                <p>从左侧素材墙选择一个真实资产，右侧会同步显示文件路径、引用影响和标签。</p>
              </div>
            </template>
          </section>

          <section class="inspector-card inspector-card--soft">
            <p class="inspector-card__eyebrow">导入边界</p>
            <p class="inspector-note">
              导入只接收桌面端真实文件路径，拖拽或选择器失效时会明确提示，不会生成假素材或空壳记录。
            </p>
            <p class="inspector-note inspector-note--subtle">
              当 Runtime 返回错误时，页面会保留中文错误消息和重试入口，不吞掉异常。
            </p>
          </section>
        </aside>
      </main>
    </section>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { open } from "@tauri-apps/plugin-dialog";

import AssetPreview from "@/components/assets/AssetPreview.vue";
import AssetToolbar from "@/components/assets/AssetToolbar.vue";
import AssetWall from "@/components/assets/AssetWall.vue";
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import { useAssetLibraryStore } from "@/stores/asset-library";
import type { AssetDto } from "@/types/runtime";

const store = useAssetLibraryStore();
const shellUiStore = useShellUiStore();
const searchQuery = ref(store.filter.q);
const sortMode = ref<"latest" | "name" | "size">("latest");
const isDragging = ref(false);
const dragFileCount = ref(0);
const importSuccessMessage = ref<string | null>(null);
const importInfoMessage = ref<string | null>(null);
const importProgress = ref<{ completed: number; total: number } | null>(null);

const visibleAssets = computed(() => {
  const assets = [...store.assets];
  switch (sortMode.value) {
    case "name":
      return assets.sort((left, right) => left.name.localeCompare(right.name, "zh-CN"));
    case "size":
      return assets.sort((left, right) => (right.fileSizeBytes ?? -1) - (left.fileSizeBytes ?? -1));
    case "latest":
    default:
      return assets.sort((left, right) => toTime(right.createdAt) - toTime(left.createdAt));
  }
});

const selectedAsset = computed(
  () => store.assets.find((asset) => asset.id === store.selectedId) ?? null
);
const selectedTags = computed(() => (selectedAsset.value ? store.parseTags(selectedAsset.value) : []));
const dragFileCountLabel = computed(() => {
  if (dragFileCount.value <= 0) return "待识别本地文件";
  return `${dragFileCount.value} 个本地文件`;
});
const isBusy = computed(() => store.status === "loading" || store.importStatus === "importing");
const selectedSummary = computed(() => (selectedAsset.value ? `${selectedAsset.value.name} · ${typeLabel(selectedAsset.value.type)}` : "未选中"));
const importStatusLabel = computed(() => {
  switch (store.importStatus) {
    case "importing":
      return "导入中";
    case "succeeded":
      return "最近导入成功";
    case "failed":
      return "导入失败";
    default:
      return "待命";
  }
});
const importStatusHint = computed(() => {
  if (importProgress.value) {
    return `正在导入 ${importProgress.value.completed}/${importProgress.value.total} 个真实本地资产`;
  }
  if (store.importStatus === "failed") {
    return store.importError || "导入失败";
  }
  if (store.importStatus === "succeeded") {
    return importSuccessMessage.value || "已导入真实本地资产";
  }
  if (store.importStatus === "importing") {
    return "正在等待桌面文件选择器和 Runtime 导入响应";
  }
  return "导入只会写入真实本地文件，不会生成占位素材";
});

const visibleNotice = computed(() => {
  const error = store.deleteError || store.importError || store.error;
  if (error) return { icon: "error", text: error, type: "error" };
  if (importProgress.value) {
    return {
      icon: "sync",
      text: `正在导入 ${importProgress.value.completed}/${importProgress.value.total} 个真实本地资产`,
      type: "info"
    };
  }
  if (importSuccessMessage.value) {
    return { icon: "check_circle", text: importSuccessMessage.value, type: "success" };
  }
  if (importInfoMessage.value) {
    return { icon: "info", text: importInfoMessage.value, type: "info" };
  }
  return null;
});

watch(
  selectedAsset,
  (asset) => {
    if (!asset) {
      shellUiStore.clearDetailContext("asset");
      shellUiStore.closeDetailPanel();
      return;
    }

    shellUiStore.openDetailWithContext(buildAssetDetailContext(asset, store.references));
  },
  { immediate: true }
);

onMounted(() => {
  void store.load();
});

onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("asset");
  shellUiStore.closeDetailPanel();
});

function handleReload() {
  void store.load();
}

function handleSearch(query: string) {
  searchQuery.value = query;
  void store.setSearchQuery(query);
}

function handleFilterType(type: string) {
  void store.setFilterType(type);
}

function handleSort(mode: string) {
  if (mode === "latest" || mode === "name" || mode === "size") {
    sortMode.value = mode;
  }
}

function handleDragOver(event: DragEvent) {
  if (!event.dataTransfer) return;
  isDragging.value = true;
  dragFileCount.value = countTransferFiles(event.dataTransfer);
}

function handleDragLeave() {
  isDragging.value = false;
  dragFileCount.value = 0;
}

async function handleUpload() {
  if (isBusy.value) return;
  store.importError = null;
  importSuccessMessage.value = null;
  importInfoMessage.value = null;

  const filePaths = await pickAssetFilePaths();
  if (filePaths.length === 0) return;
  await importFromPaths(filePaths);
}

async function handleDrop(event: DragEvent) {
  isDragging.value = false;
  dragFileCount.value = 0;
  store.importError = null;
  importSuccessMessage.value = null;
  importInfoMessage.value = null;

  const files = Array.from(event.dataTransfer?.files ?? []) as Array<File & { path?: string }>;
  if (files.length === 0) return;

  const filePaths = files.map((file) => file.path).filter((path): path is string => !!path);
  if (filePaths.length === 0) {
    store.importError = "拖拽文件未提供本地路径，请使用桌面文件选择入口。";
    return;
  }

  await importFromPaths(filePaths);
}

async function importFromPaths(filePaths: string[]) {
  const validPaths = filePaths.map((filePath) => filePath.trim()).filter((filePath) => filePath.length > 0);
  const uniquePaths = [...new Set(validPaths)];
  const skippedCount = validPaths.length - uniquePaths.length;

  if (uniquePaths.length === 0) {
    importInfoMessage.value = "没有选择可导入的本地文件。";
    return;
  }

  importProgress.value = { completed: 0, total: uniquePaths.length };
  const importedNames: string[] = [];
  const failedMessages: string[] = [];
  let lastImportedAsset: AssetDto | null = null;

  for (const filePath of uniquePaths) {
    try {
      const imported = await store.importLocalFile({
        filePath,
        type: inferAssetType(filePath),
        source: "local"
      });
      importedNames.push(imported.name);
      lastImportedAsset = imported;
    } catch (error) {
      failedMessages.push(error instanceof Error ? error.message : `${filePath} 导入失败`);
    } finally {
      importProgress.value = {
        completed: (importProgress.value?.completed ?? 0) + 1,
        total: uniquePaths.length
      };
    }
  }

  importProgress.value = null;
  if (lastImportedAsset) {
    store.selectedId = lastImportedAsset.id;
    await store.select(lastImportedAsset.id);
    shellUiStore.openDetailWithContext(buildAssetDetailContext(lastImportedAsset, store.references));
  }

  if (failedMessages.length > 0) {
    const skippedText = skippedCount > 0 ? `，跳过 ${skippedCount} 个重复路径` : "";
    store.importError = `已导入 ${importedNames.length} 个，${failedMessages.length} 个失败${skippedText}：${failedMessages[0]}`;
    importSuccessMessage.value = null;
    return;
  }

  const skippedText = skippedCount > 0 ? `，跳过 ${skippedCount} 个重复路径` : "";
  importSuccessMessage.value =
    importedNames.length === 1
      ? `已导入真实本地资产：${importedNames[0]}${skippedText}`
      : `已导入 ${importedNames.length} 个真实本地资产${skippedText}`;
}

async function pickAssetFilePaths(): Promise<string[]> {
  try {
    const selected = await open({
      multiple: true,
      filters: [
        {
          name: "创作资产",
          extensions: [
            "mp4",
            "mov",
            "mkv",
            "webm",
            "png",
            "jpg",
            "jpeg",
            "webp",
            "gif",
            "mp3",
            "wav",
            "m4a",
            "aac",
            "txt",
            "md",
            "srt",
            "json",
            "csv",
            "pdf",
            "doc",
            "docx"
          ]
        }
      ]
    });
    if (typeof selected === "string") return [selected];
    if (Array.isArray(selected)) return selected.filter((item): item is string => typeof item === "string");
    importInfoMessage.value = "已取消选择资产文件。";
    return [];
  } catch {
    store.importError = "无法打开系统文件选择器，请确认当前在桌面端运行后重试。";
    return [];
  }
}

async function selectAsset(assetId: string) {
  await store.select(assetId);
  const asset = store.assets.find((item) => item.id === assetId) ?? null;
  if (asset) {
    shellUiStore.openDetailWithContext(buildAssetDetailContext(asset, store.references));
  }
}

function clearSelection() {
  void store.select(null);
  shellUiStore.clearDetailContext("asset");
  shellUiStore.closeDetailPanel();
}

function openSelectedAssetDetail() {
  const asset = selectedAsset.value;
  if (!asset) return;
  shellUiStore.openDetailWithContext(buildAssetDetailContext(asset, store.references));
}

function buildAssetDetailContext(asset: AssetDto, references: typeof store.references) {
  const tags = store.parseTags(asset);
  return createRouteDetailContext("asset", {
    icon: "inventory_2",
    eyebrow: "资产详情",
    title: asset.name,
    description: "真实资产对象、引用影响和本地文件路径同步展示。",
    badge: {
      label: typeLabel(asset.type),
      tone: "brand"
    },
    metrics: [
      {
        id: "size",
        label: "大小",
        value: formatSize(asset.fileSizeBytes),
        hint: "来源于 Runtime 真实字段"
      },
      {
        id: "refs",
        label: "引用",
        value: String(references.length),
        hint: "删除前先检查引用"
      },
      {
        id: "project",
        label: "项目",
        value: asset.projectId || "未归入项目",
        hint: "不伪造项目归属"
      }
    ],
    sections: [
      {
        id: "source",
        title: "资产来源",
        fields: [
          { id: "type", label: "类型", value: typeLabel(asset.type) },
          { id: "source", label: "来源", value: asset.source },
          { id: "path", label: "路径", value: asset.filePath || "未记录路径", mono: true, multiline: true },
          { id: "duration", label: "时长", value: formatDuration(asset.durationMs) },
          { id: "created", label: "创建时间", value: formatShanghaiDateTime(asset.createdAt), mono: true },
          { id: "updated", label: "更新时间", value: formatShanghaiDateTime(asset.updatedAt), mono: true }
        ]
      },
      {
        id: "tags",
        title: "标签",
        emptyLabel: "Runtime 还没有为这个资产返回标签。",
        items: tags.map((tag) => ({
          id: tag,
          title: tag,
          icon: "sell",
          tone: "brand"
        }))
      },
      {
        id: "references",
        title: "引用影响",
        emptyLabel: "当前资产没有被项目链路引用。",
        items: references.map((reference) => ({
          id: reference.id,
          title: reference.referenceType,
          description: reference.referenceId,
          meta: formatShanghaiDateTime(reference.createdAt),
          icon: "link"
        }))
      }
    ],
    actions: [
      {
        id: "open-detail",
        label: "打开详情面板",
        icon: "right_panel_open",
        tone: "brand"
      },
      {
        id: "clear-selection",
        label: "清空选择",
        icon: "close",
        tone: "neutral"
      }
    ]
  });
}

function inferAssetType(name: string, mime = "") {
  if (mime.startsWith("video/")) return "video";
  if (mime.startsWith("image/")) return "image";
  if (mime.startsWith("audio/")) return "audio";
  const lowerName = name.toLowerCase();
  if (/\.(mp4|mov|mkv|webm)$/.test(lowerName)) return "video";
  if (/\.(png|jpg|jpeg|webp|gif)$/.test(lowerName)) return "image";
  if (/\.(mp3|wav|m4a|aac)$/.test(lowerName)) return "audio";
  return "document";
}

function countTransferFiles(dataTransfer: DataTransfer | null) {
  if (!dataTransfer) return 0;
  if (dataTransfer.items?.length) {
    return Array.from(dataTransfer.items).filter((item) => item.kind === "file").length;
  }
  return dataTransfer.files?.length ?? 0;
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

function formatDuration(durationMs: number | null) {
  if (durationMs === null) return "未记录时长";
  const totalSeconds = Math.max(0, Math.round(durationMs / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
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

function toTime(value: string) {
  const time = new Date(value).getTime();
  return Number.isNaN(time) ? 0 : time;
}
</script>

<style scoped>
.asset-library {
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--color-bg-canvas, var(--surface-primary)) 96%, transparent),
      var(--color-bg-canvas, var(--surface-primary))
    );
  color: var(--color-text-primary, var(--text-primary));
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.asset-library__drop-layer {
  align-items: center;
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 14%, var(--color-bg-surface, var(--surface-secondary)));
  border: 1px dashed color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 72%, var(--color-border-default, var(--border-default)));
  border-radius: var(--radius-md);
  color: var(--color-text-primary, var(--text-primary));
  display: flex;
  flex-direction: column;
  gap: 8px;
  inset: 18px;
  justify-content: center;
  pointer-events: none;
  position: absolute;
  z-index: 20;
}

.asset-library__drop-layer .material-symbols-outlined {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 48px;
}

.asset-library__drop-layer strong {
  font-size: 18px;
}

.asset-library__drop-layer span:last-child {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
}

.asset-library__hero {
  align-items: start;
  border-bottom: 1px solid var(--color-border-default, var(--border-default));
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px 18px;
}

.asset-library__hero-copy {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.asset-library__eyebrow {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0;
  text-transform: uppercase;
}

.asset-library__hero-copy h1 {
  font-size: 28px;
  line-height: 1.15;
  margin: 0;
}

.asset-library__hero-copy p {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
  line-height: 1.7;
  margin: 0;
  max-width: 760px;
}

.asset-library__hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.asset-library__hero-action {
  align-items: center;
  background: transparent;
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  color: var(--color-text-primary, var(--text-primary));
  cursor: pointer;
  display: inline-flex;
  gap: 6px;
  height: 36px;
  padding: 0 14px;
}

.asset-library__hero-action--brand {
  background: var(--color-brand-primary, var(--brand-primary));
  border-color: var(--color-brand-primary, var(--brand-primary));
  color: var(--color-text-on-brand, #fff);
}

.asset-library__hero-action:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.asset-library__summary {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  padding: 16px 24px 10px;
}

.summary-card {
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-md);
  background: var(--color-bg-surface, var(--surface-secondary));
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 14px;
}

.summary-card span {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.summary-card strong {
  font-size: 16px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-card p {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
  line-height: 1.5;
  margin: 0;
}

.asset-library__notice {
  align-items: center;
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 10%, var(--color-bg-surface, var(--surface-secondary)));
  border-bottom: 1px solid color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 24%, var(--color-border-default, var(--border-default)));
  color: var(--color-text-primary, var(--text-primary));
  display: flex;
  gap: 8px;
  min-height: 42px;
  padding: 8px 24px;
}

.asset-library__notice .material-symbols-outlined {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 18px;
}

.asset-library__notice--error {
  background: color-mix(in srgb, var(--color-danger, var(--status-error)) 10%, var(--color-bg-surface, var(--surface-secondary)));
  border-bottom-color: color-mix(in srgb, var(--color-danger, var(--status-error)) 35%, var(--color-border-default, var(--border-default)));
}

.asset-library__notice--error .material-symbols-outlined {
  color: var(--color-danger, var(--status-error));
}

.asset-library__notice--success {
  background: color-mix(in srgb, var(--color-success, var(--status-success)) 10%, var(--color-bg-surface, var(--surface-secondary)));
  border-bottom-color: color-mix(in srgb, var(--color-success, var(--status-success)) 35%, var(--color-border-default, var(--border-default)));
}

.asset-library__notice--success .material-symbols-outlined {
  color: var(--color-success, var(--status-success));
}

.asset-library__notice--info {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 10%, var(--color-bg-surface, var(--surface-secondary)));
  border-bottom-color: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 35%, var(--color-border-default, var(--border-default)));
}

.asset-library__body {
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 360px);
  min-height: 0;
  padding: 0 24px 24px;
}

.asset-library__workspace,
.asset-library__inspector {
  min-height: 0;
}

.asset-library__workspace {
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-md);
  background: var(--color-bg-surface, var(--surface-secondary));
  min-height: 0;
  overflow: hidden;
}

.asset-library__inspector {
  display: grid;
  gap: 12px;
  align-content: start;
}

.inspector-card {
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-md);
  background: var(--color-bg-surface, var(--surface-secondary));
  display: grid;
  gap: 14px;
  padding: 16px;
}

.inspector-card--soft {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 4%, var(--color-bg-surface, var(--surface-secondary)));
}

.inspector-card__eyebrow {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0;
  text-transform: uppercase;
}

.inspector-card__title-block {
  display: grid;
  gap: 5px;
}

.inspector-card__title-block h2 {
  font-size: 18px;
  line-height: 1.35;
  margin: 0;
  overflow-wrap: anywhere;
}

.inspector-card__title-block p {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
  margin: 0;
}

.inspector-metadata {
  display: grid;
  gap: 10px;
  margin: 0;
}

.inspector-metadata div {
  display: grid;
  gap: 4px;
}

.inspector-metadata dt {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
}

.inspector-metadata dd {
  font-size: 13px;
  margin: 0;
  overflow-wrap: anywhere;
}

.inspector-block {
  border-top: 1px solid var(--color-border-default, var(--border-default));
  padding-top: 14px;
  display: grid;
  gap: 10px;
}

.inspector-block__header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.inspector-block__header span {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.inspector-block__header strong {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 14%, transparent);
  border-radius: 999px;
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 12px;
  padding: 2px 8px;
}

.inspector-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.inspector-tags span {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 22%, transparent);
  border-radius: 999px;
  color: var(--color-text-primary, var(--text-primary));
  font-size: 11px;
  padding: 2px 8px;
}

.inspector-references {
  display: grid;
  gap: 8px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.inspector-references li {
  align-items: center;
  background: color-mix(in srgb, var(--color-bg-muted, var(--surface-tertiary)) 80%, transparent);
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  display: flex;
  gap: 10px;
  padding: 10px;
}

.inspector-references .material-symbols-outlined {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 18px;
}

.inspector-references div {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.inspector-references strong,
.inspector-references span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.inspector-references span {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 12px;
}

.inspector-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.inspector-actions__button {
  align-items: center;
  background: var(--color-brand-primary, var(--brand-primary));
  border: 1px solid var(--color-brand-primary, var(--brand-primary));
  border-radius: var(--radius-sm);
  color: var(--color-text-on-brand, #fff);
  cursor: pointer;
  display: inline-flex;
  flex: 1;
  justify-content: center;
  min-height: 36px;
  padding: 0 12px;
}

.inspector-actions__button--ghost {
  background: transparent;
  color: var(--color-text-primary, var(--text-primary));
}

.inspector-empty-state {
  align-items: center;
  display: grid;
  gap: 10px;
  justify-items: center;
  min-height: 280px;
  padding: 24px 12px;
  text-align: center;
}

.inspector-empty-state .material-symbols-outlined {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 40px;
}

.inspector-empty-state strong {
  font-size: 15px;
}

.inspector-empty-state p,
.inspector-empty,
.inspector-note {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
  line-height: 1.7;
  margin: 0;
}

.inspector-note--subtle {
  color: var(--color-text-tertiary, var(--text-tertiary));
}

@media (max-width: 1320px) {
  .asset-library__summary,
  .asset-library__body {
    grid-template-columns: 1fr;
  }

  .asset-library__hero {
    flex-direction: column;
  }

  .asset-library__hero-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 880px) {
  .asset-library__hero,
  .asset-library__summary,
  .asset-library__body {
    padding-left: 16px;
    padding-right: 16px;
  }

  .asset-library__notice {
    padding-left: 16px;
    padding-right: 16px;
  }
}
</style>
