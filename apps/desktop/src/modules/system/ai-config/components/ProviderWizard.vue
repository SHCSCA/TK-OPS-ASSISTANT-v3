<template>
  <div v-if="open" class="ai-modal-backdrop" @click.self="requestClose">
    <section class="ai-provider-wizard" role="dialog" aria-modal="true">
      <header class="ai-dialog-header">
        <div>
          <span class="ai-eyebrow">系统 Provider</span>
          <h2>添加 Provider</h2>
          <p>凭据明文只在当前向导内存中短暂存在。</p>
        </div>
        <button
          class="ai-icon-button"
          type="button"
          aria-label="关闭 Provider 向导"
          :disabled="submitting"
          @click="requestClose"
        >
          <span class="material-symbols-outlined">close</span>
        </button>
      </header>

      <ol class="ai-wizard-steps">
        <li
          v-for="(item, index) in STEPS"
          :key="item"
          :class="{ 'is-active': step === item, 'is-complete': index < stepIndex }"
        >
          <span>{{ index < stepIndex ? "✓" : index + 1 }}</span>
          {{ stepLabel(item) }}
        </li>
      </ol>

      <div v-if="error" class="ai-inline-feedback is-error">
        <span class="material-symbols-outlined">error</span>
        <div>
          <strong>{{ error.message }}</strong>
          <small v-if="error.logId">日志：{{ error.logId }}</small>
        </div>
        <button
          v-if="error.logId"
          class="ai-button is-quiet"
          type="button"
          @click="$emit('openLog', error.logId)"
        >
          查看日志
        </button>
      </div>

      <main class="ai-provider-wizard__body">
        <section v-if="step === 'connection'" class="ai-form-section">
          <h3>1. 连接类型</h3>
          <label>
            <span>Provider 名称</span>
            <input v-model="draft.name" maxlength="80" placeholder="例如：本机文本服务" />
          </label>
          <fieldset class="ai-choice-grid">
            <label v-for="option in adapterOptions" :key="option.value">
              <input v-model="draft.adapterType" type="radio" :value="option.value" />
              <span>
                <strong>{{ option.label }}</strong>
                <small>{{ option.description }}</small>
              </span>
            </label>
          </fieldset>
        </section>

        <section v-else-if="step === 'credential'" class="ai-form-section">
          <h3>2. 地址与凭据</h3>
          <label>
            <span>连接地址</span>
            <input
              v-model="draft.baseUrl"
              inputmode="url"
              placeholder="https://… 或 http://127.0.0.1:…"
            />
          </label>
          <label>
            <span>密钥或 Token <small>本地 Provider 可留空</small></span>
            <input
              v-model="draft.credential"
              type="password"
              autocomplete="new-password"
              placeholder="仅本次输入"
            />
          </label>
          <p class="ai-security-note">
            保存时先写入系统安全存储，再切换数据库引用；读取接口不会返回原文。
          </p>
        </section>

        <section v-else-if="step === 'network'" class="ai-form-section">
          <h3>3. 网络与并发</h3>
          <div class="ai-form-grid">
            <label>
              <span>区域 <small>可选</small></span>
              <input v-model="draft.region" maxlength="64" placeholder="例如 cn-north" />
            </label>
            <label>
              <span>超时（毫秒）</span>
              <input v-model.number="draft.timeoutMs" type="number" min="1000" step="1000" />
            </label>
            <label>
              <span>最大并发</span>
              <input v-model.number="draft.maxConcurrency" type="number" min="1" max="64" />
            </label>
          </div>
          <p class="ai-security-note">
            协议、重定向、响应体大小和本地网络范围仍由 Runtime 配置总线校验。
          </p>
        </section>

        <section v-else-if="step === 'models'" class="ai-form-section">
          <h3>4. 模型发现或手动录入</h3>
          <fieldset class="ai-choice-grid is-two">
            <label>
              <input v-model="draft.modelMode" type="radio" value="discover" />
              <span>
                <strong>发现模型</strong>
                <small>保存后提交可取消的发现任务。</small>
              </span>
            </label>
            <label>
              <input v-model="draft.modelMode" type="radio" value="manual" />
              <span>
                <strong>手动录入</strong>
                <small>只登记真实 Provider 返回的模型 ID。</small>
              </span>
            </label>
          </fieldset>
          <div v-if="draft.modelMode === 'manual'" class="ai-form-grid">
            <label>
              <span>模型 ID</span>
              <input v-model="draft.modelId" maxlength="128" />
            </label>
            <label>
              <span>显示名称</span>
              <input v-model="draft.modelDisplayName" maxlength="80" />
            </label>
          </div>
        </section>

        <section v-else class="ai-form-section">
          <h3>5. 测试并保存</h3>
          <dl class="ai-summary-list">
            <div><dt>名称</dt><dd>{{ draft.name || "未填写" }}</dd></div>
            <div><dt>适配方式</dt><dd>{{ providerAdapterLabel(draft.adapterType) }}</dd></div>
            <div><dt>地址</dt><dd>{{ draft.baseUrl || "未填写" }}</dd></div>
            <div>
              <dt>凭据</dt>
              <dd>
                {{ savedProvider?.credentialSummary.configured
                  ? "已写入安全存储"
                  : draft.credential
                    ? "将在安全存储中写入"
                    : "未提供" }}
              </dd>
            </div>
            <div><dt>模型</dt><dd>{{ draft.modelMode === "discover" ? "发现任务" : draft.modelId }}</dd></div>
          </dl>
          <p class="ai-security-note">
            Provider 会先保存为禁用配置。连接健康与能力契约验证通过后，才能允许 Route 使用。
          </p>
          <AISystemTaskBanner
            :task="task"
            :task-label="
              task?.taskType === 'provider.model_discovery'
                ? '模型发现'
                : 'Provider 连接检查'
            "
            @cancel="cancelTask"
            @open-log="$emit('openLog', $event)"
            @refresh="refreshTask"
          />
          <p v-if="pendingDiscovery" class="ai-security-note">
            连接检查成功后才会串行提交模型发现；失败或取消不会继续。
          </p>
          <div v-if="submitted && !error" class="ai-inline-feedback is-success">
            <span class="material-symbols-outlined">check_circle</span>
            <span>配置已安全保存；请等待任务完成后再启用。</span>
          </div>
        </section>
      </main>

      <footer class="ai-dialog-footer">
        <button
          v-if="canGoBack && !submitted"
          class="ai-button is-quiet"
          type="button"
          @click="back"
        >
          上一步
        </button>
        <span class="ai-dialog-footer__spacer" />
        <button
          v-if="step !== 'verify'"
          class="ai-button is-primary"
          type="button"
          :disabled="!canGoNext"
          @click="next"
        >
          下一步
        </button>
        <button
          v-else-if="!submitted"
          class="ai-button is-primary"
          type="button"
          :disabled="submitting"
          @click="submit"
        >
          {{ submitting ? "安全保存中…" : "保存并提交测试" }}
        </button>
        <button
          v-else
          class="ai-button is-primary"
          type="button"
          @click="requestClose"
        >
          完成
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { toRef } from "vue";

