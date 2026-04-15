<template>
  <ProjectContextGuard>
    <div class="asset-library" @dragover.prevent="isDragging = true" @dragleave.prevent="isDragging = false" @drop.prevent="handleDrop">
    <div v-if="isDragging" class="drag-overlay">
      <div class="drag-message">
        <span class="material-symbols-outlined">upload_file</span>
        <span>松开鼠标上传资产</span>
      </div>
    </div>

    <!-- 工具栏 -->
    <header class="asset-toolbar">
      <div class="toolbar-left">
        <div class="search-box">
          <span class="material-symbols-outlined">search</span>
          <input type="text" v-model="searchQuery" @input="handleSearch" placeholder="搜索资产名称..." />
        </div>
        <div class="type-tabs">
          <button v-for="tab in typeTabs" :key="tab.value" 
            :class="{ active: store.filter.type === tab.value }"
            @click="store.setFilterType(tab.value)">
            {{ tab.label }}
          </button>
        </div>
      </div>
      <div class="toolbar-right">
        <button class="btn-upload" @click="handleUpload">
          <span class="material-symbols-outlined">add</span>
          上传资产
        </button>
      </div>
    </header>

    <main class="asset-content">
      <!-- 资产网格 -->
      <section class="asset-grid-container">
        <div v-if="store.status === 'loading'" class="empty-state">
          <span class="material-symbols-outlined rotating">sync</span>
          <span>加载中...</span>
        </div>
        <div v-else-if="store.assets.length === 0" class="empty-state">
          <span class="material-symbols-outlined">folder_open</span>
          <span>暂无此类型资产</span>
        </div>
        <div v-else class="asset-grid">
          <div v-for="asset in store.assets" :key="asset.id" 
            class="asset-card" 
            :class="{ 'asset-card--selected': store.selectedId === asset.id }"
            @click="store.select(asset.id)">
            <div class="asset-card__thumb">
              <span class="material-symbols-outlined">{{ getAssetIcon(asset.type) }}</span>
              <button class="delete-btn" @click.stop="store.delete(asset.id)">
                <span class="material-symbols-outlined">delete</span>
              </button>
            </div>
            <div class="asset-card__meta">
              <div class="asset-name" :title="asset.name">{{ asset.name }}</div>
              <div class="asset-info">
                <span class="type-chip">{{ asset.type }}</span>
                <span class="size-text">{{ formatSize(asset.fileSizeBytes) }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 详情面板 -->
      <transition name="drawer">
        <aside v-if="selectedAsset" class="asset-detail-panel">
          <div class="panel-header">
            <h3>资产详情</h3>
            <button class="close-btn" @click="store.select(null)">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <div class="panel-body">
            <div class="detail-preview">
               <span class="material-symbols-outlined">{{ getAssetIcon(selectedAsset.type) }}</span>
            </div>
            <div class="detail-info">
              <div class="info-row">
                <label>名称</label>
                <span>{{ selectedAsset.name }}</span>
              </div>
              <div class="info-row">
                <label>类型</label>
                <span>{{ selectedAsset.type }}</span>
              </div>
              <div class="info-row">
                <label>大小</label>
                <span>{{ formatSize(selectedAsset.fileSizeBytes) }}</span>
              </div>
               <div class="info-row">
                <label>来源</label>
                <span>{{ selectedAsset.source }}</span>
              </div>
              <div class="info-row">
                <label>创建时间</label>
                <span>{{ formatDate(selectedAsset.createdAt) }}</span>
              </div>
            </div>
            <div class="detail-references">
              <h4>项目引用 ({{ store.references.length }})</h4>
              <div v-if="store.references.length === 0" class="no-references">
                暂无项目引用
              </div>
              <ul v-else class="reference-list">
                <li v-for="ref in store.references" :key="ref.id">
                  <span class="material-symbols-outlined">link</span>
                  <span class="ref-text">{{ ref.referenceType }}: {{ ref.referenceId }}</span>
                </li>
              </ul>
            </div>
          </div>
        </aside>
      </transition>
    </main>
  </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { useAssetLibraryStore } from '@/stores/asset-library';

const store = useAssetLibraryStore();
const searchQuery = ref('');
const isDragging = ref(false);

const typeTabs = [
  { label: '全部', value: '' },
  { label: '视频', value: 'video' },
  { label: '图片', value: 'image' },
  { label: '音频', value: 'audio' },
  { label: '文档', value: 'document' }
];

const selectedAsset = computed(() => 
  store.assets.find(a => a.id === store.selectedId)
);

onMounted(() => {
  store.load();
});

function handleSearch() {
  store.setSearchQuery(searchQuery.value);
}

function handleUpload() {
  alert('功能开发中：V1 仅支持通过项目导入或自动生成资产');
}

function handleDrop(e: DragEvent) {
  isDragging.value = false;
  const files = e.dataTransfer?.files;
  if (files && files.length > 0) {
    alert(`检测到 ${files.length} 个文件，功能开发中`);
  }
}

function getAssetIcon(type: string) {
  switch (type) {
    case 'video': return 'movie';
    case 'image': return 'image';
    case 'audio': return 'audiotrack';
    case 'document': return 'description';
    default: return 'draft';
  }
}

function formatSize(bytes: number | null) {
  if (!bytes) return '--';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  while (size > 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString();
}
</script>

<style scoped>
.asset-library {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  position: relative;
  overflow: hidden;
}

.drag-overlay {
  position: absolute;
  inset: var(--spacing-sm);
  background: rgba(0, 242, 234, 0.05);
  border: 2px dashed var(--brand-primary);
  border-radius: var(--radius-lg);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.drag-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--brand-primary);
}

.drag-message .material-symbols-outlined {
  font-size: 48px;
}

/* ── 工具栏 ── */
.asset-toolbar {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-lg);
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 0 12px;
  width: 240px;
  height: 32px;
}

