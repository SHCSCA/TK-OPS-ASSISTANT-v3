<template>
  <section class="ai-config-editor-layout">
    <aside class="ai-config-rail">
      <header>
        <div>
          <span class="ai-eyebrow">受控自动合成</span>
          <h3>合成模板</h3>
        </div>
        <button
          class="ai-icon-button"
          type="button"
          aria-label="新建合成模板"
          @click="runGuarded(store.beginCreateTemplate)"
        >
          <span class="material-symbols-outlined">add</span>
        </button>
      </header>
      <label class="ai-search">
        <span class="material-symbols-outlined">search</span>
        <input
          v-model="store.search"
          type="search"
          placeholder="搜索合成模板"
          @input="store.recomputeState"
        />
      </label>
      <button
        v-for="template in store.filteredTemplates"
        :key="template.templateKey"
        class="ai-rail-item"
        :class="{ 'is-active': template.templateKey === store.selectedTemplateKey }"
        type="button"
        @click="runGuarded(() => store.selectTemplate(template.templateKey))"
      >
        <span>
          <strong>{{ template.name }}</strong>
          <small>{{ templateTypeLabel(template.templateType) }}</small>
        </span>
        <span>v{{ template.activeVersion ?? "—" }}</span>
      </button>
      <button
        v-if="store.hasFilters"
        class="ai-button is-quiet"
        type="button"
        @click="store.clearFilters"
      >
        清除筛选
      </button>
      <div v-if="store.error" class="ai-inline-feedback is-error">
        <span class="material-symbols-outlined">error</span>
        <span>{{ store.error.message }}</span>
        <button
          v-if="store.error.logId"
          class="ai-icon-button"
          type="button"
          aria-label="打开合成模板错误日志"
          @click="$emit('openLog', store.error.logId)"
        >
          <span class="material-symbols-outlined">receipt_long</span>
        </button>
        <button
          class="ai-icon-button"
          type="button"
          aria-label="关闭合成模板错误"
          @click="store.clearFeedback"
        >
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
    </aside>

    <AIConfigStatePanel
      v-if="
        store.state === 'restricted'
        || (store.state !== 'ready' && store.editorState === 'closed')
      "
      action-label="新建合成模板"
      :error-message="store.error?.message"
      :log-id="store.error?.logId"
      :state="store.state"
      @action="store.beginCreateTemplate"
      @clear-filters="store.clearFilters"
      @open-log="$emit('openLog', $event)"
      @retry="store.load"
    />

    <CompositionTemplateEditorPanel
      v-else-if="store.editorState === 'edit'"
      @close="runGuarded(store.closeEditor)"
    />

    <AIConfigStatePanel
      v-else-if="store.editorState === 'loading_body'"
      state="loading"
    />

    <section v-else-if="store.selectedTemplate" class="ai-version-detail">
      <header>
        <div>
          <span class="ai-eyebrow">合成模板摘要</span>
          <h3>{{ store.selectedTemplate.name }}</h3>
          <p>
            {{ templateTypeLabel(store.selectedTemplate.templateType) }}
            · {{ store.selectedTemplate.referenceCount }} 个 Recipe 引用
          </p>
        </div>
        <button
          class="ai-icon-button"
          type="button"
          aria-label="关闭合成模板详情"
          @click="runGuarded(store.closeEditor)"
        >
          <span class="material-symbols-outlined">close</span>
        </button>
      </header>

      <div class="ai-version-strip">
        <button
          v-for="version in store.selectedTemplate.versions"
          :key="version.version"
          type="button"
          :class="{ 'is-active': version.version === store.selectedVersion }"
          @click="runGuarded(() => store.selectVersion(version.version))"
        >
          v{{ version.version }} <small>{{ version.status }}</small>
        </button>
      </div>

      <div v-if="store.editorState === 'summary'" class="ai-redacted-prompt">
        <span class="material-symbols-outlined">schema</span>
        <div>
          <strong>模板正文按需加载</strong>
          <p>摘要只包含版本、哈希、兼容能力与引用数量。</p>
        </div>
        <button class="ai-button is-primary" type="button" @click="store.openSelectedBody">
          打开模板正文
        </button>
      </div>

      <div v-else-if="store.selectedBody" class="ai-prompt-view">
        <dl class="ai-detail-list">
          <div><dt>状态</dt><dd>{{ store.selectedBody.status }}</dd></div>
          <div><dt>画幅</dt><dd>{{ store.selectedBody.aspectRatios.join("、") }}</dd></div>
          <div><dt>哈希</dt><dd>{{ store.selectedBody.contentHash }}</dd></div>
        </dl>
        <article>
          <h4>CompositionSpec 骨架</h4>
          <pre>{{ JSON.stringify(store.selectedBody.compositionSpecTemplate, null, 2) }}</pre>
        </article>
        <ul v-if="store.selectedValidation?.validationIssues.length" class="ai-issue-list">
          <li
            v-for="issue in store.selectedValidation.validationIssues"
            :key="`${issue.code}-${issue.field}`"
          >
            <strong>{{ issue.code }}</strong>
            <span>{{ issue.message }}</span>
          </li>
        </ul>
        <div class="ai-detail-actions">
          <button class="ai-button is-quiet" type="button" @click="store.beginCreateVersion">
            基于此版本新建
          </button>
          <button
            class="ai-button is-secondary"
            type="button"
            :disabled="Boolean(store.busyKey)"
            @click="store.validateSelectedVersion"
          >
            验证模板
          </button>
          <button
            v-if="store.selectedBody.status !== 'active'"
            class="ai-button is-primary"
            type="button"
            :disabled="Boolean(store.busyKey)"
            @click="store.activateSelectedVersion"
          >
            激活此版本
          </button>
        </div>
      </div>
    </section>

    <section v-else class="ai-editor-placeholder">
      <span class="material-symbols-outlined">movie_edit</span>
      <h3>选择一个合成模板</h3>
      <p>P0 只配置受控模板，不提供手动时间线或任意工作流执行。</p>
    </section>

    <AIUnsavedDialog
      :busy="Boolean(store.busyKey)"
      label="合成模板编辑器"
      :open="guardOpen"
      @cancel="cancelGuard"
      @discard="discardAndContinue"
      @save="saveAndContinue"
    />
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";

import type { CompositionTemplateType } from "@/types/runtime/ai-system";

import { useCompositionTemplateStore } from "../composition-template-store";
import AIConfigStatePanel from "./AIConfigStatePanel.vue";
import AIUnsavedDialog from "./AIUnsavedDialog.vue";
import CompositionTemplateEditorPanel from "./CompositionTemplateEditorPanel.vue";

defineEmits<{ openLog: [logId: string] }>();

const store = useCompositionTemplateStore();
const guardOpen = ref(false);
let pendingAction: (() => void) | null = null;

function runGuarded(action: () => void): void {
  if (!store.dirty) {
    action();
    return;
  }
  pendingAction = action;
  guardOpen.value = true;
}

function cancelGuard(): void {
  guardOpen.value = false;
  pendingAction = null;
}

function discardAndContinue(): void {
  store.discardDraft();
  const action = pendingAction;
  cancelGuard();
  action?.();
}

async function saveAndContinue(): Promise<void> {
  if (!await store.saveDraft()) return;
  const action = pendingAction;
  cancelGuard();
  action?.();
}

function templateTypeLabel(type: CompositionTemplateType): string {
  return {
    slideshow: "图文轮播",
    talking_head: "口播",
    product_showcase: "产品展示",
    mixed_media: "混合媒体"
  }[type];
}
</script>
