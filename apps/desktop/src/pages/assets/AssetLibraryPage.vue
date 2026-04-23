<template>
  <ProjectContextGuard>
    <div
      class="page-container"
      @dragenter.prevent="handleDragOver"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <div v-if="isDragging" class="drag-layer">
        <div class="drag-layer__content">
          <span class="material-symbols-outlined">upload_file</span>
          <strong>松开导入到资产中心</strong>
          <p>{{ dragFileCountLabel }}，只记录真实本地文件路径，不生成额外占位素材。</p>
        </div>
      </div>

      <header class="page-header">
        <div class="page-header__crumb">首页 / 资产中心</div>
        <div class="page-header__row">
          <div>
            <h1 class="page-header__title">资产中心</h1>
            <div class="page-header__subtitle">管理导入、筛选、选择和引用检查，所有素材都必须来自真实本地文件或 Runtime 返回的记录。</div>
          </div>
          <div class="page-header__actions">
            <Button variant="secondary" @click="handleReload" :disabled="isBusy">
              <template #leading><span class="material-symbols-outlined">refresh</span></template>
              重新读取
            </Button>
            <Button variant="primary" @click="handleUpload" :running="store.importStatus === 'importing'" :disabled="isBusy">
              <template #leading><span class="material-symbols-outlined">add</span></template>
              {{ store.importStatus === "importing" ? "导入中..." : "导入资产" }}
            </Button>
          </div>
        </div>
      </header>

      <section class="summary-grid">
        <Card class="summary-card">
          <span class="sc-label">资产总数</span>
          <strong class="sc-val">{{ store.assets.length }}</strong>
          <p class="sc-hint">来自 Runtime 的真实资产记录</p>
        </Card>
        <Card class="summary-card">
          <span class="sc-label">当前结果</span>
          <strong class="sc-val">{{ visibleAssets.length }}</strong>
          <p class="sc-hint">按筛选和排序后的结果</p>
        </Card>
        <Card class="summary-card">
          <span class="sc-label">当前选中</span>
          <strong class="sc-val" :title="selectedAsset ? selectedAsset.name : '未选中'">
            {{ selectedAsset ? selectedAsset.name : "未选中" }}
          </strong>
          <p class="sc-hint" :title="selectedAsset ? selectedAsset.source : '请选择一个资产继续查看'">
            {{ selectedAsset ? selectedAsset.source : "请选择一个资产继续查看" }}
          </p>
        </Card>
        <Card class="summary-card">
          <span class="sc-label">导入状态</span>
          <strong class="sc-val">{{ importStatusLabel }}</strong>
          <p class="sc-hint" :title="importStatusHint">{{ importStatusHint }}</p>
        </Card>
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
        class="dashboard-alert"
        :data-tone="visibleNotice.type === 'error' ? 'danger' : visibleNotice.type === 'success' ? 'success' : 'brand'"
        role="status"
        style="margin-top: -8px;"
      >
        <div style="display:flex;align-items:center;gap:8px;">
          <span class="material-symbols-outlined">{{ visibleNotice.icon }}</span>
          <span>{{ visibleNotice.text }}</span>
        </div>
      </div>

      <div class="asset-workspace">
        <main class="asset-main">
          <Card class="asset-wall-card h-full">
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
          </Card>
        </main>

        <aside class="asset-rail">
          <Card class="rail-card">
            <div class="rail-card__header">
              <h3>选中资产</h3>
            </div>
            <div class="rail-card__body">
              <template v-if="selectedAsset">
                <AssetPreview :asset="selectedAsset" variant="detail" />

                <div class="inspector-title-block">
                  <h4 :title="selectedAsset.name">{{ selectedAsset.name }}</h4>
                  <p>{{ typeLabel(selectedAsset.type) }} · {{ selectedAsset.source }}</p>
                </div>

                <dl class="inspector-metadata">
                  <div><dt>状态</dt><dd>
                    <Chip v-if="assetStatus(selectedAsset).isInvalid" size="sm" variant="danger">已失效</Chip>
                    <Chip v-else-if="assetStatus(selectedAsset).isGenerating" size="sm" variant="warning">生成中</Chip>
                    <Chip v-else-if="store.references.length > 0" size="sm" variant="brand">已被引用</Chip>
                    <Chip v-else size="sm" variant="success">可用</Chip>
                  </dd></div>
                  <div><dt>路径</dt><dd :title="selectedAsset.filePath || '未记录路径'">{{ selectedAsset.filePath || "未记录路径" }}</dd></div>
                  <div><dt>大小</dt><dd>{{ formatSize(selectedAsset.fileSizeBytes) }}</dd></div>
                  <div><dt>时长</dt><dd>{{ formatDuration(selectedAsset.durationMs) }}</dd></div>
                  <div><dt>项目</dt><dd>{{ selectedAsset.projectId || "未归入项目" }}</dd></div>
                  <div><dt>创建</dt><dd>{{ formatShanghaiDateTime(selectedAsset.createdAt) }}</dd></div>
                  <div><dt>更新</dt><dd>{{ formatShanghaiDateTime(selectedAsset.updatedAt) }}</dd></div>
                </dl>

                <div class="inspector-block">
                  <div class="inspector-block__header">
                    <span>标签</span>
                    <Chip size="sm" variant="brand">{{ selectedTags.length }}</Chip>
                  </div>
                  <div v-if="selectedTags.length" class="inspector-tags">
                    <span v-for="tag in selectedTags" :key="tag" class="tag-item">{{ tag }}</span>
                  </div>
                  <p v-else class="inspector-empty">Runtime 还没有为该资产返回标签。</p>
                </div>

                <div class="inspector-block">
                  <div class="inspector-block__header">
                    <span>引用影响</span>
                    <Chip size="sm" variant="brand">{{ store.references.length }}</Chip>
                  </div>
                  <p v-if="store.references.length === 0" class="inspector-empty">
                    当前资产暂无引用，删除前依然会先经过 Runtime 引用检查。
                  </p>
                  <ul v-else class="inspector-references">
                    <li v-for="reference in store.references" :key="reference.id">
                      <span class="material-symbols-outlined">link</span>
                      <div class="ref-info">
                        <strong>{{ reference.referenceType }}</strong>
                        <span>{{ reference.referenceId }}</span>
                      </div>
                    </li>
                  </ul>
                </div>

                <div class="inspector-actions">
                  <Button variant="primary" block @click="openSelectedAssetDetail">打开详情面板</Button>
                  <Button variant="ghost" block @click="clearSelection">清空选择</Button>
                </div>
              </template>

              <template v-else>
                <div class="inspector-empty-state">
                  <span class="material-symbols-outlined">ads_click</span>
                  <strong>当前未选中资产</strong>
                  <p>你现在可以从左侧素材墙选择一个真实资产，右侧会同步显示文件路径、引用影响和标签。</p>
                </div>
              </template>
            </div>
          </Card>

          <Card class="rail-card soft-card">
            <div class="rail-card__header">
              <h3>导入边界</h3>
            </div>
            <div class="rail-card__body">
              <p class="inspector-note">导入只接收桌面端真实文件路径，拖拽或选择器失效时会明确提示，不会生成假素材或空壳记录。</p>
              <p class="inspector-note subtle">当 Runtime 返回错误时，页面会保留中文错误消息和重试入口，不吞掉异常。</p>
            </div>
          </Card>
        </aside>
      </div>
    </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import AssetPreview from "@/components/assets/AssetPreview.vue";
