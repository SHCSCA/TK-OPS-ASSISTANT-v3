<template>
  <section class="asset-wall" aria-label="素材墙">
    <div v-if="status === 'loading'" class="asset-state">
      <span class="material-symbols-outlined asset-state__spinner">sync</span>
      <strong>正在读取本地资产</strong>
      <p>同步 Runtime 中的真实文件记录和项目引用。</p>
    </div>

    <div v-else-if="status === 'error'" class="asset-state asset-state--error">
      <span class="material-symbols-outlined">warning</span>
      <strong>资产列表加载失败</strong>
      <p>{{ error }}</p>
      <button type="button" @click="$emit('retry')">重试加载</button>
    </div>

    <div v-else-if="assets.length === 0" class="asset-state asset-state--empty">
      <span class="material-symbols-outlined">folder_open</span>
      <strong>当前项目还没有可复用资产</strong>
      <p>导入真实本地视频、图片、音频或文档后，它们会出现在这里并参与分镜、剪辑和发布链路。</p>
      <button type="button" @click="$emit('import')">选择本地文件</button>
    </div>

    <div v-else class="asset-wall__ready">
      <div class="asset-wall__summary">
        <p class="asset-wall__summary-label">资产结果</p>
        <strong>{{ assets.length }} 个真实资产</strong>
        <span>选中后会同步打开右侧详情面板并保留引用检查结果。</span>
      </div>

      <TransitionGroup class="asset-wall__grid" name="asset-card-list" tag="div">
        <AssetCard
          v-for="asset in assets"
          :key="asset.id"
          :asset="asset"
          :is-selected="selectedId === asset.id"
          :tags="parseTags(asset)"
          @select="$emit('select', $event)"
        />
      </TransitionGroup>
    </div>
  </section>
</template>

<script setup lang="ts">
import AssetCard from "@/components/assets/AssetCard.vue";
import type { AssetDto } from "@/types/runtime";

defineProps<{
  assets: AssetDto[];
  error: string | null;
  parseTags: (asset: AssetDto) => string[];
  selectedId: string | null;
  status: "idle" | "loading" | "ready" | "error";
}>();

defineEmits<{
  import: [];
  retry: [];
  select: [assetId: string];
}>();
</script>

<style scoped>
.asset-wall {
  min-height: 0;
  overflow-y: auto;
  padding: 22px 24px 28px;
}

.asset-wall__grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}

.asset-wall__ready {
  display: grid;
  gap: 16px;
}

.asset-wall__summary {
  align-items: end;
  display: grid;
  gap: 4px;
}

.asset-wall__summary-label {
  color: var(--color-text-tertiary, var(--text-tertiary));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0;
  text-transform: uppercase;
}

.asset-wall__summary strong {
  color: var(--color-text-primary, var(--text-primary));
  font-size: 16px;
}

.asset-wall__summary span {
  color: var(--color-text-secondary, var(--text-secondary));
  font-size: 13px;
}

.asset-card-list-enter-active,
.asset-card-list-leave-active {
  transition:
    opacity 180ms ease,
    transform 180ms ease;
}

.asset-card-list-enter-from,
.asset-card-list-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.asset-state {
  align-items: center;
  color: var(--color-text-secondary, var(--text-secondary));
  display: flex;
  flex-direction: column;
  gap: 10px;
  justify-content: center;
  min-height: 360px;
  padding: 40px 20px;
  text-align: center;
}

.asset-state .material-symbols-outlined {
  color: var(--color-brand-primary, var(--brand-primary));
  font-size: 48px;
}

.asset-state strong {
  color: var(--color-text-primary, var(--text-primary));
  font-size: 16px;
}

.asset-state p {
  line-height: 1.7;
  margin: 0;
  max-width: 520px;
}

.asset-state button {
  background: var(--color-brand-primary, var(--brand-primary));
  border: 1px solid var(--color-brand-primary, var(--brand-primary));
  border-radius: var(--radius-sm);
  color: var(--color-text-on-brand, var(--brand-ink));
  cursor: pointer;
  font: inherit;
  font-weight: 800;
  height: 36px;
  margin-top: 4px;
  padding: 0 14px;
}

.asset-state--error button {
  background: transparent;
  color: var(--color-text-primary, var(--text-primary));
}

.asset-state__spinner {
  animation: asset-spin 1.2s linear infinite;
}

@keyframes asset-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .asset-card-list-enter-active,
  .asset-card-list-leave-active,
  .asset-state__spinner {
    animation: none;
    transition: none;
  }

  .asset-card-list-enter-from,
  .asset-card-list-leave-to {
    transform: none;
  }
}
</style>
