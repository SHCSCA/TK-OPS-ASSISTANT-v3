<template>
  <main
    class="ai-system-page"
    :class="{ 'is-compact': compact, 'is-too-narrow': tooNarrow }"
  >
    <header class="ai-system-hero">
      <div>
        <span class="ai-eyebrow">系统级配置</span>
        <h1>AI 与系统设置</h1>
        <p>Provider、模型、能力路由、Prompt 与 Runtime 共用统一配置修订。</p>
      </div>
      <span class="ai-system-hero__badge">
        <span class="material-symbols-outlined">shield_lock</span>
        本地优先
      </span>
    </header>

    <aside v-if="compact" class="ai-compact-warning" role="status">
      <span class="material-symbols-outlined">desktop_windows</span>
      <span>
        <strong>{{ tooNarrow ? "窗口宽度不足" : "紧凑 PC 布局" }}</strong>
        <small>
          {{ tooNarrow
            ? "请将窗口扩展到至少 960px；本页不切换手机导航。"
            : "当前低于 1024px，详情使用覆盖式工作面。" }}
        </small>
      </span>
    </aside>

    <div v-if="pageError" class="ai-inline-feedback is-error" role="alert">
      <span class="material-symbols-outlined">error</span>
      <span>{{ pageError }}</span>
    </div>

    <template v-if="!tooNarrow">
      <nav class="ai-primary-tabs" aria-label="AI 与系统一级分区">
        <button
          type="button"
          :class="{ 'is-active': primary === 'ai' }"
          @click="requestPrimary('ai')"
        >
          <span class="material-symbols-outlined">auto_awesome</span>
          AI 能力
        </button>
        <button
          type="button"
          :class="{ 'is-active': primary === 'runtime' }"
          @click="requestPrimary('runtime')"
        >
          <span class="material-symbols-outlined">dns</span>
          Runtime 与工作区
        </button>
        <button
          type="button"
          :class="{ 'is-active': primary === 'diagnostics' }"
          @click="requestPrimary('diagnostics')"
        >
          <span class="material-symbols-outlined">troubleshoot</span>
          日志与诊断
        </button>
      </nav>

      <nav
        v-if="primary === 'ai'"
        class="ai-secondary-tabs"
        aria-label="AI 能力二级分区"
      >
        <button
          type="button"
          :class="{ 'is-active': surface === 'providers' }"
          @click="requestSurface('providers')"
        >
          Provider
        </button>
        <button
          type="button"
          :class="{ 'is-active': surface === 'models' }"
          @click="requestSurface('models')"
        >
          模型与能力
        </button>
        <button
          type="button"
          :class="{ 'is-active': surface === 'prompts' }"
          @click="requestSurface('prompts')"
        >
          Prompt 模板
        </button>
      </nav>

      <section class="ai-system-workface">
        <ProviderWorkspace
          v-if="primary === 'ai' && surface === 'providers'"
          @open-log="openLog"
        />
        <ModelRouteWorkspace
          v-else-if="primary === 'ai' && surface === 'models'"
          @open-log="openLog"
        />
        <PromptTemplateWorkspace
          v-else-if="primary === 'ai'"
          @open-log="openLog"
        />
        <RuntimeWorkspace
          v-else-if="primary === 'runtime'"
          @open-log="openLog"
        />
        <DiagnosticsWorkspace v-else />
      </section>
    </template>

    <AIUnsavedDialog
      :busy="guardBusy"
      label="AI 系统编辑器"
      :open="guardOpen"
      @cancel="cancelGuard"
      @discard="discardAndContinue"
      @save="saveAndContinue"
    />
  </main>
</template>

<script setup lang="ts">
import AIUnsavedDialog from "@/modules/system/ai-config/components/AIUnsavedDialog.vue";
import DiagnosticsWorkspace from "@/modules/system/ai-config/components/DiagnosticsWorkspace.vue";
import ModelRouteWorkspace from "@/modules/system/ai-config/components/ModelRouteWorkspace.vue";
import PromptTemplateWorkspace from "@/modules/system/ai-config/components/PromptTemplateWorkspace.vue";
import ProviderWorkspace from "@/modules/system/ai-config/components/ProviderWorkspace.vue";
import RuntimeWorkspace from "@/modules/system/ai-config/components/RuntimeWorkspace.vue";

import { useAISystemPage } from "./use-ai-system-page";
import "./ai-system.css";
import "./ai-system-forms.css";
import "./ai-system-compact-theme.css";

const {
  cancelGuard,
  compact,
  discardAndContinue,
  guardBusy,
  guardOpen,
  openLog,
  pageError,
  primary,
  requestPrimary,
  requestSurface,
  saveAndContinue,
  surface,
  tooNarrow
} = useAISystemPage();
</script>
