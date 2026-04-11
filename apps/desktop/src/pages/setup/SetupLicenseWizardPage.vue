<template>
  <section class="settings-page wizard-page">
    <header class="settings-page__header">
      <div>
        <p class="placeholder-page__eyebrow">Setup Wizard</p>
        <h1>License Activation</h1>
      </div>
      <div class="placeholder-page__meta">
        <span class="page-chip" data-license-state>{{ licenseStateLabel }}</span>
        <span class="page-chip page-chip--muted">{{ licenseStore.machineId || "pending" }}</span>
      </div>
    </header>

    <p v-if="submissionError" class="settings-page__error">
      {{ submissionError }}
    </p>

    <form class="settings-page__grid" @submit.prevent="handleActivate">
      <section class="placeholder-card settings-card">
        <h2>License</h2>
        <label class="settings-field">
          <span>Activation Code</span>
          <input
            v-model="activationCode"
            data-field="activationCode"
            :disabled="isSubmitting"
          />
        </label>
        <p>Machine ID: {{ licenseStore.machineId || "pending" }}</p>
        <p>Current state: {{ licenseStateLabel }}</p>
        <p>Masked code: {{ licenseStore.maskedCode || "not activated" }}</p>
      </section>

      <section class="placeholder-card settings-card">
        <h2>Directories</h2>
        <label class="settings-field">
          <span>Runtime Mode</span>
          <input v-model="form.runtime.mode" data-field="runtime.mode" :disabled="isSubmitting" />
        </label>
        <label class="settings-field">
          <span>Workspace Root</span>
          <input
            v-model="form.runtime.workspaceRoot"
            data-field="runtime.workspaceRoot"
            :disabled="isSubmitting"
          />
        </label>
        <label class="settings-field">
          <span>Cache Dir</span>
          <input v-model="form.paths.cacheDir" data-field="paths.cacheDir" :disabled="isSubmitting" />
        </label>
        <label class="settings-field">
          <span>Export Dir</span>
          <input
            v-model="form.paths.exportDir"
            data-field="paths.exportDir"
            :disabled="isSubmitting"
          />
        </label>
        <label class="settings-field">
          <span>Log Dir</span>
          <input v-model="form.paths.logDir" data-field="paths.logDir" :disabled="isSubmitting" />
        </label>
      </section>

      <section class="placeholder-card settings-card">
        <h2>Initial AI Defaults</h2>
        <label class="settings-field">
          <span>Logging Level</span>
          <select v-model="form.logging.level" data-field="logging.level" :disabled="isSubmitting">
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>
        </label>
        <label class="settings-field">
          <span>Provider</span>
          <input v-model="form.ai.provider" data-field="ai.provider" :disabled="isSubmitting" />
        </label>
        <label class="settings-field">
          <span>Model</span>
          <input v-model="form.ai.model" data-field="ai.model" :disabled="isSubmitting" />
        </label>
        <label class="settings-field">
          <span>Voice</span>
          <input v-model="form.ai.voice" data-field="ai.voice" :disabled="isSubmitting" />
        </label>
        <label class="settings-field">
          <span>Subtitle Mode</span>
          <input
            v-model="form.ai.subtitleMode"
            data-field="ai.subtitleMode"
            :disabled="isSubmitting"
          />
        </label>
      </section>

      <div class="settings-page__actions">
        <button
          class="settings-page__button"
          type="button"
          data-action="activate-license"
          :disabled="isSubmitting || !configBusStore.settings"
          @click="handleActivate"
        >
          Activate and continue
        </button>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useConfigBusStore } from "@/stores/config-bus";
import { useLicenseStore } from "@/stores/license";
import type { AppSettings, AppSettingsUpdateInput } from "@/types/runtime";

const configBusStore = useConfigBusStore();
const licenseStore = useLicenseStore();
const { settings } = storeToRefs(configBusStore);
const activationCode = ref("");
const form = reactive<AppSettingsUpdateInput>(createEmptySettingsInput());
const route = useRoute();
const router = useRouter();

const isSubmitting = computed(() => {
  return licenseStore.status === "submitting" || configBusStore.status === "saving";
});
const licenseStateLabel = computed(() => {
  return licenseStore.active ? "License active" : "License restricted";
});
const submissionError = computed(() => {
  if (licenseStore.error) {
    return licenseStore.error.requestId
      ? `${licenseStore.error.message} (${licenseStore.error.requestId})`
      : licenseStore.error.message;
  }

  if (configBusStore.error) {
    return configBusStore.error.requestId
      ? `${configBusStore.error.message} (${configBusStore.error.requestId})`
      : configBusStore.error.message;
  }

  return "";
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

async function handleActivate(): Promise<void> {
  await licenseStore.activate({ activationCode: activationCode.value });
  if (!licenseStore.active) {
    return;
  }

  await configBusStore.save(cloneSettingsInput(form));
  if (configBusStore.status === "error") {
    return;
  }

  await router.push(resolveRedirectTarget(route.query.redirect));
}

function resolveRedirectTarget(value: unknown): string {
  if (typeof value !== "string" || value.length === 0) {
    return "/dashboard";
  }

  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
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
