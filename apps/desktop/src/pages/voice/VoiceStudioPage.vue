<template>
  <ProjectContextGuard>
    <PagePlaceholderState
      title="配音中心"
      route-id="voice_studio"
      page-type="editor"
      description="生成 TTS 配音、管理音色版本，输出与时间线对齐的音轨。"
    />
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import PagePlaceholderState from "@/components/PagePlaceholderState.vue";
</script>
