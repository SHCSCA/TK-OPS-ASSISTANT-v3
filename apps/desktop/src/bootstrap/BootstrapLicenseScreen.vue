<template>
  <section class="bootstrap-screen" data-bootstrap-screen="license">
    <div class="bootstrap-screen__backdrop" aria-hidden="true" />
    <div class="bootstrap-screen__panel bootstrap-screen__panel--wide">
      <div class="bootstrap-screen__copy">
        <p class="bootstrap-screen__eyebrow">永久授权</p>
        <h1>当前需要完成永久授权</h1>
        <p class="bootstrap-screen__summary">
          当前机器需要完成一机一码授权。请把本机机器码发送给授权人员，再将返回的授权码粘贴到下方。授权成功后会继续进入系统初始化。
        </p>
      </div>

      <p v-if="errorSummary" class="settings-page__error">{{ errorSummary }}</p>

      <section class="license-panel">
        <div class="wizard-page__machine-code">
          <div>
            <p class="detail-panel__label">本机机器码</p>
            <strong>{{ licenseStore.machineCode || "待生成" }}</strong>
          </div>
          <button
            class="settings-page__button settings-page__button--secondary"
            type="button"
            data-action="copy-machine-code"
            :disabled="!licenseStore.machineCode"
            @click="handleCopyMachineCode"
          >
            {{ copyButtonLabel }}
          </button>
        </div>

        <label class="settings-field">
          <span>授权码</span>
          <textarea
            v-model="activationCode"
            class="editor-textarea editor-textarea--compact"
            data-field="activationCode"
            :disabled="isSubmitting"
            placeholder="请粘贴授权人员生成的授权码"
          />
        </label>

        <div class="bootstrap-screen__actions">
          <button
            class="settings-page__button"
            type="button"
            data-action="activate-license"
            :disabled="isSubmitting || activationCode.trim().length === 0"
            @click="handleActivate"
          >
            完成授权
          </button>
          <span class="wizard-page__status">授权成功后将继续进入系统初始化。</span>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import { useBootstrapStore } from "@/stores/bootstrap";
import { useLicenseStore } from "@/stores/license";

const bootstrapStore = useBootstrapStore();
const licenseStore = useLicenseStore();
const activationCode = ref("");
const copyButtonLabel = ref("复制机器码");

const isSubmitting = computed(() => licenseStore.status === "submitting");
const errorSummary = computed(() => {
  if (!licenseStore.error) {
    return "";
  }

  return licenseStore.error.requestId
    ? `${licenseStore.error.message}（${licenseStore.error.requestId}）`
    : licenseStore.error.message;
});

async function handleActivate(): Promise<void> {
  await bootstrapStore.activateLicense({ activationCode: activationCode.value });
}

async function handleCopyMachineCode(): Promise<void> {
  if (!licenseStore.machineCode) {
    return;
  }

  try {
    await navigator.clipboard.writeText(licenseStore.machineCode);
    copyButtonLabel.value = "已复制";
  } catch {
    copyButtonLabel.value = "复制失败";
  }
}
</script>
