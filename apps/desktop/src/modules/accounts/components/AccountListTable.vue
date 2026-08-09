<template>
  <div class="account-list" :aria-busy="collectionState === 'loading'">
    <div v-if="collectionState === 'loading'" class="account-list-state">
      <span class="account-spinner" aria-hidden="true"></span>
      <p>正在同步账号…</p>
    </div>

    <div v-else-if="collectionState === 'error'" class="account-list-state is-error">
      <span class="material-symbols-outlined" aria-hidden="true">sync_problem</span>
      <strong>账号列表暂时不可用</strong>
      <p>{{ errorMessage }}</p>
      <div class="account-list-state__actions">
        <button
          v-if="errorLogId"
          class="account-button is-secondary"
          type="button"
          @click="openErrorLog"
        >
          查看日志
        </button>
        <button class="account-button is-secondary" type="button" @click="$emit('retry')">
          重试
        </button>
      </div>
    </div>

    <div
      v-else-if="collectionState === 'empty' || collectionState === 'filtered-empty'"
      class="account-list-state"
    >
      <span class="material-symbols-outlined" aria-hidden="true">
        {{ collectionState === "empty" ? "person_add" : "filter_alt_off" }}
      </span>
      <strong>
        {{ collectionState === "empty" ? "还没有 TikTok 账号" : "没有匹配账号" }}
      </strong>
      <p>
        {{
          collectionState === "empty"
            ? "创建账号后，再连接真实执行环境与账号知识。"
            : "调整搜索词或状态筛选后再试。"
        }}
      </p>
      <button
        v-if="collectionState === 'empty'"
        class="account-button is-primary"
        type="button"
        @click="$emit('create')"
      >
        添加账号
      </button>
      <button
        v-else
        class="account-button is-secondary"
        type="button"
        @click="$emit('clearFilters')"
      >
        清除筛选
      </button>
    </div>

    <div v-else class="account-table-scroll">
      <table class="account-table">
        <thead>
          <tr>
            <th>身份</th>
            <th>定位摘要</th>
            <th>三项就绪</th>
            <th>生命周期</th>
            <th>最近使用</th>
            <th>推荐动作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="account in accounts"
            :key="account.id"
            :class="{ 'is-selected': selectedAccountId === account.id }"
            :data-account-id="account.id"
            tabindex="0"
            @click="$emit('select', account.id)"
            @keydown.enter="$emit('select', account.id)"
            @keydown.space.prevent="$emit('select', account.id)"
          >
            <td>
              <div class="account-identity">
                <span class="account-avatar">{{ accountInitial(account) }}</span>
                <span>
                  <strong>{{ account.name }}</strong>
                  <small>{{ accountIdentityLabel(account) }}</small>
                </span>
              </div>
            </td>
            <td>
              <span v-if="account.positioningSummary" class="account-summary">
                {{ account.positioningSummary }}
              </span>
              <span v-else class="account-muted">尚未配置定位</span>
            </td>
            <td><AccountReadinessCell :readiness="account.readiness" /></td>
            <td>
              <span
                class="account-status"
                :class="`is-${accountStatusTone(account.status)}`"
              >
                {{ accountStatusLabel(account.status) }}
              </span>
            </td>
            <td class="account-time">{{ formatAccountDate(account.lastUsedAt) }}</td>
            <td>
              <button
                class="account-text-action"
                type="button"
                @click.stop="$emit('recommendedAction', account)"
              >
                {{ recommendedActionLabel(account) }}
                <span class="material-symbols-outlined" aria-hidden="true">
                  arrow_forward
                </span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import type {
  AccountCollectionState
} from "../account-management-types";
import type { AccountDto } from "@/types/runtime/accounts";

import {
  accountIdentityLabel,
  accountInitial,
  accountStatusLabel,
  accountStatusTone,
  formatAccountDate
} from "../account-formatters";
import AccountReadinessCell from "./AccountReadinessCell.vue";

const props = defineProps<{
  accounts: AccountDto[];
  collectionState: AccountCollectionState;
  errorLogId?: string | null;
  errorMessage?: string;
  selectedAccountId: string | null;
}>();

const emit = defineEmits<{
  clearFilters: [];
  create: [];
  openLog: [logId: string];
  recommendedAction: [account: AccountDto];
  retry: [];
  select: [accountId: string];
}>();

function openErrorLog(): void {
  if (props.errorLogId) emit("openLog", props.errorLogId);
}

function recommendedActionLabel(account: AccountDto): string {
  if (account.status === "archived") return "恢复账号";
  return account.readiness.suggestedAction?.label ?? "查看详情";
}
</script>