import AssetToolbar from "@/components/assets/AssetToolbar.vue";
import AssetWall from "@/components/assets/AssetWall.vue";
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import { useAssetLibraryStore } from "@/stores/asset-library";
import type { AssetDto } from "@/types/runtime";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

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

const selectedAsset = computed(() => store.assets.find((asset) => asset.id === store.selectedId) ?? null);
const selectedTags = computed(() => (selectedAsset.value ? store.parseTags(selectedAsset.value) : []));
const dragFileCountLabel = computed(() => dragFileCount.value <= 0 ? "待识别本地文件" : `${dragFileCount.value} 个本地文件`);
const isBusy = computed(() => store.status === "loading" || store.importStatus === "importing");

function assetStatus(asset: AssetDto | null) {
  if (!asset) return { isGenerating: false, isInvalid: false };
  const isGenerating = asset.source !== 'local' && !asset.fileSizeBytes && !asset.filePath;
  const isInvalid = !isGenerating && !asset.filePath;
  return { isGenerating, isInvalid };
}

const importStatusLabel = computed(() => {
  switch (store.importStatus) {
    case "importing": return "导入中";
    case "succeeded": return "最近导入成功";
    case "failed": return "导入失败";
    default: return "待命";
  }
});

const importStatusHint = computed(() => {
  if (importProgress.value) return `正在导入 ${importProgress.value.completed}/${importProgress.value.total} 个真实本地资产`;
  if (store.importStatus === "failed") return store.importError || "导入失败";
  if (store.importStatus === "succeeded") return importSuccessMessage.value || "已导入真实本地资产";
  if (store.importStatus === "importing") return "正在等待桌面文件选择器和 Runtime 导入响应";
  return "导入只会写入真实本地文件，不会生成占位素材";
});

