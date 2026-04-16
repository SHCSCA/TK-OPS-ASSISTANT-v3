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
        <span>{{ dragFileCountLabel }}，只记录真实本地文件路径，不生成演示素材。</span>
      </div>

      <AssetToolbar
        :filter-type="store.filter.type"
        :is-importing="store.importStatus === 'importing'"
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

      <main class="asset-library__workspace">
        <AssetWall
          :assets="sortedAssets"
          :error="store.error"
          :parse-tags="store.parseTags"
          :selected-id="store.selectedId"
          :status="store.status"
          @import="handleUpload"
          @retry="store.load()"
          @select="selectAsset"
        />
      </main>
    </section>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { open } from "@tauri-apps/plugin-dialog";

import AssetToolbar from "@/components/assets/AssetToolbar.vue";
import AssetWall from "@/components/assets/AssetWall.vue";
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { useAssetLibraryStore } from "@/stores/asset-library";
import { useShellUiStore } from "@/stores/shell-ui";
import type { AssetDto } from "@/types/runtime";

const store = useAssetLibraryStore();
const shellUiStore = useShellUiStore();
const searchQuery = ref("");
const sortMode = ref<"latest" | "name" | "size">("latest");
const isDragging = ref(false);
const dragFileCount = ref(0);
const importSuccessMessage = ref<string | null>(null);
const importInfoMessage = ref<string | null>(null);
const importProgress = ref<{ completed: number; total: number } | null>(null);

const sortedAssets = computed(() => {
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

const dragFileCountLabel = computed(() => {
  if (dragFileCount.value <= 0) return "待识别本地文件";
  return `${dragFileCount.value} 个本地文件`;
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

onMounted(() => {
  void store.load();
});

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
  isDragging.value = true;
  dragFileCount.value = countTransferFiles(event.dataTransfer);
}

function handleDragLeave() {
  isDragging.value = false;
  dragFileCount.value = 0;
}

async function handleUpload() {
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
    store.references = [];
    shellUiStore.openDetailPanel();
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
  shellUiStore.openDetailPanel();
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

function toTime(value: string) {
  const time = new Date(value).getTime();
  return Number.isNaN(time) ? 0 : time;
}
</script>

<style scoped>
.asset-library {
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--surface-primary) 94%, transparent), var(--surface-primary)),
    var(--surface-primary);
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.asset-library__drop-layer {
  align-items: center;
  background: color-mix(in srgb, var(--brand-primary) 14%, var(--surface-secondary));
  border: 1px dashed color-mix(in srgb, var(--brand-primary) 72%, var(--border-default));
  border-radius: var(--radius-sm);
  color: var(--text-primary);
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
  color: var(--brand-primary);
  font-size: 48px;
}

.asset-library__drop-layer strong {
  font-size: 18px;
}

.asset-library__drop-layer span:last-child {
  color: var(--text-secondary);
  font-size: 13px;
}

.asset-library__notice {
  align-items: center;
  background: color-mix(in srgb, var(--status-error) 10%, var(--surface-secondary));
  border-bottom: 1px solid color-mix(in srgb, var(--status-error) 35%, var(--border-default));
  color: var(--text-primary);
  display: flex;
  gap: 8px;
  min-height: 42px;
  padding: 8px 24px;
}

.asset-library__notice .material-symbols-outlined {
  color: var(--status-error);
  font-size: 18px;
}

.asset-library__notice--success {
  background: color-mix(in srgb, var(--status-success) 10%, var(--surface-secondary));
  border-bottom-color: color-mix(in srgb, var(--status-success) 35%, var(--border-default));
}

.asset-library__notice--success .material-symbols-outlined {
  color: var(--status-success);
}

.asset-library__notice--info {
  background: color-mix(in srgb, var(--brand-primary) 10%, var(--surface-secondary));
  border-bottom-color: color-mix(in srgb, var(--brand-primary) 35%, var(--border-default));
}

.asset-library__notice--info .material-symbols-outlined {
  color: var(--brand-primary);
}

.asset-library__workspace {
  display: grid;
  flex: 1;
  grid-template-columns: minmax(0, 1fr);
  min-height: 0;
}
</style>
