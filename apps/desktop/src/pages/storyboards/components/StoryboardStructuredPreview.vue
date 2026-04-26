<template>
  <article class="storyboard-structured-preview" data-storyboard-structured-preview>
    <h1>{{ view.title }}</h1>

    <section class="structured-section">
      <h2>详细分镜表</h2>
      <StructuredTable :headers="view.shotTable.headers" :rows="view.shotTable.rows" />
    </section>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";

import { buildStoryboardViewModel, type StoryboardDocumentJson } from "@/modules/storyboards/storyboard-document-view-model";
import StructuredTable from "@/pages/storyboards/components/StructuredTable.vue";

const props = defineProps<{
  storyboardJson: StoryboardDocumentJson;
}>();

const view = computed(() => buildStoryboardViewModel(props.storyboardJson));
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
</style>
