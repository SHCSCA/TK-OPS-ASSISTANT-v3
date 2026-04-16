import { defineStore } from 'pinia';
import { fetchAccounts, createAccount, deleteAccount, fetchAccountGroups, refreshAccountStats } from '@/app/runtime-client';
import type { AccountDto, AccountGroupDto, AccountCreateInput } from '@/types/runtime';

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '账号操作失败';
}

export const useAccountManagementStore = defineStore('account-management', {
  state: () => ({
    accounts: [] as AccountDto[],
    groups: [] as AccountGroupDto[],
    selectedGroupId: null as string | null,
    showAddModal: false,
    status: 'idle' as 'idle' | 'loading' | 'ready' | 'error',
    error: null as string | null
  }),
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
        this.status = 'ready';
      } catch (e) {
        this.status = 'error';
        this.error = getErrorMessage(e);
        console.error('Failed to load accounts/groups', e);
      }
    },
    async addAccount(input: AccountCreateInput) {
      this.error = null;
      try {
        const newAccount = await createAccount(input);
        this.accounts.push(newAccount);
        this.showAddModal = false;
      } catch (e) {
        this.error = getErrorMessage(e);
        console.error('Failed to create account', e);
      }
    },
    async removeAccount(id: string) {
      this.error = null;
      try {
        await deleteAccount(id);
        this.accounts = this.accounts.filter(a => a.id !== id);
      } catch (e) {
        this.error = getErrorMessage(e);
        console.error('Failed to delete account', e);
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
        console.error('Failed to refresh stats', e);
      }
    },
    setSelectedGroup(groupId: string | null) {
      this.selectedGroupId = groupId;
      this.load();
    }
  }
});
