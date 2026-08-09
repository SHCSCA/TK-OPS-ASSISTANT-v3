<template>
  <div class="account-wizard-panel">
    <div class="account-health-summary">
      <AccountReadinessCell :readiness="account.readiness" />
      <p>
        {{
          account.readiness.checkedAt
            ? `最近检查：${formatAccountDate(account.readiness.checkedAt)}`
            : "尚未执行完整健康检查"
        }}
      </p>
    </div>
    <div v-if="taskId" class="account-task-note">
      <span class="material-symbols-outlined">pending_actions</span>
      <span>任务 {{ taskId }} 已提交，完成后请刷新真实状态。</span>
    </div>
    <div class="account-wizard-step-actions">
      <button
        class="account-button is-secondary"
        type="button"
        :disabled="busy"
        @click="$emit('refresh')"
      >
        刷新状态
      </button>
      <button
        class="account-button is-primary"
        type="button"
        :disabled="busy"
        @click="$emit('check')"
      >
        {{ busy ? "提交中…" : "运行健康检查" }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AccountDto } from "@/types/runtime/accounts";

import { formatAccountDate } from "../../account-formatters";
import AccountReadinessCell from "../AccountReadinessCell.vue";

defineProps<{ account: AccountDto; busy: boolean; taskId: string | null }>();
defineEmits<{ check: []; refresh: [] }>();
</script>

