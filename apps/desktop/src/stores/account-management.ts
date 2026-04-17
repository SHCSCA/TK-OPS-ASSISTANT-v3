import { defineStore } from 'pinia';
import { fetchAccounts, createAccount, deleteAccount, fetchAccountGroups, refreshAccountStats } from '@/app/runtime-client';
import type { AccountDto, AccountGroupDto, AccountCreateInput } from '@/types/runtime';
import { resolveCollectionStatus, toRuntimeErrorMessage } from "@/stores/runtime-store-helpers";

function getErrorMessage(error: unknown): string {
  return toRuntimeErrorMessage(error, '账号操作失败，请稍后重试。');
}

export const useAccountManagementStore = defineStore('account-management', {
  state: () => ({
    accounts: [] as AccountDto[],
    groups: [] as AccountGroupDto[],
    selectedGroupId: null as string | null,
    showAddModal: false,
    status: 'idle' as 'idle' | 'loading' | 'empty' | 'ready' | 'error',
    error: null as string | null
  }),
  getters: {
    viewState: (state): "loading" | "empty" | "ready" | "error" => {
      if (state.status === "loading") return "loading";
      if (state.status === "error") return "error";
      return state.accounts.length > 0 ? "ready" : "empty";
    }
  },
  actions: {
    async load() {
      this.status = 'loading';
      this.error = null;
      try {
        const [accounts, groups] = await Promise.all([
          fetchAccounts(this.selectedGroupId || undefined),
          fetchAccountGroups()
        ]);
        this.accounts = accounts;
        this.groups = groups;
        this.status = resolveCollectionStatus(accounts.length);
      } catch (e) {
        this.status = 'error';
        this.error = getErrorMessage(e);
      }
    },
    async addAccount(input: AccountCreateInput) {
      this.error = null;
      try {
        const newAccount = await createAccount(input);
        this.accounts.push(newAccount);
        this.status = "ready";
        this.showAddModal = false;
      } catch (e) {
        this.error = getErrorMessage(e);
      }
    },
    async removeAccount(id: string) {
      this.error = null;
      try {
        await deleteAccount(id);
        this.accounts = this.accounts.filter(a => a.id !== id);
        this.status = this.accounts.length > 0 ? "ready" : "empty";
      } catch (e) {
        this.error = getErrorMessage(e);
      }
    },
    async refreshStats(id: string) {
      this.error = null;
      try {
        await refreshAccountStats(id);
        // 后端刷新统计后重新拉取账号列表，保持本地状态与 Runtime 一致。
        await this.load();
      } catch (e) {
        this.error = getErrorMessage(e);
      }
    },
    setSelectedGroup(groupId: string | null) {
      this.selectedGroupId = groupId;
      this.load();
    }
  }
});
