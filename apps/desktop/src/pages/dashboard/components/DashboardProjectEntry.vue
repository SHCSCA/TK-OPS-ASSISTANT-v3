<template>
  <section
    id="create-project"
    class="command-panel command-panel--primary project-entry-card"
    data-dashboard-section="project-entry"
  >
    <div>
      <p class="detail-panel__label">项目入口</p>
      <h2>创建新的创作项目</h2>
      <p class="workspace-page__summary">
        项目会成为脚本、分镜、时间线、配音、字幕和渲染任务的统一上下文。
      </p>
    </div>

    <label class="settings-field">
      <span>项目名称</span>
      <input
        :value="name"
        data-field="project.name"
        :disabled="isBusy"
        placeholder="例如：TikTok 新品短视频首发"
        @input="$emit('update:name', ($event.target as HTMLInputElement).value)"
      />
    </label>
    <label class="settings-field">
      <span>项目描述</span>
      <textarea
        :value="description"
        data-field="project.description"
        :disabled="isBusy"
        placeholder="写下目标受众、创作方向或需要 AI 优先理解的背景。"
        @input="$emit('update:description', ($event.target as HTMLTextAreaElement).value)"
      />
    </label>
    <button
      class="settings-page__button"
      type="button"
      data-action="create-project"
      :disabled="isBusy || name.trim().length === 0"
      @click="$emit('create')"
    >
      创建并进入主链路
    </button>
  </section>
</template>

<script setup lang="ts">
defineEmits<{
  create: [];
  "update:description": [value: string];
  "update:name": [value: string];
}>();

defineProps<{
  description: string;
  isBusy: boolean;
  name: string;
}>();
</script>
