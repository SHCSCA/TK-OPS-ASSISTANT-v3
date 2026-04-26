<template>
  <article class="storyboard-structured-preview" :data-storyboard-mode="mode" data-storyboard-structured-preview>
    <h1>{{ view.title }}</h1>

    <section v-if="mode === 'preview'" class="structured-section">
      <h2>1. 分镜元信息</h2>
      <StructuredTable :headers="view.infoTable.headers" :rows="view.infoTable.rows" />
    </section>

    <section v-if="mode === 'outline' && view.overviewTable.rows.length" class="structured-section">
      <h2>2. 分镜总览</h2>
      <StructuredTable :headers="view.overviewTable.headers" :rows="view.overviewTable.rows" />
    </section>

    <section v-if="mode === 'list'" class="structured-section">
      <h2>详细分镜表</h2>
      <StructuredTable :headers="view.shotTable.headers" :rows="view.shotTable.rows" />
    </section>

    <section v-if="mode === 'preview'" class="structured-section shot-card-grid">
      <article v-for="shot in view.shots" :key="shot.shotId" class="shot-card">
        <header>
          <span>{{ shot.shotId }}</span>
          <strong>{{ shot.time || "未标注时间" }}</strong>
        </header>
        <h2>{{ shot.visualContent || shot.visualPrompt || "未填写画面内容" }}</h2>
        <dl>
          <div>
            <dt>景别</dt>
            <dd>{{ shot.shotSize || "-" }}</dd>
          </div>
          <div>
            <dt>动作</dt>
            <dd>{{ shot.action || "-" }}</dd>
          </div>
          <div>
            <dt>镜头</dt>
            <dd>{{ [shot.cameraAngle, shot.cameraMovement].filter(Boolean).join(" / ") || "-" }}</dd>
          </div>
          <div>
            <dt>口播/字幕</dt>
            <dd>{{ shot.voiceover || shot.subtitle || "-" }}</dd>
          </div>
        </dl>
      </article>
    </section>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";

import { buildStoryboardViewModel, type StoryboardDocumentJson } from "@/modules/storyboards/storyboard-document-view-model";
import StructuredTable from "@/pages/storyboards/components/StructuredTable.vue";

const props = defineProps<{
  storyboardJson: StoryboardDocumentJson;
  mode?: "list" | "outline" | "preview";
}>();

const view = computed(() => buildStoryboardViewModel(props.storyboardJson));
const mode = computed(() => props.mode ?? "preview");
</script>

<style scoped>
.storyboard-structured-preview {
  color: var(--text-primary);
  font-size: 0.95rem;
  line-height: 1.7;
}

.storyboard-structured-preview h1,
.storyboard-structured-preview h2 {
  margin: 0 0 14px;
  color: var(--text-strong);
  font-weight: 800;
  letter-spacing: -0.02em;
}

.storyboard-structured-preview h1 {
  font-size: clamp(1.6rem, 2.2vw, 2.15rem);
}

.storyboard-structured-preview h2 {
  font-size: 1.2rem;
}

.structured-section {
  margin: 0 0 24px;
}

.shot-card-grid {
  display: grid;
  gap: 14px;
}

.shot-card {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  background: var(--surface-raised);
}

.shot-card header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--text-secondary);
  font-size: 12px;
}

.shot-card header span {
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--surface-muted);
  color: var(--text-strong);
  font-weight: 800;
}

.shot-card h2 {
  margin: 0;
}

.shot-card dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.shot-card dl div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.shot-card dt {
  color: var(--text-secondary);
  font-size: 12px;
}

.shot-card dd {
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--text-primary);
}

@container (max-width: 720px) {
  .shot-card dl {
    grid-template-columns: 1fr;
  }
}
</style>
