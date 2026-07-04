<template>
  <section
    class="render-workspace-handoff"
    :data-tone="handoff.tone"
    data-testid="render-workspace-handoff"
    aria-labelledby="render-workspace-handoff-title"
  >
    <div class="render-workspace-handoff__icon" aria-hidden="true">
      <span class="material-symbols-outlined">{{ handoff.canCreateFromHandoff ? "task_alt" : "warning" }}</span>
    </div>

    <div class="render-workspace-handoff__body">
      <p class="render-workspace-handoff__eyebrow">来自 AI 剪辑工作台</p>
      <h2 id="render-workspace-handoff-title">{{ handoff.title }}</h2>
      <p class="render-workspace-handoff__description">{{ handoff.description }}</p>

      <dl class="render-workspace-handoff__meta">
        <div>
          <dt>项目名称</dt>
          <dd>{{ handoff.projectName }}</dd>
        </div>
        <div>
          <dt>传入项目 ID</dt>
          <dd>{{ handoff.projectId || "未提供" }}</dd>
        </div>
        <div>
          <dt>当前项目</dt>
          <dd>当前项目：{{ handoff.currentProjectId }}</dd>
        </div>
        <div>
          <dt>时间线 ID</dt>
          <dd>{{ handoff.timelineId || "未提供" }}</dd>
        </div>
      </dl>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { RenderWorkspaceHandoffView } from "./renderWorkspaceHandoff";

defineProps<{
  handoff: RenderWorkspaceHandoffView;
}>();
</script>

<style scoped>
.render-workspace-handoff {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
}

.render-workspace-handoff[data-tone="success"] {
  border-color: color-mix(in srgb, var(--color-success) 36%, var(--color-border-default));
  background: color-mix(in srgb, var(--color-success) 8%, var(--color-bg-surface));
}

.render-workspace-handoff[data-tone="warning"] {
  border-color: color-mix(in srgb, var(--color-warning) 44%, var(--color-border-default));
  background: color-mix(in srgb, var(--color-warning) 9%, var(--color-bg-surface));
}

.render-workspace-handoff__icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-sm);
  background: var(--color-bg-muted);
}

.render-workspace-handoff[data-tone="success"] .render-workspace-handoff__icon {
  color: var(--color-success);
}

.render-workspace-handoff[data-tone="warning"] .render-workspace-handoff__icon {
  color: var(--color-warning);
}

.render-workspace-handoff__body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.render-workspace-handoff__eyebrow {
  margin: 0;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.render-workspace-handoff h2 {
  margin: 0;
  font: var(--font-title-md);
  color: var(--color-text-primary);
}

.render-workspace-handoff__description {
  margin: 0;
  font: var(--font-body-sm);
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.render-workspace-handoff__meta {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
}

.render-workspace-handoff__meta div {
  min-width: 0;
  padding: var(--space-3);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-bg-canvas) 74%, transparent);
}

.render-workspace-handoff__meta dt {
  margin: 0 0 4px;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.render-workspace-handoff__meta dd {
  margin: 0;
  font: var(--font-body-md);
  color: var(--color-text-primary);
  overflow-wrap: anywhere;
}

@media (max-width: 980px) {
  .render-workspace-handoff__meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .render-workspace-handoff {
    grid-template-columns: 1fr;
  }

  .render-workspace-handoff__meta {
    grid-template-columns: 1fr;
  }
}
</style>
