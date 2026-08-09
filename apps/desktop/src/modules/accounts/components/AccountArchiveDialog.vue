<template>
  <div v-if="open && account" class="account-modal-backdrop" @click.self="$emit('close')">
    <section class="account-dialog" role="alertdialog" aria-modal="true">
      <header>
        <span class="account-dialog__icon is-danger material-symbols-outlined">
          archive
        </span>
        <div>
          <h2>归档 {{ account.name }}</h2>
          <p>账号内容会保留，但当前工作区和任务将停止使用此账号。</p>
        </div>
      </header>
      <label class="account-dialog__field">
        <span>归档原因 <small>可选</small></span>
        <textarea
          v-model="reason"
          maxlength="512"
          rows="3"
          placeholder="仅用于本地操作记录"
        ></textarea>
      </label>
      <footer>
        <button class="account-button is-secondary" type="button" @click="$emit('close')">
          取消
        </button>
        <button
          class="account-button is-danger"
          type="button"
          :disabled="busy"
          @click="$emit('confirm', reason)"
        >
          {{ busy ? "正在归档…" : "确认归档" }}
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";

import type { AccountDto } from "@/types/runtime/accounts";

const props = defineProps<{
  account: AccountDto | null;
  busy: boolean;
  open: boolean;
}>();

defineEmits<{ close: []; confirm: [reason: string] }>();

const reason = ref("");
watch(
  () => props.open,
  (open) => {
    if (open) reason.value = "";
  }
);
</script>

