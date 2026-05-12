<template>
  <section class="panel-shell" data-testid="subtitle-script-table">
    <header class="panel-heading">
      <div>
        <span class="panel-heading__kicker">脚本文案表格</span>
        <strong>{{ rows.length }} 行</strong>
      </div>
      <span class="panel-heading__chip" :data-state="sourceVoiceTrack ? 'ready' : 'pending'">
        {{ sourceVoiceTrack ? "配音已接入" : "待配音" }}
      </span>
    </header>

    <div v-if="rows.length === 0" class="state-surface">
      <strong>暂无可转换的脚本文案。</strong>
      <p>{{ stateMessage }}</p>
    </div>

    <div v-else class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>段号</th>
            <th>时间</th>
            <th>段落目标</th>
            <th>字幕文案</th>
            <th>时间码状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.segmentId">
            <td class="segment-id">{{ row.segmentId }}</td>
            <td>{{ row.time || "待确认" }}</td>
            <td>{{ row.goal || "未标注" }}</td>
            <td>{{ row.subtitle || row.voiceover }}</td>
            <td>
              <span class="timecode-pill" :data-state="sourceVoiceTrack ? 'ready' : 'pending'">
                {{ sourceVoiceTrack ? "跟随配音" : "估算草稿" }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ScriptSubtitleTableRow } from "@/modules/scripts/script-document-view-model";
import type { VoiceTrackDto } from "@/types/runtime";

defineProps<{
  rows: ScriptSubtitleTableRow[];
  sourceVoiceTrack: VoiceTrackDto | null;
  stateMessage: string;
}>();
</script>

<style scoped>
.panel-shell {
  min-height: 0;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
  overflow: hidden;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-heading > div {
  display: grid;
  gap: 4px;
}

.panel-heading__kicker {
  color: var(--text-tertiary);
  font-size: 12px;
}

.panel-heading strong {
  color: var(--brand-primary);
  font-size: 14px;
}

.panel-heading__chip,
.timecode-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.panel-heading__chip[data-state="ready"],
.timecode-pill[data-state="ready"] {
  border-color: color-mix(in srgb, var(--brand-primary) 28%, transparent);
  color: var(--brand-primary);
}

.panel-heading__chip[data-state="pending"],
.timecode-pill[data-state="pending"] {
  border-color: color-mix(in srgb, var(--warning) 28%, transparent);
  color: var(--warning);
}

.table-scroll {
  overflow-x: auto;
}

table {
  width: max-content;
  min-width: 720px;
  border-collapse: collapse;
}

th,
td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.55;
  text-align: left;
  vertical-align: top;
  white-space: normal;
  word-break: normal;
  overflow-wrap: anywhere;
}

th:nth-child(4),
td:nth-child(4) {
  min-width: 260px;
  max-width: 360px;
}

th {
  color: var(--text-tertiary);
  font-weight: 700;
  white-space: nowrap;
}

.segment-id {
  color: var(--brand-primary);
  font-weight: 800;
  white-space: nowrap;
}

.state-surface {
  display: grid;
  gap: 6px;
  padding: 16px;
  margin: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
}

.state-surface strong {
  font-size: 14px;
}

.state-surface p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}
</style>
