<template>
  <section class="settings-page">
    <header class="settings-page__header">
      <div>
        <p class="placeholder-page__eyebrow">Foundation Config Bus</p>
        <h1>AI & System Settings</h1>
      </div>
      <div class="placeholder-page__meta">
        <span class="page-chip">revision {{ settings?.revision ?? "-" }}</span>
        <span class="page-chip page-chip--muted">{{ store.status }}</span>
      </div>
    </header>

    <p v-if="store.error" class="settings-page__error">
      {{ errorSummary }}
    </p>
    <p v-if="capabilityStore.error" class="settings-page__error">
      {{ capabilityErrorSummary }}
    </p>

    <form class="settings-page__grid" @submit.prevent="handleSave">
      <section class="placeholder-card settings-card">
        <h2>Runtime</h2>
        <label class="settings-field">
          <span>Mode</span>
          <input v-model="form.runtime.mode" data-field="runtime.mode" :disabled="isDisabled" />
        </label>
        <label class="settings-field">
          <span>Workspace Root</span>
          <input
            v-model="form.runtime.workspaceRoot"
            data-field="runtime.workspaceRoot"
            :disabled="isDisabled"
          />
        </label>
      </section>

      <section class="placeholder-card settings-card">
        <h2>Paths</h2>
        <label class="settings-field">
          <span>Cache Dir</span>
          <input v-model="form.paths.cacheDir" data-field="paths.cacheDir" :disabled="isDisabled" />
        </label>
        <label class="settings-field">
          <span>Export Dir</span>
          <input
            v-model="form.paths.exportDir"
            data-field="paths.exportDir"
            :disabled="isDisabled"
          />
        </label>
        <label class="settings-field">
          <span>Log Dir</span>
          <input v-model="form.paths.logDir" data-field="paths.logDir" :disabled="isDisabled" />
        </label>
      </section>

      <section class="placeholder-card settings-card">
        <h2>Logging</h2>
        <label class="settings-field">
          <span>Level</span>
          <select v-model="form.logging.level" data-field="logging.level" :disabled="isDisabled">
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>
        </label>
      </section>

      <section class="placeholder-card settings-card">
        <h2>AI</h2>
        <label class="settings-field">
          <span>Provider</span>
          <input v-model="form.ai.provider" data-field="ai.provider" :disabled="isDisabled" />
        </label>
        <label class="settings-field">
          <span>Model</span>
          <input v-model="form.ai.model" data-field="ai.model" :disabled="isDisabled" />
        </label>
        <label class="settings-field">
          <span>Voice</span>
          <input v-model="form.ai.voice" data-field="ai.voice" :disabled="isDisabled" />
        </label>
        <label class="settings-field">
          <span>Subtitle Mode</span>
          <input
            v-model="form.ai.subtitleMode"
            data-field="ai.subtitleMode"
            :disabled="isDisabled"
          />
        </label>
      </section>

      <div class="settings-page__actions">
        <button
          class="settings-page__button"
          type="button"
          data-action="save-settings"
          :disabled="isDisabled"
          @click="handleSave"
        >
          Save settings
        </button>
      </div>

      <section class="placeholder-card settings-card settings-card--wide">
        <div class="editor-card__header">
          <div>
            <h2>AI Capability Center</h2>
            <p class="workspace-page__summary">
              能力级配置是页面调用 AI 的唯一入口，页面只选能力，不再自己拼 provider 和 model。
            </p>
          </div>
          <button
            class="dashboard-list__action"
            type="button"
            data-action="save-capabilities"
            :disabled="isCapabilityDisabled"
            @click="handleSaveCapabilities"
          >
            Save capabilities
          </button>
        </div>

        <div v-if="capabilityForms.length === 0" class="empty-state">
          AI capabilities have not loaded yet.
        </div>
        <div v-else class="capability-grid">
          <article
            v-for="capability in capabilityForms"
            :key="capability.capabilityId"
            class="capability-card"
          >
            <div class="capability-card__header">
              <h3>{{ capability.capabilityId }}</h3>
              <label class="capability-card__toggle">
                <input
                  v-model="capability.enabled"
                  :data-field="`capability.${capability.capabilityId}.enabled`"
                  type="checkbox"
                  :disabled="isCapabilityDisabled"
                />
                enabled
              </label>
            </div>
            <label class="settings-field">
              <span>Provider</span>
              <input
                v-model="capability.provider"
                :data-field="`capability.${capability.capabilityId}.provider`"
                :disabled="isCapabilityDisabled"
              />
            </label>
            <label class="settings-field">
              <span>Model</span>
              <input
                v-model="capability.model"
                :data-field="`capability.${capability.capabilityId}.model`"
                :disabled="isCapabilityDisabled"
              />
            </label>
            <label class="settings-field">
              <span>Agent Role</span>
              <input
                v-model="capability.agentRole"
                :data-field="`capability.${capability.capabilityId}.agentRole`"
                :disabled="isCapabilityDisabled"
              />
            </label>
            <label class="settings-field">
              <span>System Prompt</span>
              <textarea
                v-model="capability.systemPrompt"
                class="editor-textarea editor-textarea--compact"
                :data-field="`capability.${capability.capabilityId}.systemPrompt`"
                :disabled="isCapabilityDisabled"
              />
            </label>
            <label class="settings-field">
              <span>User Prompt Template</span>
              <textarea
                v-model="capability.userPromptTemplate"
                class="editor-textarea editor-textarea--compact"
                :data-field="`capability.${capability.capabilityId}.userPromptTemplate`"
                :disabled="isCapabilityDisabled"
              />
            </label>
          </article>
        </div>
      </section>

      <section class="placeholder-card settings-card settings-card--wide">
        <h2>Provider Status</h2>
        <div class="provider-grid">
          <article
            v-for="provider in capabilityStore.settings?.providers ?? []"
            :key="provider.provider"
            class="provider-card"
            :data-provider-id="provider.provider"
          >
            <h3>{{ provider.label }}</h3>
            <p>{{ provider.provider }}</p>
            <p>{{ provider.configured ? provider.maskedSecret : "Not configured" }}</p>
            <p>{{ provider.supportsTextGeneration ? "Text generation ready" : "Registered only" }}</p>
          </article>
        </div>
      </section>
    </form>
  </section>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, reactive, ref, watch } from "vue";