import type {
  ProviderAdapterType,
  ProviderDto
} from "@/types/runtime/ai-system";

import { providerAdapterLabel } from "../ai-config-helpers";
import type { ProviderWizardStep } from "../ai-config-types";
import { useProviderWizard } from "../use-provider-wizard";
import AISystemTaskBanner from "./AISystemTaskBanner.vue";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{
  close: [];
  openLog: [logId: string];
  saved: [provider: ProviderDto];
}>();

const wizard = useProviderWizard(
  toRef(props, "open"),
  (provider) => emit("saved", provider)
);
const {
  STEPS,
  back,
  canGoBack,
  canGoNext,
  cancelTask,
  draft,
  error,
  next,
  pendingDiscovery,
  refreshTask,
  savedProvider,
  step,
  stepIndex,
  submit,
  submitted,
  submitting,
  task
} = wizard;

const adapterOptions: Array<{
  value: ProviderAdapterType;
  label: string;
  description: string;
}> = [
  { value: "direct_api", label: "Direct API", description: "供应商原生协议适配。" },
  { value: "openai_compatible", label: "OpenAI-compatible", description: "兼容 Chat Completions 风格接口。" },
  { value: "comfyui", label: "ComfyUI", description: "受控本地工作流服务。" },
  { value: "runninghub", label: "RunningHub", description: "托管工作流连接。" }
];

function stepLabel(value: ProviderWizardStep): string {
  return {
    connection: "连接类型",
    credential: "地址凭据",
    network: "网络并发",
    models: "模型",
    verify: "测试保存"
  }[value];
}

function requestClose(): void {
  if (!submitting.value) emit("close");
}
</script>