const visibleNotice = computed(() => {
  const error = store.deleteError || store.importError || store.error;
  if (error) return { icon: "error", text: error, type: "error" };
  if (importProgress.value) return { icon: "sync", text: `正在导入 ${importProgress.value.completed}/${importProgress.value.total} 个真实本地资产`, type: "info" };
  if (importSuccessMessage.value) return { icon: "check_circle", text: importSuccessMessage.value, type: "success" };
  if (importInfoMessage.value) return { icon: "info", text: importInfoMessage.value, type: "info" };
  return null;
});

watch(selectedAsset, (asset) => {
  if (!asset) {
    shellUiStore.clearDetailContext("asset");
    shellUiStore.closeDetailPanel();
    return;
  }
  shellUiStore.openDetailWithContext(buildAssetDetailContext(asset, store.references));
}, { immediate: true });

onMounted(() => { void store.load(); });
onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("asset");
  shellUiStore.closeDetailPanel();
});

function handleReload() { void store.load(); }
function handleSearch(query: string) { searchQuery.value = query; void store.setSearchQuery(query); }
function handleFilterType(type: string) { void store.setFilterType(type); }
function handleSort(mode: string) { if (mode === "latest" || mode === "name" || mode === "size") sortMode.value = mode; }

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
  const validPaths = filePaths.map((p) => p.trim()).filter((p) => p.length > 0);
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
      const imported = await store.importLocalFile({ filePath, type: inferAssetType(filePath), source: "local" });
      importedNames.push(imported.name);
      lastImportedAsset = imported;
    } catch (error) {
      failedMessages.push(error instanceof Error ? error.message : `${filePath} 导入失败`);
    } finally {
      importProgress.value = { completed: (importProgress.value?.completed ?? 0) + 1, total: uniquePaths.length };
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
  importSuccessMessage.value = importedNames.length === 1 ? `已导入真实本地资产：${importedNames[0]}${skippedText}` : `已导入 ${importedNames.length} 个真实本地资产${skippedText}`;
}

