<template>
  <div class="storyboard-structured-preview" data-storyboard-structured-preview>
    <h1>{{ view.title }}</h1>
    <h2>详细分镜表</h2>
    <StoryboardSegmentedTable :groups="groups" />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import {
  buildScriptWorkspaceTableRows,
  type ScriptDocumentJson
} from "@/modules/scripts/script-document-view-model";
import { buildStoryboardViewModel, type StoryboardDocumentJson } from "@/modules/storyboards/storyboard-document-view-model";
import { buildStoryboardShotGroups } from "@/modules/storyboards/storyboard-segment-groups";
import StoryboardSegmentedTable from "@/pages/storyboards/components/StoryboardSegmentedTable.vue";

const props = defineProps<{
  scriptContent?: string;
  scriptDocumentJson?: ScriptDocumentJson | null;
  storyboardJson: StoryboardDocumentJson;
}>();

const view = computed(() => buildStoryboardViewModel(props.storyboardJson));
const scriptRows = computed(() => buildScriptWorkspaceTableRows(props.scriptDocumentJson, props.scriptContent ?? ""));
const groups = computed(() => buildStoryboardShotGroups(view.value.shots, scriptRows.value));
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