import { useAICapabilityStore } from "@/stores/ai-capability";
import { useConfigBusStore } from "@/stores/config-bus";
import type {
  AICapabilityConfig,
  AppSettings,
  AppSettingsUpdateInput
} from "@/types/runtime";

const store = useConfigBusStore();
const capabilityStore = useAICapabilityStore();
const { settings } = storeToRefs(store);
const form = reactive<AppSettingsUpdateInput>(createEmptySettingsInput());
const capabilityForms = ref<AICapabilityConfig[]>([]);

const isDisabled = computed(() => store.status === "saving" || settings.value === null);
const isCapabilityDisabled = computed(
  () => capabilityStore.status === "loading" || capabilityStore.status === "saving"
);
const errorSummary = computed(() => {
  if (!store.error) {
    return "";
  }

  return store.error.requestId
    ? `${store.error.message} (${store.error.requestId})`
    : store.error.message;
});
const capabilityErrorSummary = computed(() => {
  if (!capabilityStore.error) {
    return "";
  }

  return capabilityStore.error.requestId
    ? `${capabilityStore.error.message} (${capabilityStore.error.requestId})`
    : capabilityStore.error.message;
});

watch(
  settings,
  (value) => {
    if (!value) {
      return;
    }

    applySettingsToForm(form, value);
  },
  { immediate: true }
);
watch(
  () => capabilityStore.settings,
  (value) => {
    capabilityForms.value = (value?.capabilities ?? []).map((item) => ({ ...item }));
  },
  { immediate: true }
);

onMounted(() => {
  if (capabilityStore.status === "idle") {
    void capabilityStore.load();
  }
});

async function handleSave(): Promise<void> {
  await store.save(cloneSettingsInput(form));
}

async function handleSaveCapabilities(): Promise<void> {
  await capabilityStore.saveCapabilities(
    capabilityForms.value.map((item) => ({ ...item }))
  );
}

function createEmptySettingsInput(): AppSettingsUpdateInput {
  return {
    runtime: {
      mode: "",
      workspaceRoot: ""
    },
    paths: {
      cacheDir: "",
      exportDir: "",
      logDir: ""
    },
    logging: {
      level: "INFO"
    },
    ai: {
      provider: "",
      model: "",
      voice: "",
      subtitleMode: ""
    }
  };
}

function applySettingsToForm(target: AppSettingsUpdateInput, source: AppSettings): void {
  target.runtime.mode = source.runtime.mode;
  target.runtime.workspaceRoot = source.runtime.workspaceRoot;
  target.paths.cacheDir = source.paths.cacheDir;
  target.paths.exportDir = source.paths.exportDir;
  target.paths.logDir = source.paths.logDir;
  target.logging.level = source.logging.level;
  target.ai.provider = source.ai.provider;
  target.ai.model = source.ai.model;
  target.ai.voice = source.ai.voice;
  target.ai.subtitleMode = source.ai.subtitleMode;
}

function cloneSettingsInput(source: AppSettingsUpdateInput): AppSettingsUpdateInput {
  return {
    runtime: {
      mode: source.runtime.mode,
      workspaceRoot: source.runtime.workspaceRoot
    },
    paths: {
      cacheDir: source.paths.cacheDir,
      exportDir: source.paths.exportDir,
      logDir: source.paths.logDir
    },
    logging: {
      level: source.logging.level
    },
    ai: {
      provider: source.ai.provider,
      model: source.ai.model,
      voice: source.ai.voice,
      subtitleMode: source.ai.subtitleMode
    }
  };
}
</script>
