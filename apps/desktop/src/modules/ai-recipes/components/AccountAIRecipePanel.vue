<template>
  <section
    class="recipe-panel"
    :class="[`is-${mode}`, { 'is-restricted': restricted }]"
    :data-account-id="accountId"
  >
    <header class="recipe-panel__header">
      <div>
        <span class="recipe-eyebrow">账号级配置</span>
        <h3>AI Recipe</h3>
        <p>系统 Route → 账号覆盖 → 后续批次快照。</p>
      </div>
      <button
        class="recipe-button is-quiet"
        type="button"
        :disabled="restricted"
        @click="store.load(accountId)"
      >
        刷新
      </button>
    </header>

    <div v-if="cache.feedback" class="recipe-feedback is-success">
      <span class="material-symbols-outlined">info</span>
      <span>{{ cache.feedback }}</span>
      <button class="recipe-icon-button" type="button" @click="store.clearFeedback(accountId)">
        <span class="material-symbols-outlined">close</span>
      </button>
    </div>

    <div v-if="cache.error" class="recipe-feedback is-error">
      <span class="material-symbols-outlined">error</span>
      <span>{{ cache.error.message }}</span>
      <button
        v-if="cache.error.logId"
        class="recipe-button is-quiet"
        type="button"
        @click="$emit('openLog', cache.error.logId)"
      >
        查看日志
      </button>
    </div>

    <AIConfigStatePanel
      v-if="showBlockingState"
      :action-label="effectiveState === 'first_use' ? '创建首个 Recipe' : ''"
      :cancellable="false"
      :description="stateDescription"
      :error-message="cache.error?.message"
      :log-id="cache.error?.logId"
      :state="effectiveState"
      @action="store.beginCreateVersion(accountId)"
      @open-log="$emit('openLog', $event)"
      @retry="store.load(accountId)"
    />

    <template v-else>
      <section v-if="cache.recipe" class="recipe-summary">
        <div>
          <small>激活版本</small>
          <strong>{{ cache.recipe.activeVersion ? `v${cache.recipe.activeVersion}` : "未激活" }}</strong>
        </div>
        <div>
          <small>版本数量</small>
          <strong>{{ cache.versions.length }}</strong>
        </div>
        <div>
          <small>配置修订</small>
          <strong>{{ cache.recipe.revision }}</strong>
        </div>
      </section>

      <div
        v-if="effectiveState === 'dependency_blocked'"
        class="recipe-feedback is-warning"
      >
        <span class="material-symbols-outlined">link_off</span>
        <span>当前版本未验证或系统能力依赖已变化，请验证后再激活。</span>
      </div>
      <div
        v-if="effectiveState === 'waiting_external'"
        class="recipe-feedback"
      >
        <span class="material-symbols-outlined">progress_activity</span>
        <span>正在提交 Recipe 版本或验证结果，请勿重复操作。</span>
      </div>

      <AccountAIRecipeEditor
        v-if="cache.editorOpen"
        :account-id="accountId"
        :cache="cache"
        @close="requestCloseEditor"
        @save="saveVersion"
      />

      <template v-else>
        <div class="recipe-version-list">
          <button
            v-for="version in cache.versions"
            :key="version.id"
            type="button"
            :class="{ 'is-active': version.version === selectedVersion?.version }"
            @click="store.selectVersion(accountId, version.version)"
          >
            <span>
              <strong>v{{ version.version }} · {{ version.name }}</strong>
              <small>
                {{ version.status }} · {{ version.validationStatus }}
              </small>
            </span>
            <span>{{ version.sourceAiConfigRevision }}</span>
          </button>
        </div>

        <section v-if="selectedVersion" class="recipe-version-detail">
          <dl>
            <div><dt>状态</dt><dd>{{ selectedVersion.status }}</dd></div>
            <div><dt>验证</dt><dd>{{ selectedVersion.validationStatus }}</dd></div>
            <div><dt>系统 AI 修订</dt><dd>{{ selectedVersion.sourceAiConfigRevision }}</dd></div>
            <div>
              <dt>合成模板</dt>
              <dd>{{ compositionTemplateLabel(selectedVersion.compositionTemplateRef) }}</dd>
            </div>
            <div><dt>内容哈希</dt><dd>{{ selectedVersion.contentHash }}</dd></div>
          </dl>
          <ul v-if="selectedVersion.validationIssues.length" class="recipe-issues">
            <li v-for="issue in selectedVersion.validationIssues" :key="`${issue.code}-${issue.field}`">
              <strong>{{ issue.code }}</strong>
              <span>{{ issue.message }}</span>
            </li>
          </ul>
          <footer>
            <button
              class="recipe-button is-quiet"
              type="button"
              :disabled="Boolean(cache.busyKey)"
              @click="store.beginCreateVersion(accountId, selectedVersion)"
            >
              基于此版本新建
            </button>
            <button
              class="recipe-button is-secondary"
              type="button"
              :disabled="Boolean(cache.busyKey)"
              @click="validateVersion(selectedVersion.version)"
            >
              验证
            </button>
            <button
              v-if="selectedVersion.status !== 'active'"
              class="recipe-button is-primary"
              type="button"
              :disabled="Boolean(cache.busyKey) || selectedVersion.validationStatus !== 'valid'"
              @click="activateVersion(selectedVersion.version)"
            >
              激活
            </button>
          </footer>
        </section>

        <button
          v-if="cache.versions.length"
          class="recipe-button is-secondary recipe-create-button"
          type="button"
          :disabled="restricted"
          @click="store.beginCreateVersion(accountId, selectedVersion)"
        >
          创建新版本
        </button>
      </template>

      <AIExecutionLauncher
        v-if="mode !== 'wizard' && activeRecipeVersion && !cache.editorOpen"
        :account-id="accountId"
        :account-revision="cache.recipe?.revision ?? 0"
        :recipe-version-id="activeRecipeVersion.id"
        :restricted="restricted"
        @open-log="$emit('openLog', $event)"
      />
    </template>

    <AIUnsavedDialog
      :busy="Boolean(cache.busyKey)"
      label="账号 AI Recipe"
      :open="guardOpen"
      @cancel="guardOpen = false"
      @discard="discardAndClose"
      @save="saveAndClose"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import AIConfigStatePanel from "@/modules/system/ai-config/components/AIConfigStatePanel.vue";