.search-box input {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  width: 100%;
  outline: none;
}

.type-tabs {
  display: flex;
  gap: var(--spacing-sm);
}

.type-tabs button {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 4px 12px;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.type-tabs button:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.type-tabs button.active {
  color: var(--brand-primary);
  background: rgba(0, 242, 234, 0.1);
  font-weight: 600;
}

.btn-upload {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--brand-primary);
  color: #000;
  border: none;
  padding: 6px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

/* ── 主内容 ── */
.asset-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.asset-grid-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
}

.asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--spacing-lg);
}

.asset-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
}

.asset-card:hover {
  border-color: var(--border-default);
  transform: translateY(-2px);
  background: var(--bg-hover);
}

.asset-card--selected {
  border-color: var(--brand-primary);
  box-shadow: 0 0 0 1px var(--brand-primary);
}

.asset-card__thumb {
  aspect-ratio: 16/10;
  background: #252525;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.asset-card__thumb .material-symbols-outlined {
  font-size: 40px;
  color: var(--text-muted);
}

.delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.5);
  border: none;
  color: var(--text-secondary);
  width: 28px;
  height: 28px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.asset-card:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: var(--brand-secondary);
  background: rgba(255, 0, 80, 0.1);
}

.asset-card__meta {
  padding: 12px;
}

.asset-name {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.asset-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.type-chip {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.05);
  padding: 1px 6px;
  border-radius: 4px;
}

.size-text {
  font-size: 11px;
  color: var(--text-muted);
}

/* ── 详情面板 ── */
.asset-detail-panel {
  width: 360px;
  background: var(--bg-elevated);
  border-left: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.panel-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-lg);
  border-bottom: 1px solid var(--border-subtle);
}

.panel-header h3 {
  font-size: 15px;
  font-weight: 600;
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
}

.detail-preview {
  aspect-ratio: 16/9;
  background: #252525;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--spacing-xl);
}

.detail-preview .material-symbols-outlined {
  font-size: 64px;
  color: var(--text-muted);
}

.detail-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: var(--spacing-xl);
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.info-row label {
  color: var(--text-secondary);
}

.detail-references h4 {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.no-references {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  padding: 20px;
}

.reference-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reference-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 8px;
  background: var(--bg-card);
  border-radius: var(--radius-sm);
}

.ref-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 动画 ── */
.drawer-enter-active, .drawer-leave-active {
  transition: transform 0.3s ease;
}
.drawer-enter-from, .drawer-leave-to {
  transform: translateX(100%);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  gap: 12px;
}

.empty-state .material-symbols-outlined {
  font-size: 48px;
}

.rotating {
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
