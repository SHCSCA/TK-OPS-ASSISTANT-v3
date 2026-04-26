<template>
  <article class="script-structured-preview" data-script-structured-preview>
    <h1>{{ view.title }}</h1>

    <section class="structured-section">
      <h2>1. 脚本元信息</h2>
      <div class="structured-table-wrap">
        <table class="structured-table">
          <thead>
            <tr>
              <th v-for="header in view.infoTable.headers" :key="header">{{ header }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in view.infoTable.rows" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="structured-section">
      <h2>2. 分段脚本</h2>
      <div class="structured-table-wrap">
        <table class="structured-table">
          <thead>
            <tr>
              <th v-for="header in view.segmentTable.headers" :key="header">{{ header }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in view.segmentTable.rows" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-for="section in view.sections" :key="section.title" class="structured-section">
      <h2>{{ section.title }}</h2>
      <div v-if="section.kind === 'table' && section.table" class="structured-table-wrap">
        <table class="structured-table">
          <thead>
            <tr>
              <th v-for="header in section.table.headers" :key="header">{{ header }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in section.table.rows" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <ul v-else-if="section.kind === 'list'" class="structured-list">
        <li v-for="item in section.items" :key="item">{{ item }}</li>
      </ul>
      <p v-else>{{ section.text }}</p>
    </section>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";

import {
  buildScriptDocumentViewModel,
  type ScriptDocumentJson
} from "@/modules/scripts/script-document-view-model";

const props = defineProps<{
  documentJson: ScriptDocumentJson;
}>();

const view = computed(() => buildScriptDocumentViewModel(props.documentJson));
</script>

<style scoped>
.script-structured-preview {
  color: var(--text-primary);
  font-size: 0.95rem;
  line-height: 1.7;
}

.script-structured-preview h1,
.script-structured-preview h2 {
  margin: 0 0 14px;
  color: var(--text-strong);
  font-weight: 800;
  letter-spacing: -0.02em;
}

.script-structured-preview h1 {
  font-size: clamp(1.6rem, 2.2vw, 2.15rem);
}

.script-structured-preview h2 {
  font-size: 1.2rem;
}

.structured-section {
  margin: 0 0 24px;
}

.structured-table-wrap {
  max-width: 100%;
  overflow: auto;
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
}

.structured-table {
  width: 100%;
  min-width: 680px;
  border-collapse: collapse;
  background: var(--surface-raised);
}

.structured-table th,
.structured-table td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-subtle);
  border-left: 1px solid var(--border-subtle);
  text-align: left;
  vertical-align: top;
}

.structured-table th:first-child,
.structured-table td:first-child {
  border-left: 0;
}

.structured-table th {
  background: var(--surface-muted);
  color: var(--text-strong);
  font-weight: 800;
}

.structured-table tr:last-child td {
  border-bottom: 0;
}

.structured-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.structured-list li {
  padding: 12px 14px;
  border-radius: 12px;
  background: var(--surface-muted);
}
</style>
