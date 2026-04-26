<template>
  <div class="script-markdown-preview" data-script-preview v-html="previewHtml" />
</template>

<script setup lang="ts">
import { computed } from "vue";

import { renderScriptMarkdownPreview } from "@/pages/scripts/script-markdown-preview";

const props = defineProps<{
  markdown: string;
}>();

const previewHtml = computed(() => renderScriptMarkdownPreview(props.markdown));
</script>

<style scoped>
.script-markdown-preview {
  display: block;
  min-width: 0;
  color: var(--color-text-primary, #0f172a);
  font-size: 15px;
  line-height: 1.75;
}

.script-markdown-preview :deep(h1),
.script-markdown-preview :deep(h2),
.script-markdown-preview :deep(h3),
.script-markdown-preview :deep(h4),
.script-markdown-preview :deep(h5),
.script-markdown-preview :deep(h6) {
  margin: 0 0 14px;
  color: var(--color-text-primary, #0f172a);
  line-height: 1.35;
}

.script-markdown-preview :deep(h1),
.script-markdown-preview :deep(h2) {
  font-size: 26px;
  font-weight: 800;
}

.script-markdown-preview :deep(h3),
.script-markdown-preview :deep(h4) {
  font-size: 20px;
  font-weight: 800;
}

.script-markdown-preview :deep(h5),
.script-markdown-preview :deep(h6) {
  font-size: 16px;
  font-weight: 700;
}

.script-markdown-preview :deep(p),
.script-markdown-preview :deep(ul),
.script-markdown-preview :deep(ol),
.script-markdown-preview :deep(table),
.script-markdown-preview :deep(blockquote),
.script-markdown-preview :deep(pre) {
  margin: 0 0 16px;
}

.script-markdown-preview :deep(p),
.script-markdown-preview :deep(li) {
  color: var(--color-text-secondary, #334155);
}

.script-markdown-preview :deep(ul),
.script-markdown-preview :deep(ol) {
  padding-left: 22px;
}

.script-markdown-preview :deep(table) {
  width: 100%;
  border-collapse: collapse;
  border-radius: 8px;
  overflow: hidden;
  background: var(--color-bg-canvas, #ffffff);
  border: 1px solid var(--color-border-subtle, rgba(15, 23, 42, 0.08));
}

.script-markdown-preview :deep(th),
.script-markdown-preview :deep(td) {
  padding: 12px 14px;
  border-bottom: 1px solid var(--color-border-subtle, rgba(15, 23, 42, 0.08));
  text-align: left;
  vertical-align: top;
  font-size: 14px;
  line-height: 1.65;
}

.script-markdown-preview :deep(th) {
  background: var(--color-bg-muted, rgba(148, 163, 184, 0.08));
  color: var(--color-text-primary, #0f172a);
  font-weight: 700;
}

.script-markdown-preview :deep(code) {
  padding: 2px 6px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.06);
  font-size: 13px;
}

.script-markdown-preview :deep(pre) {
  overflow-x: auto;
  padding: 14px;
  border-radius: 8px;
  background: var(--color-bg-muted, rgba(148, 163, 184, 0.08));
}

.script-markdown-preview :deep(pre code) {
  padding: 0;
  background: transparent;
}

.script-markdown-preview :deep(blockquote) {
  padding-left: 14px;
  border-left: 3px solid var(--color-border-default, rgba(15, 23, 42, 0.18));
  color: var(--color-text-secondary, #334155);
}

.script-markdown-preview :deep(hr) {
  margin: 22px 0;
  border: none;
  border-top: 1px solid var(--color-border-subtle, rgba(15, 23, 42, 0.12));
}
</style>
