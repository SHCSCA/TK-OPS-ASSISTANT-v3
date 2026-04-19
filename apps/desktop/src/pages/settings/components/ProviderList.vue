<template>
  <div class="provider-list-container">
    <div class="list-toolbar">
      <div class="search-box">
        <span class="material-symbols-outlined">search</span>
        <input v-model="searchQuery" type="text" placeholder="搜索 Provider 名称..." />
      </div>
      
      <div class="filter-group">
        <Chip 
          v-for="cat in categories" 
          :key="cat.id"
          :variant="selectedCategory === cat.id ? 'brand' : 'default'"
          clickable
          @click="selectedCategory = cat.id"
        >
          {{ cat.label }}
        </Chip>
      </div>

      <Button variant="secondary" size="sm" disabled>
        <template #leading><span class="material-symbols-outlined">add</span></template>
        自定义 Provider
      </Button>
    </div>

    <div v-for="group in groupedProviders" :key="group.label" class="provider-group">
      <h4 class="group-title">{{ group.label }}</h4>
      <div class="provider-grid">
        <ProviderCard
          v-for="provider in group.items"
          :key="provider.provider"
          :provider="provider"
          @configure="$emit('configure', $event)"
          @test="$emit('test', $event)"
        />
      </div>
    </div>

    <div v-if="filteredProviders.length === 0" class="empty-state">
      <span class="material-symbols-outlined">search_off</span>
      <p>没有找到符合条件的 Provider。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import type { ProviderCardState, ProviderCategory } from "../types";
import ProviderCard from "./ProviderCard.vue";
import Button from "@/components/ui/Button/Button.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const props = defineProps<{
  providers: ProviderCardState[];
}>();

defineEmits<{
  (e: "configure", id: string): void;
  (e: "test", id: string): void;
}>();

const searchQuery = ref("");
const selectedCategory = ref<ProviderCategory>("all");

const categories: Array<{ id: ProviderCategory; label: string }> = [
  { id: "all", label: "全部" },
  { id: "commercial", label: "商业服务" },
  { id: "local", label: "本地推理" },
  { id: "aggregator", label: "聚合路由" },
  { id: "media", label: "媒体服务" }
];

const filteredProviders = computed(() => {
  let list = props.providers;
  
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase();
    list = list.filter(p => p.label.toLowerCase().includes(q) || p.provider.toLowerCase().includes(q));
  }
  
  if (selectedCategory.value !== "all") {
    list = list.filter(p => p.kind === selectedCategory.value);
  }
  
  return list;
});

const groupedProviders = computed(() => {
  const groups: Record<ProviderCategory, { label: string; items: ProviderCardState[] }> = {
    commercial: { label: "商业服务", items: [] },
    local: { label: "本地推理", items: [] },
    aggregator: { label: "聚合路由", items: [] },
    media: { label: "媒体服务", items: [] },
    all: { label: "其他", items: [] }
  };
  
  filteredProviders.value.forEach(p => {
    const cat = p.kind as ProviderCategory;
    if (cat && groups[cat]) {
      groups[cat].items.push(p);
    } else {
      groups.all.items.push(p);
    }
  });
  
  return Object.values(groups).filter(g => g.items.length > 0);
});
</script>

<style scoped>
.provider-list-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.list-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  background: var(--color-bg-canvas);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
}

.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  padding: 0 12px;
  height: 36px;
}

.search-box input {
  background: transparent;
  border: none;
  color: var(--color-text-primary);
  outline: none;
  flex: 1;
  font: var(--font-body-md);
}

.filter-group {
  display: flex;
  gap: 8px;
}

.provider-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.group-title {
  margin: 0;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--space-4);
}

.empty-state {
  text-align: center;
  padding: var(--space-12);
  color: var(--color-text-tertiary);
}

.empty-state .material-symbols-outlined {
  font-size: 48px;
  margin-bottom: var(--space-4);
  opacity: 0.5;
}
</style>
