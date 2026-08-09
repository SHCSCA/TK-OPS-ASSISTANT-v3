<template>
  <section class="ai-config-editor-layout">
    <aside class="ai-config-rail">
      <header>
        <div>
          <span class="ai-eyebrow">版本化 Prompt</span>
          <h3>Prompt 列表</h3>
        </div>
        <button
          class="ai-icon-button"
          type="button"
          aria-label="新建 Prompt"
          @click="runGuarded(store.beginCreateProfile)"
        >
          <span class="material-symbols-outlined">add</span>
        </button>
      </header>
      <label class="ai-search">
        <span class="material-symbols-outlined">search</span>
        <input
          v-model="store.search"
          type="search"
          placeholder="搜索 Prompt"
          @input="store.recomputeState"
        />
      </label>
      <select v-model="store.capabilityFilter" @change="store.recomputeState">
        <option value="">全部能力</option>
        <option v-for="key in AI_CAPABILITY_KEYS" :key="key" :value="key">
          {{ capabilityLabel(key) }}
        </option>
      </select>
      <button
        v-for="profile in store.filteredProfiles"
        :key="profile.profileKey"
        class="ai-rail-item"
        :class="{ 'is-active': profile.profileKey === store.selectedProfileKey }"
        type="button"
        @click="runGuarded(() => store.selectProfile(profile.profileKey))"
      >
        <span>
          <strong>{{ profile.name }}</strong>
          <small>{{ capabilityLabel(profile.capabilityKey) }}</small>
        </span>
        <span>v{{ profile.activeVersion ?? "—" }}</span>
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
          aria-label="打开 Prompt 错误日志"
          @click="$emit('openLog', store.error.logId)"
        >
          <span class="material-symbols-outlined">receipt_long</span>
        </button>
        <button
          class="ai-icon-button"
          type="button"
          aria-label="关闭 Prompt 错误"
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
      action-label="新建 Prompt"
      :error-message="store.error?.message"
      :log-id="store.error?.logId"
      :state="store.state"
      @action="store.beginCreateProfile"
      @clear-filters="store.clearFilters"
      @open-log="$emit('openLog', $event)"
      @retry="store.load"
    />

    <PromptEditorPanel
      v-else-if="store.editorState === 'edit'"
      @close="runGuarded(store.closeEditor)"
    />

    <AIConfigStatePanel
      v-else-if="store.editorState === 'loading_body'"
      state="loading"
    />

    <section
      v-else-if="store.selectedProfile"
      class="ai-version-detail"
    >
      <header>
        <div>
          <span class="ai-eyebrow">Prompt 摘要</span>
          <h3>{{ store.selectedProfile.name }}</h3>
          <p>
            {{ capabilityLabel(store.selectedProfile.capabilityKey) }}
            · {{ store.selectedProfile.referenceCount }} 个引用
          </p>
        </div>
        <button
          class="ai-icon-button"
          type="button"
          aria-label="关闭 Prompt 详情"
          @click="runGuarded(store.closeEditor)"
        >
          <span class="material-symbols-outlined">close</span>
        </button>
      </header>

      <div class="ai-version-strip">
        <button
          v-for="version in store.selectedProfile.versions"
          :key="version.version"
          type="button"
          :class="{ 'is-active': version.version === store.selectedVersion }"
          @click="runGuarded(() => store.selectVersion(version.version))"
        >
          v{{ version.version }}
          <small>{{ version.status }}</small>
        </button>
      </div>

      <div v-if="store.editorState === 'summary'" class="ai-redacted-prompt">
        <span class="material-symbols-outlined">visibility_off</span>
        <div>
          <strong>正文按需加载</strong>
          <p>列表和日志只保留版本、哈希与长度；主动打开后才读取完整 Prompt。</p>
        </div>
        <button
          class="ai-button is-primary"
          type="button"
          @click="store.openSelectedBody"
        >
          打开版本正文
        </button>
      </div>

      <div v-else-if="store.selectedBody" class="ai-prompt-view">
        <dl class="ai-detail-list">
          <div><dt>状态</dt><dd>{{ store.selectedBody.status }}</dd></div>
          <div><dt>哈希</dt><dd>{{ store.selectedBody.contentHash }}</dd></div>
          <div><dt>创建时间</dt><dd>{{ store.selectedBody.createdAt }}</dd></div>
        </dl>
        <article>
          <h4>系统提示</h4>
          <pre>{{ store.selectedBody.systemPrompt }}</pre>
        </article>
        <article>
          <h4>任务模板</h4>
          <pre>{{ store.selectedBody.taskTemplate }}</pre>
        </article>
        <div class="ai-detail-actions">
          <button
            class="ai-button is-secondary"
            type="button"
            @click="store.beginCreateVersion"
          >
            基于此版本新建
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
      <span class="material-symbols-outlined">description</span>
      <h3>选择一个 Prompt</h3>
      <p>正文不会随列表一起加载。</p>
    </section>

    <AIUnsavedDialog
      :busy="Boolean(store.busyKey)"
      label="Prompt 编辑器"
      :open="guardOpen"
      @cancel="cancelGuard"
      @discard="discardAndContinue"
      @save="saveAndContinue"
    />
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { AI_CAPABILITY_KEYS } from "@/types/runtime/ai-system";

import { capabilityLabel } from "../ai-config-helpers";
import { usePromptConfigStore } from "../prompt-config-store";
import AIConfigStatePanel from "./AIConfigStatePanel.vue";
import AIUnsavedDialog from "./AIUnsavedDialog.vue";
import PromptEditorPanel from "./PromptEditorPanel.vue";

defineEmits<{ openLog: [logId: string] }>();

const store = usePromptConfigStore();
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
</script>
