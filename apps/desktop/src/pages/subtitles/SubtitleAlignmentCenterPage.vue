<template>
  <ProjectContextGuard>
    <PagePlaceholderState
      title="字幕对齐中心"
      route-id="subtitle_alignment_center"
      page-type="editor"
      description="自动生成字幕、校正时间码，调整样式与节奏。"
    />
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import PagePlaceholderState from "@/components/PagePlaceholderState.vue";
</script>
