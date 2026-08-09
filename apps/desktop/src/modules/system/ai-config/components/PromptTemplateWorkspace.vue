<template>
  <section class="ai-workspace" aria-labelledby="prompt-heading">
    <header class="ai-workspace-header">
      <div>
        <span class="ai-eyebrow">不可变版本配置</span>
        <h2 id="prompt-heading">Prompt 模板</h2>
        <p>正文按需加载；激活版本只能作为新版本来源。</p>
      </div>
      <button class="ai-button is-quiet" type="button" @click="refreshCurrent">
        刷新
      </button>
    </header>

    <nav class="ai-segmented" aria-label="Prompt 与合成模板">
      <button
        type="button"
        :class="{ 'is-active': mode === 'prompts' }"
        @click="requestMode('prompts')"
      >
        Prompt Profile
      </button>
      <button
        type="button"
        :class="{ 'is-active': mode === 'composition' }"
        @click="requestMode('composition')"
      >
        合成模板
      </button>
    </nav>

    <PromptProfilePanel
      v-if="mode === 'prompts'"
      @open-log="$emit('openLog', $event)"
    />
    <CompositionTemplatePanel
      v-else
      @open-log="$emit('openLog', $event)"
    />

    <AIUnsavedDialog
      :busy="saving"
      :label="mode === 'prompts' ? 'Prompt 编辑器' : '合成模板编辑器'"
      :open="guardOpen"
      @cancel="cancelGuard"
      @discard="discardAndSwitch"
      @save="saveAndSwitch"
    />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import { useCompositionTemplateStore } from "../composition-template-store";
import { usePromptConfigStore } from "../prompt-config-store";
import AIUnsavedDialog from "./AIUnsavedDialog.vue";
import CompositionTemplatePanel from "./CompositionTemplatePanel.vue";
import PromptProfilePanel from "./PromptProfilePanel.vue";

defineEmits<{ openLog: [logId: string] }>();

const promptStore = usePromptConfigStore();
const templateStore = useCompositionTemplateStore();
const mode = ref<"prompts" | "composition">("prompts");
const pendingMode = ref<"prompts" | "composition" | null>(null);
const guardOpen = ref(false);
const saving = ref(false);

onMounted(() => {
  if (promptStore.state === "idle") void promptStore.load();
});

function requestMode(next: "prompts" | "composition"): void {
  if (next === mode.value) return;
  if (currentDirty()) {
    pendingMode.value = next;
    guardOpen.value = true;
    return;
  }
  applyMode(next);
}

function applyMode(next: "prompts" | "composition"): void {
  mode.value = next;
  if (next === "prompts" && promptStore.state === "idle") void promptStore.load();
  if (next === "composition" && templateStore.state === "idle") {
    void templateStore.load();
  }
}

function currentDirty(): boolean {
  return mode.value === "prompts" ? promptStore.dirty : templateStore.dirty;
}

function discardAndSwitch(): void {
  if (mode.value === "prompts") promptStore.discardDraft();
  else templateStore.discardDraft();
  finishGuard();
}

async function saveAndSwitch(): Promise<void> {
  saving.value = true;
  const saved = mode.value === "prompts"
    ? await promptStore.saveDraft()
    : await templateStore.saveDraft();
  saving.value = false;
  if (saved) finishGuard();
}

function finishGuard(): void {
  const next = pendingMode.value;
  cancelGuard();
  if (next) applyMode(next);
}

function cancelGuard(): void {
  guardOpen.value = false;
  pendingMode.value = null;
}

function refreshCurrent(): void {
  if (mode.value === "prompts") void promptStore.load();
  else void templateStore.load();
}
</script>
