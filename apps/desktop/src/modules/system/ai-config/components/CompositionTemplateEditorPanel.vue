<template>
  <form
    v-if="store.draft"
    class="ai-editor-form"
    @submit.prevent="store.saveDraft"
  >
    <header>
      <div>
        <span class="ai-eyebrow">
          {{ store.draft.mode === "create_profile" ? "新合成模板" : "不可变新版本" }}
        </span>
        <h3>{{ store.draft.name || "未命名合成模板" }}</h3>
      </div>
      <button
        class="ai-icon-button"
        type="button"
        aria-label="关闭模板编辑器"
        @click="$emit('close')"
      >
        <span class="material-symbols-outlined">close</span>
      </button>
    </header>

    <div class="ai-form-grid">
      <label v-if="store.draft.mode === 'create_profile'">
        <span>稳定键</span>
        <input
          :value="store.draft.templateKey"
          maxlength="128"
          @input="updateText('templateKey', $event)"
        />
      </label>
      <label v-if="store.draft.mode === 'create_profile'">
        <span>模板类型</span>
        <select :value="store.draft.templateType" @change="updateType">
          <option value="slideshow">图文轮播</option>
          <option value="talking_head">口播</option>
          <option value="product_showcase">产品展示</option>
          <option value="mixed_media">混合媒体</option>
        </select>
      </label>
      <label>
        <span>名称</span>
        <input
          :value="store.draft.name"
          maxlength="100"
          @input="updateText('name', $event)"
        />
      </label>
      <label>
        <span>允许画幅 <small>逗号分隔</small></span>
        <input
          :value="store.draft.aspectRatios"
          @input="updateText('aspectRatios', $event)"
        />
      </label>
    </div>

    <div class="ai-form-grid">
      <label>
        <span>参数 Schema</span>
        <textarea
          class="is-code"
          :value="store.draft.parameterSchema"
          rows="9"
          @input="updateText('parameterSchema', $event)"
        />
      </label>
      <label>
        <span>兼容能力</span>
        <textarea
          class="is-code"
          :value="store.draft.compatibleCapabilities"
          rows="9"
          @input="updateText('compatibleCapabilities', $event)"
        />
      </label>
    </div>
    <label>
      <span>CompositionSpec 骨架</span>
      <textarea
        class="is-code"
        :value="store.draft.compositionSpecTemplate"
        rows="12"
        @input="updateText('compositionSpecTemplate', $event)"
      />
    </label>
    <label>
      <span>受控预览资产引用 <small>可选</small></span>
      <input
        :value="store.draft.previewAssetRef"
        @input="updateText('previewAssetRef', $event)"
      />
    </label>
    <p class="ai-security-note">
      只接受声明式 CompositionSpec；Runtime 会拒绝脚本、Shell、绝对路径和未注册节点。
    </p>

    <footer class="ai-detail-actions">
      <span>保存会创建新版本，并要求重新验证能力依赖。</span>
      <button
        class="ai-button is-primary"
        type="submit"
        :disabled="Boolean(store.busyKey)"
      >
        {{ store.busyKey ? "保存中…" : "创建版本" }}
      </button>
    </footer>
  </form>
</template>

<script setup lang="ts">
import type { CompositionTemplateType } from "@/types/runtime/ai-system";

import type { CompositionTemplateEditorDraft } from "../ai-config-types";
import { useCompositionTemplateStore } from "../composition-template-store";

defineEmits<{ close: [] }>();

const store = useCompositionTemplateStore();

function updateText(
  field: Exclude<
    keyof CompositionTemplateEditorDraft,
    "templateType" | "createdFromVersion" | "mode"
  >,
  event: Event
): void {
  store.updateDraft(field, (event.target as HTMLInputElement).value);
}

function updateType(event: Event): void {
  store.updateDraft(
    "templateType",
    (event.target as HTMLSelectElement).value as CompositionTemplateType
  );
}
</script>
