<template>
  <div class="storyboard-structured-preview" data-storyboard-structured-preview>
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
</style>
