<template>
  <div class="structured-table-wrap">
    <table class="structured-table">
      <thead>
        <tr>
          <th v-for="header in headers" :key="header">{{ header }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, rowIndex) in rows" :key="rowIndex">
          <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  headers: string[];
  rows: string[][];
}>();
</script>

<style scoped>
.structured-table-wrap {
  max-width: 100%;
  overflow: auto;
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
}

.structured-table {
  width: 100%;
  min-width: 760px;
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
</style>
