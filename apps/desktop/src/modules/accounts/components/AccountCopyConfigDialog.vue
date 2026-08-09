<template>
  <div v-if="open && target" class="account-modal-backdrop" @click.self="$emit('close')">
    <section class="account-dialog is-wide" role="dialog" aria-modal="true">
      <header>
        <span class="account-dialog__icon material-symbols-outlined">content_copy</span>
        <div>
          <h2>复制配置到 {{ target.name }}</h2>
          <p>只复制明确选择的分区，缺失内容会由 Runtime 标记为跳过。</p>
        </div>
      </header>

      <label class="account-dialog__field">
        <span>来源账号</span>
        <select v-model="sourceAccountId">
          <option value="">选择来源账号</option>
          <option
            v-for="account in sourceAccounts"
            :key="account.id"
            :value="account.id"
          >
            {{ account.name }} · {{ accountStatusLabel(account.status) }}
          </option>
        </select>
      </label>

      <fieldset class="account-copy-sections">
        <legend>复制分区</legend>
        <label v-for="section in ACCOUNT_COPY_SECTIONS" :key="section.id">
          <input
            v-model="sections"
            type="checkbox"
            :value="section.id"
          />
          <span>{{ section.label }}</span>
        </label>
      </fieldset>

      <p v-if="validationMessage" class="account-inline-error">
        {{ validationMessage }}
      </p>

      <footer>
        <button class="account-button is-secondary" type="button" @click="$emit('close')">
          取消
        </button>
        <button
          class="account-button is-primary"
          type="button"
          :disabled="busy"
          @click="submit"
        >
          {{ busy ? "正在复制…" : "开始复制" }}
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { AccountCopySection, AccountDto } from "@/types/runtime/accounts";

import { accountStatusLabel } from "../account-formatters";
import {
  ACCOUNT_COPY_SECTIONS,
  type AccountCopyForm
} from "../account-management-types";

const props = defineProps<{
  accounts: AccountDto[];
  busy: boolean;
  open: boolean;
  target: AccountDto | null;
}>();
const emit = defineEmits<{ close: []; submit: [form: AccountCopyForm] }>();

const sourceAccountId = ref("");
const sections = ref<AccountCopySection[]>([]);
const validationMessage = ref("");
const sourceAccounts = computed(() =>
  props.accounts.filter((account) => account.id !== props.target?.id)
);

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    sourceAccountId.value = "";
    sections.value = [];
    validationMessage.value = "";
  }
);

function submit(): void {
  validationMessage.value = "";
  if (!sourceAccountId.value) {
    validationMessage.value = "请选择来源账号。";
    return;
  }
  if (sections.value.length === 0) {
    validationMessage.value = "至少选择一个可复制分区。";
    return;
  }
  emit("submit", {
    sourceAccountId: sourceAccountId.value,
    sections: [...sections.value]
  });
}
</script>
