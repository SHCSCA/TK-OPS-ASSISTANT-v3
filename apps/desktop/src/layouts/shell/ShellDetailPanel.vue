<template>
  <aside class="detail-panel command-detail-panel shell-detail-panel">
    <section class="detail-panel__hero command-detail-panel__hero">
      <p class="detail-panel__label">当前页面</p>
      <h2>{{ pageTitle }}</h2>
      <p>{{ pageSummary }}</p>
    </section>

    <section class="detail-panel__section">
      <p class="detail-panel__label">项目上下文</p>
      <template v-if="projectName">
        <strong>{{ projectName }}</strong>
        <p>项目 ID：{{ projectId }}</p>
        <p>状态：{{ projectStatus }}</p>
      </template>
      <p v-else>尚未选择项目。需要项目上下文的页面会先回到创作总览。</p>
    </section>

    <section class="detail-panel__section">
      <p class="detail-panel__label">运行状态</p>
      <div class="detail-panel__metric">
        <span>Runtime</span>
        <strong>{{ runtimeLabel }}</strong>
      </div>
      <div class="detail-panel__metric">
        <span>模式</span>
        <strong>{{ runtimeMode }}</strong>
      </div>
      <div class="detail-panel__metric">
        <span>版本</span>
        <strong>{{ runtimeVersion }}</strong>
      </div>
    </section>

    <section v-if="showDiagnostics" class="detail-panel__section">
      <p class="detail-panel__label">诊断信息</p>
      <template v-if="diagnostics">
        <p>数据库：{{ diagnostics.databasePath }}</p>
        <p>日志目录：{{ diagnostics.logDir }}</p>
        <p>修订号：{{ diagnostics.revision }}</p>
        <p>健康状态：{{ diagnostics.healthStatus }}</p>
      </template>
      <p v-else>暂无诊断信息。</p>
    </section>

    <section class="detail-panel__section">
      <p class="detail-panel__label">授权摘要</p>
      <p>状态：{{ licenseLabel }}</p>
      <p>机器码：{{ machineCode }}</p>
      <p>绑定：{{ machineBound ? "已绑定" : "未绑定" }}</p>
      <p>授权码：{{ maskedCode }}</p>
    </section>

    <section class="detail-panel__section detail-panel__section--error">
      <p class="detail-panel__label">最近错误</p>
      <p>{{ lastErrorSummary }}</p>
    </section>
  </aside>
</template>

<script setup lang="ts">
import type { RuntimeDiagnostics } from "@/types/runtime";

defineProps<{
  diagnostics: RuntimeDiagnostics | null;
  lastErrorSummary: string;
  licenseLabel: string;
  machineBound: boolean;
  machineCode: string;
  maskedCode: string;
  pageSummary: string;
  pageTitle: string;
  projectId: string;
  projectName: string;
  projectStatus: string;
  runtimeLabel: string;
  runtimeMode: string;
  runtimeVersion: string;
  showDiagnostics: boolean;
}>();
</script>
