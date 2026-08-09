<template>
  <aside v-if="account" class="account-detail" :data-account-id="account.id">
    <header class="account-detail__header">
      <div class="account-identity">
        <span class="account-avatar is-large">{{ accountInitial(account) }}</span>
        <span>
          <strong>{{ account.name }}</strong>
          <small>{{ accountIdentityLabel(account) }}</small>
        </span>
      </div>
      <button
        class="account-icon-button"
        type="button"
        aria-label="关闭账号详情"
        @click="$emit('close')"
      >
        <span class="material-symbols-outlined">close</span>
      </button>
    </header>

    <nav class="account-detail__tabs" aria-label="账号详情">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        :class="{ 'is-active': activeTab === tab.id }"
        @click="$emit('update:activeTab', tab.id)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <div class="account-detail__body">
      <section v-if="activeTab === 'overview'" class="account-detail-grid">
        <DetailItem label="生命周期" :value="accountStatusLabel(account.status)" />
        <DetailItem
          label="推荐动作"
          :value="account.readiness.suggestedAction?.label ?? '暂无待办'"
        />
        <DetailItem
          label="最近使用"
          :value="formatAccountDate(account.lastUsedAt)"
        />
        <DetailItem
          label="向导"
          :value="account.wizardCompletedAt ? '已完成' : '未完成'"
        />
      </section>

      <section v-else-if="activeTab === 'identity'" class="account-detail-section">
        <dl>
          <div><dt>平台</dt><dd>TikTok</dd></div>
          <div><dt>账号名</dt><dd>{{ account.name }}</dd></div>
          <div><dt>用户名</dt><dd>{{ accountIdentityLabel(account) }}</dd></div>
          <div>
            <dt>定位摘要</dt>
            <dd>{{ account.positioningSummary || "尚未配置" }}</dd>
          </div>
        </dl>
        <p class="account-detail-note">
          身份编辑和头像资产将在账号编辑契约落地后开放，当前不会写入本地假值。
        </p>
      </section>

      <section
        v-else-if="activeTab === 'connection'"
        class="account-readiness-detail"
      >
        <ReadinessRow
          label="执行连接"
          :item="account.readiness.connection"
          @open-log="$emit('openLog', $event)"
        />
        <ReadinessRow
          label="账号知识"
          :item="account.readiness.knowledge"
          @open-log="$emit('openLog', $event)"
        />
      </section>

      <AccountAIRecipePanel
        v-else-if="activeTab === 'ai_recipe'"
        :account-id="account.id"
        mode="compact"
        :restricted="account.status === 'archived'"
        @activated="$emit('recipeUpdated', account.id)"
        @open-log="$emit('openLog', $event)"
        @version-saved="$emit('recipeUpdated', account.id)"
      />

      <section
        v-else-if="activeTab === 'archive'"
        class="account-detail-section"
      >
        <dl>
          <div><dt>账号修订</dt><dd>{{ account.revision }}</dd></div>
          <div>
            <dt>归档状态</dt>
            <dd>{{ account.status === "archived" ? "已归档" : "使用中" }}</dd>
          </div>
        </dl>
        <p class="account-detail-note">
          归档保留账号数据；恢复会先提交真实健康复检任务，不会直接伪造就绪状态。
        </p>
      </section>
    </div>

    <footer class="account-detail__actions">
      <button
        v-if="account.status !== 'archived'"
        class="account-button is-secondary"
        type="button"
        :disabled="busy"
        @click="$emit('health', account)"
      >
        健康检查
      </button>
      <button
        v-if="account.status === 'draft'"
        class="account-button is-secondary"
        type="button"
        :disabled="busy"
        @click="$emit('copy', account)"
      >
        复制配置
      </button>
      <button
        v-if="account.status === 'archived'"
        class="account-button is-primary"
        type="button"
        :disabled="busy"
        @click="$emit('restore', account)"
      >
        提交恢复
      </button>
      <button
        v-else
        class="account-button is-danger"
        type="button"
        :disabled="busy"
        @click="$emit('archive', account)"
      >
        归档
      </button>
    </footer>
  </aside>
</template>

<script setup lang="ts">
import AccountAIRecipePanel from "@/modules/ai-recipes/components/AccountAIRecipePanel.vue";
import type { AccountDto } from "@/types/runtime/accounts";

import {
  accountIdentityLabel,
  accountInitial,
  accountStatusLabel,
  formatAccountDate
} from "../account-formatters";
import type { AccountDetailTab } from "../account-management-types";
import DetailItem from "./AccountDetailItem.vue";
import ReadinessRow from "./AccountReadinessRow.vue";

withDefaults(defineProps<{
  account: AccountDto | null;
  activeTab?: AccountDetailTab;
  busy: boolean;
}>(), {
  activeTab: "overview"
});

defineEmits<{
  "update:activeTab": [tab: AccountDetailTab];
  archive: [account: AccountDto];
  close: [];
  copy: [account: AccountDto];
  health: [account: AccountDto];
  openLog: [logId: string];
  recipeUpdated: [accountId: string];
  restore: [account: AccountDto];
}>();

const tabs: Array<{ id: AccountDetailTab; label: string }> = [
  { id: "overview", label: "概览" },
  { id: "identity", label: "身份定位" },
  { id: "connection", label: "连接知识" },
  { id: "ai_recipe", label: "AI 创作档案" },
  { id: "archive", label: "数据归档" }
];
</script>
