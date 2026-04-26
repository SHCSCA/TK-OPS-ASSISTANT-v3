<template>
  <section class="video-result-view">
    <div class="result-tabs" role="tablist" aria-label="视频拆解结果">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        :data-active="activeTab === tab.id"
        role="tab"
        :aria-selected="activeTab === tab.id"
        @click="$emit('update:activeTab', tab.id)"
      >
        <span class="material-symbols-outlined">{{ tab.icon }}</span>
        {{ tab.label }}
      </button>
    </div>

    <div class="result-body">
      <div v-if="activeTab === 'script'" class="script-timeline">
        <article v-for="line in scriptLines" :key="line.key" class="script-line">
          <div class="script-line__time">{{ line.timeLabel }}</div>
          <div class="script-line__content">
            <p class="script-line__primary">{{ line.primary }}</p>
            <p v-if="line.secondary" class="script-line__secondary">{{ line.secondary }}</p>
          </div>
        </article>
        <div v-if="scriptLines.length === 0" class="result-empty">
          <strong>{{ scriptEmptyTitle }}</strong>
          <p>{{ scriptEmptyDescription }}</p>
          <Button
            v-if="needsProviderConfiguration"
            variant="secondary"
            size="sm"
            @click="$emit('configureProvider')"
          >
            配置视频解析模型
          </Button>
        </div>
      </div>

      <div v-else-if="activeTab === 'keyframes'" class="keyframe-table">
        <table v-if="keyframes.length > 0">
          <thead>
            <tr>
              <th>镜头号</th>
              <th>时间</th>
              <th>画面内容</th>
              <th>口播/字幕</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="keyframe in keyframes" :key="keyframe.index">
              <td class="keyframe-index">
                <span>{{ keyframe.index }}</span>
                <small v-if="keyframe.shotType || keyframe.camera">
                  {{ [keyframe.shotType, keyframe.camera].filter(Boolean).join(" / ") }}
                </small>
              </td>
              <td>{{ formatRange(keyframe.startMs, keyframe.endMs) }}</td>
              <td>
                <strong v-if="keyframe.intent">{{ keyframe.intent }}</strong>
                <p>{{ keyframe.visual || "未识别画面" }}</p>
              </td>
              <td>{{ keyframeSpeechText(keyframe) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="result-empty">
          <strong>还没有关键帧结果</strong>
          <p>点击“开始拆解”后生成视频关键帧和基础分段。</p>
        </div>
      </div>

      <div v-else class="structure-result">
        <div v-if="structureTags.length > 0" class="structure-map">
          <strong>话术结构</strong>
          <div class="structure-tags">
            <span
              v-for="tag in structureTags"
              :key="tag.id"
              class="structure-tag"
              :data-tone="tag.tone"
            >
              {{ tag.label }}
            </span>
          </div>
        </div>

        <article
          v-for="block in structureBlocks"
          :key="block.id"
          class="structure-block"
          :data-tone="block.tone"
        >
          <h4>{{ block.title }}</h4>
          <p>{{ block.body }}</p>
          <div v-if="block.evidence.length > 0" class="structure-block__reason">
            <strong>结构作用</strong>
            <ul>
              <li v-for="item in block.evidence" :key="item">{{ item }}</li>
            </ul>
          </div>
        </article>

        <div v-if="structureBlocks.length === 0" class="result-empty">
          <strong>还没有内容结构</strong>
          <p>点击“开始拆解”后生成可回流到脚本与分镜的结构信息。</p>
        </div>
      </div>
    </div>

    <div class="result-utility-actions">
      <Button variant="secondary" size="sm" :disabled="!canCopyScript" @click="$emit('copyScript')">
        <template #leading><span class="material-symbols-outlined">content_copy</span></template>
        复制脚本
      </Button>
      <Button variant="secondary" size="sm" :disabled="!canCopyStructure" @click="$emit('copyStructure')">
        <template #leading><span class="material-symbols-outlined">data_object</span></template>
        复制结构
      </Button>
    </div>
  </section>
</template>

<script setup lang="ts">
import Button from "@/components/ui/Button/Button.vue";
import type { VideoKeyframeDto } from "@/types/runtime";
import type {
  VideoResultTabId,
  VideoScriptDisplayLine,
  VideoStructureDisplayBlock,
  VideoStructureDisplayTag
} from "../video-result-presenters";

defineProps<{
  activeTab: VideoResultTabId;
  tabs: Array<{ id: VideoResultTabId; label: string; icon: string }>;
  scriptLines: VideoScriptDisplayLine[];
  scriptEmptyTitle: string;
  scriptEmptyDescription: string;
  needsProviderConfiguration: boolean;
  keyframes: VideoKeyframeDto[];
  structureTags: VideoStructureDisplayTag[];
  structureBlocks: VideoStructureDisplayBlock[];
  canCopyScript: boolean;
  canCopyStructure: boolean;
}>();

defineEmits<{
  "update:activeTab": [tab: VideoResultTabId];
  copyScript: [];
  copyStructure: [];
  configureProvider: [];
}>();

function keyframeSpeechText(keyframe: VideoKeyframeDto): string {
  return [keyframe.speech, keyframe.onscreenText].filter(Boolean).join(" / ") || "未识别口播或字幕";
}

function formatRange(startMs: number, endMs: number): string {
  return `${formatMs(startMs)}-${formatMs(endMs)}`;
}

function formatMs(value: number): string {
  const seconds = Math.floor(value / 1000);
  const mins = Math.floor(seconds / 60);
  const secs = String(seconds % 60).padStart(2, "0");
  return `${mins}:${secs}`;
}
</script>

<style scoped>
.video-result-view {
  display: grid;
  gap: var(--space-3);
}

.result-tabs {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border-subtle);
}

.result-tabs button {
  border: 0;
  background: transparent;
  color: var(--color-text-secondary);
  border-radius: 999px;
  padding: 8px 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font: var(--font-title-xs);
  cursor: pointer;
}

.result-tabs button[data-active="true"] {
  color: var(--color-brand-primary);
  background: color-mix(in srgb, var(--color-brand-primary) 12%, transparent);
}

.result-tabs .material-symbols-outlined {
  font-size: 16px;
}

.result-body {
  min-height: 280px;
  max-height: 46vh;
  overflow: auto;
  padding-right: 4px;
}

.script-timeline {
  display: grid;
  gap: var(--space-3);
}

.script-line {
  display: grid;
  grid-template-columns: 98px minmax(0, 1fr);
  gap: var(--space-3);
  align-items: start;
  padding: var(--space-3);
  border-radius: var(--radius-lg);
  background: var(--color-bg-muted);
}

.script-line__time {
  color: var(--color-text-tertiary);
  font: var(--font-title-xs);
  letter-spacing: 0.01em;
  white-space: nowrap;
}

.script-line__content {
  display: grid;
  gap: 4px;
}

.script-line__primary {
  margin: 0;
  color: var(--color-text-primary);
  font: var(--font-body-md);
}

.script-line__secondary {
  margin: 0;
  color: var(--color-text-secondary);
  font: var(--font-body-sm);
}

.result-empty {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
}

.result-empty strong {
  color: var(--color-text-primary);
  font: var(--font-title-sm);
}

.keyframe-table {
  overflow-x: auto;
}

.keyframe-table table {
  width: 100%;
  border-collapse: collapse;
  font: var(--font-body-sm);
}

.keyframe-table th,
.keyframe-table td {
  border: 1px solid var(--color-border-subtle);
  padding: 10px 12px;
  text-align: left;
  vertical-align: top;
}

.keyframe-table th {
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  font: var(--font-title-xs);
}

.keyframe-table td p {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
}

.keyframe-index {
  min-width: 72px;
}

.keyframe-index span,
.keyframe-index small {
  display: block;
}

.keyframe-index small {
  margin-top: 4px;
  color: var(--color-text-tertiary);
}

.structure-result {
  display: grid;
  gap: var(--space-3);
}

.structure-map {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  background: linear-gradient(90deg, color-mix(in srgb, var(--color-brand-primary) 6%, transparent), var(--color-bg-muted));
}

.structure-map strong {
  color: var(--color-text-primary);
  font: var(--font-title-sm);
}

.structure-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.structure-tag {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 6px 10px;
  color: var(--color-text-primary);
  font: var(--font-caption);
}

.structure-tag[data-tone="hook"],
.structure-block[data-tone="hook"] {
  background: color-mix(in srgb, #ff8a8a 14%, var(--color-bg-muted));
}

.structure-tag[data-tone="scene"],
.structure-block[data-tone="scene"] {
  background: color-mix(in srgb, #78b7ff 14%, var(--color-bg-muted));
}

.structure-tag[data-tone="value"],
.structure-block[data-tone="value"] {
  background: color-mix(in srgb, #7be6a4 14%, var(--color-bg-muted));
}

.structure-tag[data-tone="proof"],
.structure-block[data-tone="proof"] {
  background: color-mix(in srgb, #8fe7e2 14%, var(--color-bg-muted));
}

.structure-tag[data-tone="cta"],
.structure-block[data-tone="cta"] {
  background: color-mix(in srgb, #c69cff 14%, var(--color-bg-muted));
}

.structure-tag[data-tone="risk"],
.structure-block[data-tone="risk"] {
  background: color-mix(in srgb, #ffd166 16%, var(--color-bg-muted));
}

.structure-block {
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid color-mix(in srgb, var(--color-border-subtle) 70%, transparent);
}

.structure-block h4 {
  margin: 0 0 var(--space-2);
  font: var(--font-title-sm);
  color: var(--color-text-primary);
}

.structure-block p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.structure-block__reason {
  display: grid;
  gap: var(--space-2);
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
}

.structure-block__reason strong {
  color: var(--color-text-primary);
  font: var(--font-title-xs);
}

.structure-block__reason ul {
  margin: 0;
  padding-left: 18px;
  line-height: 1.7;
}

.result-utility-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-subtle);
}

@media (max-width: 760px) {
  .script-line {
    grid-template-columns: 1fr;
  }
}
</style>
