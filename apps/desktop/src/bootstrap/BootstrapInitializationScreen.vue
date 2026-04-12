<template>
  <section class="bootstrap-screen" data-bootstrap-screen="initialization">
    <div class="bootstrap-screen__backdrop" aria-hidden="true" />
    <div class="bootstrap-screen__panel bootstrap-screen__panel--wide">
      <div class="bootstrap-screen__copy">
        <p class="bootstrap-screen__eyebrow">系统初始化</p>
        <h1>授权已完成，继续准备本地工作环境</h1>
        <p class="bootstrap-screen__summary">
          请确认工作区、缓存、导出、日志目录和基础 AI 默认项。保存后会进入创作总览。
        </p>
      </div>

      <p v-if="errorSummary" class="settings-page__error">{{ errorSummary }}</p>

      <form class="initialization-grid" @submit.prevent="handleSave">
        <fieldset class="command-panel settings-card">
          <h2>基础目录</h2>
          <label class="settings-field">
            <span>运行模式</span>
            <input v-model="form.runtime.mode" data-field="runtime.mode" :disabled="isSubmitting" />
          </label>
          <label class="settings-field">
            <span>工作区目录</span>
            <input
              v-model="form.runtime.workspaceRoot"
              data-field="runtime.workspaceRoot"
              :disabled="isSubmitting"
            />
          </label>
          <label class="settings-field">
            <span>缓存目录</span>
            <input v-model="form.paths.cacheDir" data-field="paths.cacheDir" :disabled="isSubmitting" />
          </label>
          <label class="settings-field">
            <span>导出目录</span>
            <input
              v-model="form.paths.exportDir"
              data-field="paths.exportDir"
              :disabled="isSubmitting"
            />
          </label>
          <label class="settings-field">
            <span>日志目录</span>
            <input v-model="form.paths.logDir" data-field="paths.logDir" :disabled="isSubmitting" />
          </label>
        </fieldset>

        <fieldset class="command-panel settings-card">
          <h2>AI 初始配置</h2>
          <label class="settings-field">
            <span>日志级别</span>
            <select v-model="form.logging.level" data-field="logging.level" :disabled="isSubmitting">
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </label>
          <label class="settings-field">
            <span>默认 Provider</span>
            <input v-model="form.ai.provider" data-field="ai.provider" :disabled="isSubmitting" />
          </label>
          <label class="settings-field">
            <span>默认模型</span>
            <input v-model="form.ai.model" data-field="ai.model" :disabled="isSubmitting" />
          </label>
          <label class="settings-field">
            <span>默认音色</span>
            <input v-model="form.ai.voice" data-field="ai.voice" :disabled="isSubmitting" />
          </label>
          <label class="settings-field">
            <span>字幕模式</span>
            <input
              v-model="form.ai.subtitleMode"
              data-field="ai.subtitleMode"
              :disabled="isSubmitting"
            />
          </label>
        </fieldset>

        <div class="bootstrap-screen__actions bootstrap-screen__actions--full">
          <button
            class="settings-page__button"
            type="button"
            data-action="save-bootstrap"
            :disabled="isSubmitting || !configBusStore.settings"
            @click="handleSave"
          >
            保存初始化并进入工作台
          </button>
          <span class="wizard-page__status">保存后将统一写入配置总线，页面不会各自维护配置副本。</span>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, reactive, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  applySettingsToBootstrapForm,
  cloneBootstrapSettingsInput,
  createBootstrapSettingsInput
} from "@/bootstrap/bootstrap-form";
import { useBootstrapStore } from "@/stores/bootstrap";
import { useConfigBusStore } from "@/stores/config-bus";

const bootstrapStore = useBootstrapStore();
const configBusStore = useConfigBusStore();
const { settings } = storeToRefs(configBusStore);
const form = reactive(createBootstrapSettingsInput());
const route = useRoute();
const router = useRouter();

const isSubmitting = computed(() => configBusStore.status === "saving");
const errorSummary = computed(() => {
  if (!configBusStore.error) {
    return "";
  }

  return configBusStore.error.requestId
    ? `${configBusStore.error.message}（${configBusStore.error.requestId}）`
    : configBusStore.error.message;
});

watch(
  settings,
  (value) => {
    if (value) {
      applySettingsToBootstrapForm(form, value);
    }
  },
  { immediate: true }
);

async function handleSave(): Promise<void> {
  const ready = await bootstrapStore.completeInitialization(
    cloneBootstrapSettingsInput(form)
  );

  if (!ready) {
    return;
  }

  await router.replace(resolveRedirectTarget(route.query.redirect));
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
</script>
