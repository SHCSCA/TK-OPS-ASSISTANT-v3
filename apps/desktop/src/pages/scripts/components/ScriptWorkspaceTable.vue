<template>
  <article
    class="script-workspace-table"
    :class="`script-workspace-table--${density}`"
    data-script-workspace-table
    :data-script-workspace-density="density"
  >
    <div v-if="rows.length === 0" class="script-workspace-table__empty">
      暂无可表格化的脚本文案，请切换到原文补充内容。
    </div>
    <div v-else class="script-workspace-table__scroll">
      <table class="script-workspace-table__table">
        <thead>
          <tr>
            <th>段落</th>
            <th>时间</th>
            <th v-if="density === 'full'">段落目标</th>
            <th>口播文案</th>
            <th v-if="density === 'full'">屏幕字幕</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="`${row.segmentId}-${row.time}-${row.voiceover}`" data-script-workspace-row>
            <td class="script-workspace-table__id">{{ row.segmentId }}</td>
            <td>{{ row.time || "待确认" }}</td>
            <td v-if="density === 'full'">{{ row.goal || "未标注" }}</td>
            <td>
              <span class="script-workspace-table__copy">{{ row.voiceover || row.subtitle || "待补充" }}</span>
            </td>
            <td v-if="density === 'full'">{{ row.subtitle || row.voiceover || "待补充" }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";

import {
  buildScriptWorkspaceTableRows,
  type ScriptDocumentJson
} from "@/modules/scripts/script-document-view-model";

const props = defineProps<{
  content: string;
  documentJson?: ScriptDocumentJson | null;
  density?: "full" | "compact";
}>();

const rows = computed(() => buildScriptWorkspaceTableRows(props.documentJson, props.content));
const density = computed(() => props.density ?? "full");
</script>

<style scoped>
.script-workspace-table {
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
  color: var(--color-text-primary);
}

.script-workspace-table__scroll {
  flex: 1;
  min-width: 0;
  overflow: auto;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
}

.script-workspace-table__table {
  width: 100%;
  min-width: 920px;
  border-collapse: collapse;
  table-layout: fixed;
}

.script-workspace-table__table th,
.script-workspace-table__table td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border-subtle);
  text-align: left;
  vertical-align: top;
  white-space: normal;
  word-break: normal;
  overflow-wrap: anywhere;
}

.script-workspace-table__table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--color-bg-canvas);
  color: var(--color-text-primary);
  font: var(--font-title-sm);
}

.script-workspace-table__table td {
  color: var(--color-text-secondary);
  font: var(--font-body-md);
  line-height: 1.55;
}

.script-workspace-table__table th:nth-child(1),
.script-workspace-table__table td:nth-child(1) {
  width: 86px;
}

.script-workspace-table__table th:nth-child(2),
.script-workspace-table__table td:nth-child(2) {
  width: 108px;
}

.script-workspace-table__table th:nth-child(3),
.script-workspace-table__table td:nth-child(3) {
  width: 150px;
}

.script-workspace-table--compact .script-workspace-table__table {
  min-width: 560px;
}

.script-workspace-table--compact .script-workspace-table__table th,
.script-workspace-table--compact .script-workspace-table__table td {
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.5;
}

.script-workspace-table--compact .script-workspace-table__table th:nth-child(1),
.script-workspace-table--compact .script-workspace-table__table td:nth-child(1) {
  width: 68px;
}

.script-workspace-table--compact .script-workspace-table__table th:nth-child(2),
.script-workspace-table--compact .script-workspace-table__table td:nth-child(2) {
  width: 92px;
}

.script-workspace-table--compact .script-workspace-table__copy {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.script-workspace-table__table tbody tr:last-child td {
  border-bottom: 0;
}

td.script-workspace-table__id {
  color: var(--color-brand-primary);
  font-weight: 800;
}

.script-workspace-table__empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  border: 1px dashed var(--color-border-default);
  border-radius: var(--radius-md);
  color: var(--color-text-tertiary);
  font: var(--font-body-md);
  text-align: center;
}

@media (max-width: 980px) {
  .script-workspace-table__table {
    min-width: 760px;
  }

  .script-workspace-table__table th,
  .script-workspace-table__table td {
    padding: 12px;
  }
}
</style>
