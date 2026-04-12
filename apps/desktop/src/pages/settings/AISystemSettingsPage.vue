<template>
  <section class="settings-page">
    <header class="settings-page__header settings-page__header--hero">
      <div>
        <p class="placeholder-page__eyebrow">AI 与系统设置</p>
        <h1>统一配置总线</h1>
        <p class="workspace-page__summary">
          Runtime、目录、日志和 AI 能力配置都从这里统一维护，页面只消费配置总线。
        </p>
      </div>
      <div class="placeholder-page__meta">
        <span class="page-chip">修订号 {{ settings?.revision ?? "-" }}</span>
        <span class="page-chip page-chip--muted">{{ statusLabel }}</span>
      </div>
    </header>

    <p v-if="store.error" class="settings-page__error">
      {{ errorSummary }}
    </p>
    <p v-if="capabilityStore.error" class="settings-page__error">
      {{ capabilityErrorSummary }}
    </p>

    <form class="settings-page__grid" @submit.prevent="handleSave">
      <section class="command-panel settings-card">
        <h2>Runtime</h2>
        <label class="settings-field">
          <span>运行模式</span>
          <input v-model="form.runtime.mode" data-field="runtime.mode" :disabled="isDisabled" />
        </label>
        <label class="settings-field">
          <span>工作区目录</span>
          <input
            v-model="form.runtime.workspaceRoot"
            data-field="runtime.workspaceRoot"
            :disabled="isDisabled"
          />
        </label>
      </section>

      <section class="command-panel settings-card">
        <h2>路径配置</h2>
        <label class="settings-field">
          <span>缓存目录</span>
          <input v-model="form.paths.cacheDir" data-field="paths.cacheDir" :disabled="isDisabled" />
        </label>
        <label class="settings-field">
          <span>导出目录</span>
          <input
            v-model="form.paths.exportDir"
            data-field="paths.exportDir"
            :disabled="isDisabled"
          />
        </label>
        <label class="settings-field">
          <span>日志目录</span>
          <input v-model="form.paths.logDir" data-field="paths.logDir" :disabled="isDisabled" />
        </label>
      </section>

      <section class="command-panel settings-card">
        <h2>日志</h2>
        <label class="settings-field">
          <span>日志级别</span>
          <select v-model="form.logging.level" data-field="logging.level" :disabled="isDisabled">
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>
        </label>
      </section>

      <section class="command-panel settings-card">
        <h2>AI 默认项</h2>
        <label class="settings-field">
          <span>默认 Provider</span>
          <input v-model="form.ai.provider" data-field="ai.provider" :disabled="isDisabled" />
        </label>
        <label class="settings-field">
          <span>默认模型</span>
          <input v-model="form.ai.model" data-field="ai.model" :disabled="isDisabled" />
        </label>
        <label class="settings-field">
          <span>默认音色</span>
          <input v-model="form.ai.voice" data-field="ai.voice" :disabled="isDisabled" />
        </label>
        <label class="settings-field">
          <span>字幕模式</span>
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
          保存系统配置
        </button>
      </div>

      <section class="command-panel settings-card settings-card--wide">
        <div class="editor-card__header">
          <div>
            <p class="detail-panel__label">AI 能力中心</p>
            <h2>按能力管理 Provider、模型和提示词</h2>
            <p class="workspace-page__summary">
              能力级配置是页面调用 AI 的唯一入口。页面只选择能力，不直接拼接 Provider、模型或提示词。
            </p>
          </div>
          <button
            class="dashboard-list__action"
            type="button"
            data-action="save-capabilities"
            :disabled="isCapabilityDisabled"
            @click="handleSaveCapabilities"
          >
            保存能力配置
          </button>
        </div>

        <div v-if="capabilityForms.length === 0" class="empty-state">
          AI 能力配置尚未加载。
        </div>
        <div v-else class="capability-grid">
          <article
            v-for="capability in capabilityForms"
            :key="capability.capabilityId"
            class="capability-card"
          >
            <div class="capability-card__header">
              <div>
                <h3>{{ capabilityLabel(capability.capabilityId) }}</h3>
                <p>{{ capability.capabilityId }}</p>
              </div>
              <label class="capability-card__toggle">
                <input
                  v-model="capability.enabled"
                  :data-field="`capability.${capability.capabilityId}.enabled`"
                  type="checkbox"
                  :disabled="isCapabilityDisabled"
                />
                已启用
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
              <span>模型</span>
              <input
                v-model="capability.model"
                :data-field="`capability.${capability.capabilityId}.model`"
                :disabled="isCapabilityDisabled"
              />
            </label>
            <label class="settings-field">
              <span>Agent 角色</span>
              <input
                v-model="capability.agentRole"
                :data-field="`capability.${capability.capabilityId}.agentRole`"
                :disabled="isCapabilityDisabled"
              />
            </label>
            <label class="settings-field">
              <span>系统提示词</span>
              <textarea
                v-model="capability.systemPrompt"
                class="editor-textarea editor-textarea--compact"
                :data-field="`capability.${capability.capabilityId}.systemPrompt`"
                :disabled="isCapabilityDisabled"
              />
            </label>
            <label class="settings-field">
              <span>用户提示词模板</span>
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

      <section class="command-panel settings-card settings-card--wide">
        <p class="detail-panel__label">Provider 状态</p>
        <h2>凭据与能力摘要</h2>
        <div class="provider-grid">
          <article
            v-for="provider in capabilityStore.settings?.providers ?? []"
            :key="provider.provider"
            class="provider-card"
            :data-provider-id="provider.provider"
          >
            <h3>{{ provider.label }}</h3>
            <p>{{ provider.provider }}</p>
            <p>{{ provider.configured ? provider.maskedSecret : "尚未配置凭据" }}</p>
            <p>{{ provider.supportsTextGeneration ? "文本生成可用" : "仅完成注册" }}</p>
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

const capabilityLabels: Record<string, string> = {
  script_generation: "脚本生成",
  script_rewrite: "脚本改写",
  storyboard_generation: "分镜生成",
  tts_generation: "配音生成",
  subtitle_alignment: "字幕对齐",
  video_generation: "视频生成",
  asset_analysis: "资产分析"
};

const isDisabled = computed(() => store.status === "saving" || settings.value === null);
const isCapabilityDisabled = computed(
  () => capabilityStore.status === "loading" || capabilityStore.status === "saving"
);
const statusLabel = computed(() => {
  switch (store.status) {
    case "loading":
      return "读取中";
    case "saving":
      return "保存中";
    case "ready":
      return "已就绪";
    case "error":
      return "异常";
    default:
      return "待加载";
  }
});
const errorSummary = computed(() => {
  if (!store.error) {
    return "";
  }

  return store.error.requestId
    ? `${store.error.message}（${store.error.requestId}）`
    : store.error.message;
});
const capabilityErrorSummary = computed(() => {
  if (!capabilityStore.error) {
    return "";
  }

  return capabilityStore.error.requestId
    ? `${capabilityStore.error.message}（${capabilityStore.error.requestId}）`
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

function capabilityLabel(capabilityId: string): string {
  return capabilityLabels[capabilityId] ?? capabilityId;
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
