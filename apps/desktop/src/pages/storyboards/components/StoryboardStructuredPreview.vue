<template>
  <div class="storyboard-structured-preview" data-storyboard-structured-preview>
    <h1>{{ view.title }}</h1>
    <h2>详细分镜表</h2>
    <StructuredTable :headers="view.shotTable.headers" :rows="view.shotTable.rows" />
  </div>
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
  width: 100%;
  min-width: 0;
}

.storyboard-structured-preview h1,
.storyboard-structured-preview h2 {
  margin: 0 0 14px;
  color: var(--text-strong);
  font-weight: 800;
}

.storyboard-structured-preview h1 {
  font-size: 1.55rem;
  line-height: 1.25;
}

.storyboard-structured-preview h2 {
  font-size: 1.15rem;
}
</style>
