<template>
  <section class="sk-card sk-brand-card" data-testid="brand-kit-panel">
    <header class="sk-card__header">
      <div>
        <p class="sk-eyebrow">BrandKit</p>
        <h2>品牌约束</h2>
      </div>
      <span v-if="kit?.activeVersion" class="sk-pill sk-pill--active">
        v{{ kit.activeVersion }}
      </span>
    </header>

    <div v-if="kit?.active" class="sk-brand-summary">
      <div class="sk-brand-colors" aria-label="品牌色">
        <span
          v-for="color in visibleColors"
          :key="color"
          :style="{ backgroundColor: color }"
          :title="color"
        />
        <small v-if="hiddenColorCount">+{{ hiddenColorCount }}</small>
        <small v-if="!kit.active.colors.length">未配置品牌色</small>
      </div>
      <dl>
        <div>
          <dt>字体</dt>
          <dd>{{ fontSummary }}</dd>
        </div>
        <div>
          <dt>视觉规则</dt>
          <dd>{{ objectItemCount(kit.active.visualRules) }} 项</dd>
        </div>
        <div>
          <dt>Logo 素材</dt>
          <dd>{{ kit.active.logoAssetRefs.length }} 项</dd>
        </div>
        <div>
          <dt>口吻规则</dt>
          <dd>{{ objectItemCount(kit.active.voiceRules) }} 项</dd>
        </div>
      </dl>
    </div>
    <div v-else class="sk-inline-empty">
      <span class="material-symbols-outlined" aria-hidden="true">palette</span>
      <p>尚未配置 BrandKit。当前不会猜测品牌颜色或表达规则。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { BrandKitDto } from "@/types/runtime/account-knowledge";
import { objectItemCount } from "./knowledge-view-helpers";

const props = defineProps<{ kit: BrandKitDto | null }>();
const visibleColors = computed(() => props.kit?.active?.colors.slice(0, 6) ?? []);
const hiddenColorCount = computed(() =>
  Math.max(0, (props.kit?.active?.colors.length ?? 0) - visibleColors.value.length)
);
const fontSummary = computed(() => {
  const fonts = props.kit?.active?.fonts ?? [];
  if (!fonts.length) return "未配置";
  const visible = fonts.slice(0, 3).join("、");
  return fonts.length > 3 ? `${visible} 等 ${fonts.length} 项` : visible;
});
</script>
