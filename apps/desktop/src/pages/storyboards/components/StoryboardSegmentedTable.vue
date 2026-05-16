<template>
  <div class="storyboard-segmented-table" data-storyboard-segmented-table>
    <section
      v-for="group in groups"
      :key="group.segmentId"
      class="storyboard-segment-group"
      :data-segment-id="group.segmentId"
      data-storyboard-segment-group
    >
      <header class="storyboard-segment-group__header">
        <div class="storyboard-segment-group__meta">
          <strong>{{ group.segmentId }}</strong>
          <span>{{ group.segmentTime }}</span>
        </div>
        <p>{{ group.segmentSummary }}</p>
      </header>

      <div class="storyboard-segmented-table__scroll">
        <table>
          <thead>
            <tr>
              <th v-for="header in headers" :key="header">{{ header }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in group.rows"
              :key="row.shot.shotId"
              :data-time-status="row.timeStatus"
            >
              <td>{{ row.shot.shotId }}</td>
              <td>{{ row.shot.segmentId || group.segmentId }}</td>
              <td>
                <span class="storyboard-segmented-table__cell-text">{{ row.shot.time }}</span>
                <span
                  v-if="row.timeMessage"
                  class="storyboard-segmented-table__warning"
                  data-storyboard-shot-warning
                >
                  {{ row.timeMessage }}
                </span>
              </td>
              <td>{{ row.shot.shotSize }}</td>
              <td><span class="storyboard-segmented-table__cell-text">{{ row.shot.visualContent }}</span></td>
              <td><span class="storyboard-segmented-table__cell-text">{{ row.shot.action }}</span></td>
              <td><span class="storyboard-segmented-table__cell-text">{{ row.shot.cameraAngle }}</span></td>
              <td><span class="storyboard-segmented-table__cell-text">{{ row.shot.cameraMovement }}</span></td>
              <td><span class="storyboard-segmented-table__cell-text">{{ row.shot.voiceover || "无新增口播" }}</span></td>
              <td><span class="storyboard-segmented-table__cell-text">{{ row.shot.subtitle || "无新增字幕" }}</span></td>
              <td><span class="storyboard-segmented-table__cell-text">{{ row.shot.audio }}</span></td>
              <td><span class="storyboard-segmented-table__cell-text">{{ row.shot.shootingNote }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { StoryboardSegmentGroup } from "@/modules/storyboards/storyboard-segment-groups";

defineProps<{
  groups: StoryboardSegmentGroup[];
}>();

const headers = [
  "镜头",
  "对应段落",
  "时间",
  "景别",
  "画面内容",
  "人物动作",
  "镜头角度",
  "运镜方式",
  "口播文案",
  "屏幕字幕",
  "音效/BGM",
  "拍摄注意"
];
</script>

<style scoped>
.storyboard-segmented-table {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.storyboard-segment-group {
  display: grid;
  gap: 10px;
  min-width: 0;
  padding-top: 16px;
  border-top: 1px solid var(--border-subtle);
}

.storyboard-segment-group:first-child {
  padding-top: 0;
  border-top: 0;
}

.storyboard-segment-group__header {
  display: grid;
  grid-template-columns: minmax(96px, 150px) minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.storyboard-segment-group__meta {
  display: flex;
  gap: 8px;
  align-items: center;
  color: var(--text-muted);
  font-size: 0.86rem;
}

.storyboard-segment-group__meta strong {
  color: var(--brand-primary);
  font-weight: 800;
}

.storyboard-segment-group__header p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: var(--text-secondary);
  line-height: 1.6;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.storyboard-segmented-table__scroll {
  max-width: 100%;
  overflow: auto;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
}

.storyboard-segmented-table table {
  width: max-content;
  min-width: 1380px;
  border-collapse: collapse;
  background: var(--surface-raised);
}

.storyboard-segmented-table th,
.storyboard-segmented-table td {
  min-width: 88px;
  max-width: 260px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-subtle);
  border-left: 1px solid var(--border-subtle);
  text-align: left;
  vertical-align: top;
  white-space: normal;
  word-break: normal;
}

.storyboard-segmented-table th:first-child,
.storyboard-segmented-table td:first-child {
  border-left: 0;
}

.storyboard-segmented-table th {
  background: var(--surface-muted);
  color: var(--text-strong);
  font-weight: 800;
}

.storyboard-segmented-table td:nth-child(1),
.storyboard-segmented-table th:nth-child(1),
.storyboard-segmented-table td:nth-child(2),
.storyboard-segmented-table th:nth-child(2),
.storyboard-segmented-table td:nth-child(3),
.storyboard-segmented-table th:nth-child(3),
.storyboard-segmented-table td:nth-child(4),
.storyboard-segmented-table th:nth-child(4) {
  max-width: 120px;
  min-width: 84px;
}

.storyboard-segmented-table td:nth-child(5),
.storyboard-segmented-table th:nth-child(5),
.storyboard-segmented-table td:nth-child(6),
.storyboard-segmented-table th:nth-child(6),
.storyboard-segmented-table td:nth-child(9),
.storyboard-segmented-table th:nth-child(9),
.storyboard-segmented-table td:nth-child(10),
.storyboard-segmented-table th:nth-child(10),
.storyboard-segmented-table td:nth-child(12),
.storyboard-segmented-table th:nth-child(12) {
  min-width: 210px;
}

.storyboard-segmented-table tr:last-child td {
  border-bottom: 0;
}

.storyboard-segmented-table tr[data-time-status="outside"] td {
  background: color-mix(in srgb, var(--color-warning) 7%, var(--surface-raised));
}

.storyboard-segmented-table__cell-text {
  display: -webkit-box;
  overflow: hidden;
  line-height: 1.55;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.storyboard-segmented-table__warning {
  display: block;
  margin-top: 6px;
  color: var(--color-warning);
  font-size: 0.76rem;
  font-weight: 700;
  line-height: 1.45;
}

@media (max-width: 980px) {
  .storyboard-segment-group__header {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
