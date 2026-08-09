<template>
  <form class="account-wizard-form" @submit.prevent="submit">
    <label>
      <span>账号名称</span>
      <input
        v-model.trim="form.name"
        maxlength="128"
        autocomplete="off"
        placeholder="例如：效率工具观察"
        @input="emitDirty"
      />
    </label>
    <label>
      <span>TikTok 用户名 <small>可稍后填写</small></span>
      <div class="account-input-prefix">
        <span>@</span>
        <input
          v-model.trim="form.username"
          maxlength="64"
          autocomplete="off"
          placeholder="creator_name"
          @input="emitDirty"
        />
      </div>
    </label>
    <p v-if="validationMessage" class="account-inline-error">
      {{ validationMessage }}
    </p>
    <div class="account-wizard-step-actions">
      <button
        class="account-button is-primary"
        type="submit"
        :disabled="busy || !form.name"
      >
        {{ busy ? "正在创建…" : "创建草稿并继续" }}
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";

import type { AccountDraftInput } from "../../account-management-types";

const props = defineProps<{ busy: boolean }>();
const emit = defineEmits<{
  dirtyChange: [dirty: boolean];
  submit: [input: AccountDraftInput];
}>();

const form = reactive<AccountDraftInput>({ name: "", username: "" });
const validationMessage = ref("");

function submit(): void {
  validationMessage.value = "";
  if (!form.name.trim()) {
    validationMessage.value = "请输入账号名称。";
    return;
  }
  if (
    form.username &&
    !/^[A-Za-z0-9._]{2,64}$/.test(form.username)
  ) {
    validationMessage.value = "用户名需为 2 至 64 位字母、数字、点或下划线。";
    return;
  }
  if (!props.busy) emit("submit", { ...form });
}

function emitDirty(): void {
  emit("dirtyChange", Boolean(form.name || form.username));
}

function reset(): void {
  form.name = "";
  form.username = "";
  validationMessage.value = "";
  emit("dirtyChange", false);
}

function snapshot(): AccountDraftInput {
  return { ...form };
}

defineExpose({ reset, snapshot, submit });
</script>