async function pickAssetFilePaths(): Promise<string[]> {
  try {
    const dialogModuleName = "@tauri-apps/plugin-dialog";
    const { open } = await import(/* @vite-ignore */ dialogModuleName);
    const selected = await open({
      multiple: true,
      filters: [{ name: "创作资产", extensions: ["mp4", "mov", "mkv", "webm", "png", "jpg", "jpeg", "webp", "gif", "mp3", "wav", "m4a", "aac", "txt", "md", "srt", "json", "csv", "pdf", "doc", "docx"] }]
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
    badge: { label: typeLabel(asset.type), tone: "brand" },
    metrics: [
      { id: "size", label: "大小", value: formatSize(asset.fileSizeBytes), hint: "来源于 Runtime 真实字段" },
      { id: "refs", label: "引用", value: String(references.length), hint: "删除前先检查引用" },
      { id: "project", label: "项目", value: asset.projectId || "未归入项目", hint: "不伪造项目归属" }
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
        items: tags.map((tag) => ({ id: tag, title: tag, icon: "sell", tone: "brand" }))
      },
      {
        id: "references",
        title: "引用影响",
        emptyLabel: "当前资产没有被项目链路引用。",
        items: references.map((reference) => ({
          id: reference.id, title: reference.referenceType, description: reference.referenceId, meta: formatShanghaiDateTime(reference.createdAt), icon: "link"
        }))
      }
    ],
    actions: [
      { id: "open-detail", label: "打开详情面板", icon: "right_panel_open", tone: "brand" },
      { id: "clear-selection", label: "清空选择", icon: "close", tone: "neutral" }
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
  if (dataTransfer.items?.length) return Array.from(dataTransfer.items).filter((item) => item.kind === "file").length;
  return dataTransfer.files?.length ?? 0;
}

function typeLabel(type: string) {
  const map: Record<string, string> = { video: "视频", image: "图片", audio: "音频", document: "文档" };
  return map[type] || type || "未知";
}

function formatSize(bytes: number | null) {
  if (bytes === null) return "未记录";
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let i = 0;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatDuration(durationMs: number | null) {
  if (durationMs === null) return "未记录时长";
  const totalSeconds = Math.max(0, Math.round(durationMs / 1000));
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatShanghaiDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false, hourCycle: "h23"
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
.page-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-8) var(--space-8);
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

.drag-layer {
  position: absolute;
  inset: var(--space-8);
  background: color-mix(in srgb, var(--color-brand-primary) 10%, var(--color-bg-canvas));
  border: 2px dashed var(--color-brand-primary);
  border-radius: var(--radius-xl);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drag-layer__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  color: var(--color-brand-primary);
}

.drag-layer__content .material-symbols-outlined {
  font-size: 64px;
}

.page-header {
  display: grid;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.summary-card {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: transform var(--motion-fast) var(--ease-spring);
}

.summary-card:active {
  transform: scale(0.98);
}

.sc-label {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.sc-val {
  font: var(--font-title-md);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sc-hint {
  font: var(--font-caption);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-alert {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-muted);
  line-height: 1.6;
  margin-bottom: var(--space-4);
  font: var(--font-body-sm);
}

.dashboard-alert[data-tone="danger"] {
  border-color: rgba(255, 90, 99, 0.20);
  background: rgba(255, 90, 99, 0.08);
  color: var(--color-danger);
}

.dashboard-alert[data-tone="success"] {
  border-color: rgba(34, 211, 154, 0.20);
  background: rgba(34, 211, 154, 0.08);
  color: var(--color-success);
}

.dashboard-alert[data-tone="brand"] {
  border-color: rgba(0, 188, 212, 0.20);
  background: rgba(0, 188, 212, 0.08);
  color: var(--color-brand-primary);
}

.asset-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
  margin-top: var(--space-4);
}

.asset-main {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.asset-main :deep(.asset-wall) {
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-strong) transparent;
}

.asset-main :deep(.asset-wall)::-webkit-scrollbar {
  width: 4px;
}
.asset-main :deep(.asset-wall)::-webkit-scrollbar-thumb {
  background: var(--color-border-strong);
  border-radius: 99px;
}

.h-full {
  height: 100%;
}

.asset-wall-card {
  padding: 0; /* Let AssetWall handle padding */
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.asset-rail {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-strong) transparent;
}

.asset-rail::-webkit-scrollbar {
  width: 4px;
}
.asset-rail::-webkit-scrollbar-thumb {
  background: var(--color-border-strong);
  border-radius: 99px;
}

.rail-card {
  padding: 0;
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

.soft-card {
  background: color-mix(in srgb, var(--color-brand-primary) 4%, var(--color-bg-surface));
}

.inspector-title-block h4 {
  margin: 0 0 4px 0;
  font: var(--font-title-md);
  color: var(--color-text-primary);
  overflow-wrap: anywhere;
}

.inspector-title-block p {
  margin: 0;
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.inspector-metadata {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.inspector-metadata div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.inspector-metadata dt {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.inspector-metadata dd {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-primary);
  overflow-wrap: anywhere;
}

.inspector-block {
  border-top: 1px solid var(--color-border-subtle);
  padding-top: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.inspector-block__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.inspector-block__header span {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.inspector-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.tag-item {
  font: var(--font-caption);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  padding: 2px 8px;
  border-radius: 999px;
  color: var(--color-text-secondary);
}

.inspector-empty {
  margin: 0;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.inspector-references {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.inspector-references li {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
}

.inspector-references .material-symbols-outlined {
  font-size: 16px;
  color: var(--color-brand-primary);
}

.ref-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.ref-info strong {
  font: var(--font-caption);
  color: var(--color-text-primary);
}

.ref-info span {
  font: var(--font-caption);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.inspector-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.inspector-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: var(--space-3);
  padding: var(--space-8) 0;
  color: var(--color-text-tertiary);
}

.inspector-empty-state .material-symbols-outlined {
  font-size: 40px;
  color: var(--color-brand-primary);
}

.inspector-empty-state strong {
  font: var(--font-title-sm);
  color: var(--color-text-primary);
}

.inspector-empty-state p {
  margin: 0;
  font: var(--font-body-sm);
  line-height: 1.5;
}

.inspector-note {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.inspector-note.subtle {
  color: var(--color-text-tertiary);
}

@media (max-width: 1180px) {
  .asset-workspace {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 860px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .page-header__row {
    flex-direction: column;
  }
}
</style>
