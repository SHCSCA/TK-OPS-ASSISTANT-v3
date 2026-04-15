import { defineStore } from 'pinia';
import { fetchAssets, deleteAsset, fetchAssetReferences } from '@/app/runtime-client';
import type { AssetDto, AssetReferenceDto } from '@/types/runtime';

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '资产操作失败';
}

export const useAssetLibraryStore = defineStore('asset-library', {
  state: () => ({
    assets: [] as AssetDto[],
    filter: { type: '', q: '' },
    selectedId: null as string | null,
    status: 'idle' as 'idle' | 'loading' | 'ready' | 'error',
    error: null as string | null,
    references: [] as AssetReferenceDto[]
  }),
  actions: {
    async load() {
      this.status = 'loading';
      this.error = null;
      try {
        this.assets = await fetchAssets(this.filter.type || undefined, this.filter.q || undefined);
        this.status = 'ready';
      } catch (e) {
        this.status = 'error';
        this.error = getErrorMessage(e);
        console.error('Failed to load assets', e);
      }
    },
    async delete(id: string) {
      this.error = null;
      try {
        await deleteAsset(id);
        this.assets = this.assets.filter(a => a.id !== id);
        if (this.selectedId === id) {
          this.selectedId = null;
          this.references = [];
        }
      } catch (e) {
        this.error = getErrorMessage(e);
        console.error('Failed to delete asset', e);
      }
    },
    async select(id: string | null) {
      this.selectedId = id;
      this.error = null;
      if (id) {
        try {
          this.references = await fetchAssetReferences(id);
        } catch (e) {
          this.references = [];
          this.error = getErrorMessage(e);
          console.error('Failed to fetch asset references', e);
        }
      } else {
        this.references = [];
      }
    },
    setFilterType(type: string) {
      this.filter.type = type;
      this.load();
    },
    setSearchQuery(q: string) {
      this.filter.q = q;
      this.load();
    }
  }
});
