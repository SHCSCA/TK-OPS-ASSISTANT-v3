<template>
  <header class="asset-toolbar">
    <div class="asset-toolbar__heading">
      <span class="asset-toolbar__eyebrow">M09 资产中心</span>
      <h1>资产中心</h1>
      <p>沉淀创作素材、分镜引用和剪辑可复用文件，保持每个资产都能追踪到真实来源。</p>
    </div>

    <div class="asset-toolbar__controls">
      <label class="asset-toolbar__search">
        <span class="material-symbols-outlined">search</span>
        <input
          :value="searchQuery"
          type="search"
          placeholder="搜索资产名称、标签或来源"
          @input="emitSearch"
        />
      </label>

      <div class="asset-toolbar__tabs" aria-label="资产类型筛选">
        <button
          v-for="tab in typeTabs"
          :key="tab.value"
          :class="{ active: filterType === tab.value }"
          type="button"
          @click="$emit('filter-type', tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>

      <label class="asset-toolbar__sort">
        <span>排序</span>
        <select :value="sortMode" @change="emitSort">
          <option value="latest">最新导入</option>
          <option value="name">名称 A-Z</option>
          <option value="size">文件大小</option>
        </select>
      </label>

      <button
        class="asset-toolbar__import"
        data-testid="asset-import-button"
        type="button"
        :disabled="isImporting"
        @click="$emit('import')"
      >
        <span class="material-symbols-outlined">add</span>
        {{ isImporting ? "导入中" : "导入资产" }}
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  filterType: string;
  isImporting: boolean;
  searchQuery: string;
  sortMode: string;
}>();

const typeTabs = [
  { label: "全部", value: "" },
  { label: "视频", value: "video" },
  { label: "图片", value: "image" },
  { label: "音频", value: "audio" },
  { label: "文档", value: "document" }
];

function emitSearch(event: Event) {
  const target = event.target as HTMLInputElement;
  emit("search", target.value);
}

function emitSort(event: Event) {
  const target = event.target as HTMLSelectElement;
  emit("sort", target.value);
}

const emit = defineEmits<{
  "filter-type": [type: string];
  import: [];
  search: [query: string];
  sort: [mode: string];
}>();
</script>

<style scoped>
.asset-toolbar {
  border-bottom: 1px solid var(--color-border-default, var(--border-default));
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(260px, 1fr) minmax(420px, auto);
  padding: 20px 24px 18px;
}

.asset-toolbar__heading {
  min-width: 0;
}

.asset-toolbar__eyebrow {
  color: var(--color-brand-primary, var(--brand-primary));
  display: block;
  font-size: 12px;
  font-weight: 800;
  margin-bottom: 6px;
}

.asset-toolbar__heading h1 {
  font-size: 28px;
  line-height: 1.15;
  margin: 0;
}

.asset-toolbar__heading p {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
  line-height: 1.7;
  margin: 9px 0 0;
  max-width: 720px;
}

.asset-toolbar__controls {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.asset-toolbar__search,
.asset-toolbar__sort {
  align-items: center;
  background: var(--color-bg-surface, var(--surface-secondary));
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  display: flex;
  height: 38px;
}

.asset-toolbar__search {
  gap: 8px;
  min-width: 250px;
  padding: 0 11px;
}

.asset-toolbar__search .material-symbols-outlined {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 18px;
}

.asset-toolbar__search input {
  background: transparent;
  border: none;
  color: var(--color-text-primary, var(--text-primary));
  font-size: 13px;
  min-width: 0;
  outline: none;
  width: 100%;
}

.asset-toolbar__tabs {
  background: var(--color-bg-surface, var(--surface-secondary));
  border: 1px solid var(--color-border-default, var(--border-default));
  border-radius: var(--radius-sm);
  display: flex;
  height: 38px;
  overflow: hidden;
}

.asset-toolbar__tabs button,
.asset-toolbar__import,
.asset-toolbar__sort select {
  border-radius: var(--radius-sm);
  cursor: pointer;
  font: inherit;
}

.asset-toolbar__tabs button {
  background: transparent;
  border: none;
  color: var(--color-text-secondary, var(--text-secondary));
  padding: 0 12px;
}

.asset-toolbar__tabs button.active,
.asset-toolbar__tabs button:hover {
  background: color-mix(in srgb, var(--color-brand-primary, var(--brand-primary)) 14%, transparent);
  color: var(--color-text-primary, var(--text-primary));
}

.asset-toolbar__sort {
  color: var(--color-text-secondary, var(--text-secondary));
  gap: 7px;
  padding: 0 6px 0 10px;
}

.asset-toolbar__sort span {
  font-size: 12px;
  font-weight: 700;
}

.asset-toolbar__sort select {
  background: transparent;
  border: none;
  color: var(--color-text-primary, var(--text-primary));
  height: 30px;
  outline: none;
}

.asset-toolbar__import {
  align-items: center;
  background: var(--color-brand-primary, var(--brand-primary));
  border: 1px solid var(--color-brand-primary, var(--brand-primary));
  color: var(--color-text-on-brand, var(--brand-ink));
  display: flex;
  font-weight: 800;
  gap: 6px;
  height: 38px;
  padding: 0 15px;
}

.asset-toolbar__import:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

@media (max-width: 1180px) {
  .asset-toolbar {
    grid-template-columns: 1fr;
  }

  .asset-toolbar__controls {
    justify-content: flex-start;
  }
}
</style>
