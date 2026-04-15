import { defineStore } from 'pinia';
import { fetchAccounts, createAccount, deleteAccount, fetchAccountGroups, refreshAccountStats } from '@/app/runtime-client';
import type { AccountDto, AccountGroupDto, AccountCreateInput } from '@/types/runtime';

export const useAccountManagementStore = defineStore('account-management', {
  state: () => ({
    accounts: [] as AccountDto[],
    groups: [] as AccountGroupDto[],
    selectedGroupId: null as string | null,
    showAddModal: false,
    status: 'idle' as 'idle' | 'loading' | 'ready' | 'error'
  }),
  actions: {
    async load() {
      this.status = 'loading';
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
        console.error('Failed to load accounts/groups', e);
      }
    },
    async addAccount(input: AccountCreateInput) {
      try {
        const newAccount = await createAccount(input);
        this.accounts.push(newAccount);
        this.showAddModal = false;
      } catch (e) {
        console.error('Failed to create account', e);
      }
    },
    async removeAccount(id: string) {
      try {
        await deleteAccount(id);
        this.accounts = this.accounts.filter(a => a.id !== id);
      } catch (e) {
        console.error('Failed to delete account', e);
      }
    },
    async refreshStats(id: string) {
      try {
        await refreshAccountStats(id);
        // Refresh local account data after request is sent
        // Note: Backend handles this asynchronously, but we might want to reload list
        await this.load();
      } catch (e) {
        console.error('Failed to refresh stats', e);
      }
    },
    setSelectedGroup(groupId: string | null) {
      this.selectedGroupId = groupId;
      this.load();
    }
  }
});
