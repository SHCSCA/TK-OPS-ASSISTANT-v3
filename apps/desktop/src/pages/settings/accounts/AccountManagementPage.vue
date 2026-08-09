<template>
  <main class="account-management-page">
    <header class="account-page-header">
      <div>
        <span class="account-eyebrow">系统级</span>
        <h1>账号管理</h1>
        <p>每个账号拥有独立定位、知识、任务与发布上下文。</p>
      </div>
      <button class="account-button is-primary" type="button" @click="openNewWizard">
        <span class="material-symbols-outlined">add</span>
        添加账号
      </button>
    </header>

    <section class="account-management-card">
      <form class="account-toolbar" @submit.prevent="applyFilters">
        <label class="account-search">
          <span class="material-symbols-outlined" aria-hidden="true">search</span>
          <input
            v-model="filterDraft.q"
            type="search"
            maxlength="128"
            placeholder="搜索账号名称或用户名"
          />
        </label>
        <select v-model="filterDraft.status" aria-label="账号状态筛选">
          <option value="">全部状态</option>
          <option value="draft">草稿</option>
          <option value="unbound">未连接</option>
          <option value="ready">就绪</option>
          <option value="attention">需处理</option>
          <option value="archived">已归档</option>
        </select>
        <button class="account-button is-secondary" type="submit">应用</button>
        <button
          v-if="store.hasFilters"
          class="account-text-action"
          type="button"
          @click="clearFilters"
        >
          清除
        </button>
      </form>

      <AccountListTable
        :accounts="accounts"
        :collection-state="collectionState"
        :error-log-id="error?.logId"
        :error-message="error?.message"
        :selected-account-id="selectedAccountId"
        @clear-filters="clearFilters"
        @create="openNewWizard"
        @open-log="showLog"
        @recommended-action="handleRecommendedAction"
        @retry="loadAccounts"
        @select="requestSelectAccount"
      />
    </section>

    <AccountDetailPanel
      v-model:active-tab="detailTab"
      :account="selectedAccount"
      :busy="Boolean(busyKey)"
      @archive="openArchive"
      @close="requestSelectAccount(null)"
      @copy="openCopy"
      @health="runHealth"
      @open-log="showLog"
      @recipe-updated="handleRecipeUpdated"
      @restore="restore"
    />

    <div
      v-if="feedback"
      class="account-feedback"
      :class="`is-${feedback.tone}`"
      role="status"
    >
      <span class="material-symbols-outlined" aria-hidden="true">
        {{ feedback.tone === "error" ? "error" : "check_circle" }}
      </span>
      <span>
        <strong>{{ feedback.message }}</strong>
        <small v-if="feedback.taskId">任务：{{ feedback.taskId }}</small>
        <small v-if="visibleLogId">日志：{{ visibleLogId }}</small>
      </span>
      <button
        v-if="feedback.logId"
        class="account-text-action"
        type="button"
        @click="showLog(feedback.logId)"
      >
        查看日志
      </button>
      <button
        v-if="feedback.taskId"
        class="account-text-action"
        type="button"
        @click="loadAccounts"
      >
        刷新列表
      </button>
      <button
        v-if="feedback.tone === 'error' && lastRetry"
        class="account-text-action"
        type="button"
        @click="retryLast"
      >
        重试
      </button>
      <button
        class="account-icon-button"
        type="button"
        aria-label="关闭反馈"
        @click="store.clearFeedback"
      >
        <span class="material-symbols-outlined">close</span>
      </button>
    </div>

    <AccountCreationWizard
      ref="wizardRef"
      :initial-account="wizardAccount"
      :open="wizardOpen"
      @completed="handleWizardCompleted"
      @open-dependency="openDependency"
      @open-log="showLog"
      @request-close="requestWizardClose"
    />

    <AccountArchiveDialog
      :account="archiveTarget"
      :busy="Boolean(busyKey)"
      :open="Boolean(archiveTarget)"
      @close="archiveTarget = null"
      @confirm="confirmArchive"
    />

    <AccountCopyConfigDialog
      :accounts="accounts"
      :busy="Boolean(busyKey)"
      :open="Boolean(copyTarget)"
      :target="copyTarget"
      @close="copyTarget = null"
      @submit="confirmCopy"
    />

    <div
      v-if="visibleLogId"
      class="account-modal-backdrop"
      @click.self="visibleLogId = null"
    >
      <section class="account-dialog" role="dialog" aria-modal="true">
        <header>
          <span class="account-dialog__icon material-symbols-outlined">receipt_long</span>
          <div>
            <h2>操作日志标识</h2>
            <p>请使用此标识在 Runtime 日志中定位完整异常记录。</p>
          </div>
        </header>
        <code class="account-log-id">{{ visibleLogId }}</code>
        <footer>
          <button
            class="account-button is-primary"
            type="button"
            @click="visibleLogId = null"
          >
            知道了
          </button>
        </footer>
      </section>
    </div>

    <div
      v-if="showUnsavedConfirm"
      class="account-modal-backdrop"
      @click.self="cancelUnsavedConfirm"
    >
      <section class="account-dialog" role="alertdialog" aria-modal="true">
        <header>
          <span class="account-dialog__icon material-symbols-outlined">edit_note</span>
          <div>
            <h2>保留未保存内容？</h2>
            <p>你可以保存当前输入、放弃修改，或返回继续编辑。</p>
          </div>
        </header>
        <footer>
          <button
            class="account-button is-secondary"
            type="button"
            @click="cancelUnsavedConfirm"
          >
            返回
          </button>
          <button class="account-button is-danger" type="button" @click="discardAndClose">
            放弃
          </button>
          <button
            class="account-button is-primary"
            type="button"
            :disabled="Boolean(busyKey)"
            @click="saveAndClose"
          >
            保存
          </button>
        </footer>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { useAccountManagementPage } from "@/modules/accounts/use-account-management-page";
import AccountArchiveDialog from "@/modules/accounts/components/AccountArchiveDialog.vue";
import AccountCopyConfigDialog from "@/modules/accounts/components/AccountCopyConfigDialog.vue";
import AccountCreationWizard from "@/modules/accounts/components/AccountCreationWizard.vue";
import AccountDetailPanel from "@/modules/accounts/components/AccountDetailPanel.vue";
import AccountListTable from "@/modules/accounts/components/AccountListTable.vue";
import "@/modules/accounts/styles/account-management.css";

const {
  applyFilters,
  archiveTarget,
  accounts,
  busyKey,
  cancelUnsavedConfirm,
  clearFilters,
  collectionState,
  confirmArchive,
  confirmCopy,
  copyTarget,
  detailTab,
  discardAndClose,
  error,
  feedback,
  filterDraft,
  handleRecommendedAction,
  handleRecipeUpdated,
  handleWizardCompleted,
  lastRetry,
  loadAccounts,
  openArchive,
  openCopy,
  openDependency,
  openNewWizard,
  requestWizardClose,
  requestSelectAccount,
  restore,
  retryLast,
  runHealth,
  saveAndClose,
  selectedAccount,
  selectedAccountId,
  showLog,
  showUnsavedConfirm,
  store,
  visibleLogId,
  wizardAccount,
  wizardOpen,
  wizardRef
} = useAccountManagementPage();
</script>