import AIUnsavedDialog from "@/modules/system/ai-config/components/AIUnsavedDialog.vue";
import AIExecutionLauncher from "@/modules/ai-executions/components/AIExecutionLauncher.vue";

import { useAccountAIRecipeStore } from "../account-ai-recipe-store";
import type {
  AccountAIRecipePanelMode
} from "../account-ai-recipe-types";
import AccountAIRecipeEditor from "./AccountAIRecipeEditor.vue";
import "../styles/account-ai-recipe.css";

const props = withDefaults(defineProps<{
  accountId: string;
  mode?: AccountAIRecipePanelMode;
  restricted?: boolean;
}>(), {
  mode: "full",
  restricted: false
});
const emit = defineEmits<{
  activated: [version: number];
  openLog: [logId: string];
  versionSaved: [version: number];
}>();

const store = useAccountAIRecipeStore();
const guardOpen = ref(false);
const cache = computed(() => store.cache(props.accountId));
const selectedVersion = computed(
  () =>
    cache.value.versions.find(
      (version) => version.version === cache.value.selectedVersion
    )
    ?? cache.value.versions.find(
      (version) => version.version === cache.value.recipe?.activeVersion
    )
    ?? cache.value.versions.at(-1)
    ?? null
);
const activeRecipeVersion = computed(
  () => cache.value.versions.find(
    (version) => version.version === cache.value.recipe?.activeVersion
  ) ?? null
);
const effectiveState = computed(
  () => props.restricted ? "restricted" : cache.value.state
);
const showBlockingState = computed(
  () =>
    ["idle", "loading", "restricted"].includes(effectiveState.value)
    || (
      effectiveState.value === "error"
      && cache.value.recipe === null
    )
    || (
      effectiveState.value === "first_use"
      && !cache.value.editorOpen
    )
);
const stateDescription = computed(() =>
  effectiveState.value === "restricted"
    ? "归档账号不能修改或激活 AI Recipe。"
    : ""
);

watch(
  () => props.accountId,
  (accountId) => {
    void store.load(accountId);
  }
);
onMounted(() => {
  void store.load(props.accountId);
});

function requestCloseEditor(): void {
  if (cache.value.dirty) guardOpen.value = true;
  else store.closeEditor(props.accountId);
}

async function saveVersion(): Promise<void> {
  if (!await store.saveDraft(props.accountId)) return;
  const version = cache.value.selectedVersion;
  if (version !== null) emit("versionSaved", version);
}

async function validateVersion(version: number): Promise<void> {
  await store.validateVersion(props.accountId, version);
}

function compositionTemplateLabel(activeVersionId: string | null): string {
  if (!activeVersionId) return "继承系统默认";
  const template = cache.value.templates.find(
    (item) => item.activeVersionId === activeVersionId
  );
  return template
    ? `${template.name} · v${template.activeVersion}`
    : "引用已失效";
}

async function activateVersion(version: number): Promise<void> {
  if (await store.activateVersion(props.accountId, version)) {
    emit("activated", version);
  }
}

function discardAndClose(): void {
  store.discardDraft(props.accountId);
  guardOpen.value = false;
}

async function saveAndClose(): Promise<void> {
  if (await store.saveDraft(props.accountId)) {
    guardOpen.value = false;
  }
}
</script>
