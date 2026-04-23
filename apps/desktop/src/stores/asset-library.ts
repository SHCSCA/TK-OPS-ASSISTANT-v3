import { defineStore } from "pinia";

import {
  fetchAsset,
  deleteAsset as deleteRuntimeAsset,
  fetchAssetReferences,
  fetchAssets,
  importAsset
} from "@/app/runtime-client";
import type { AssetDto, AssetImportInput, AssetReferenceDto } from "@/types/runtime";
import {
  resolveCollectionStatus,
  toRuntimeErrorMessage
} from "@/stores/runtime-store-helpers";

type LoadStatus = "idle" | "loading" | "empty" | "ready" | "error";
type ImportStatus = "idle" | "importing" | "succeeded" | "failed";
type DeleteStatus = "idle" | "checking" | "blocked" | "deleting" | "ready" | "error";
type ReferenceStatus = "idle" | "loading" | "ready" | "blocked" | "error";

function getErrorMessage(error: unknown): string {
  return toRuntimeErrorMessage(error, "资产操作失败，请稍后重试。");
}

function upsertAsset(assets: AssetDto[], next: AssetDto): AssetDto[] {
  const exists = assets.some((asset) => asset.id === next.id);
  if (!exists) return [next, ...assets];
  return assets.map((asset) => (asset.id === next.id ? next : asset));
}

export const useAssetLibraryStore = defineStore("asset-library", {
  state: () => ({
    assets: [] as AssetDto[],
    assetDetailsById: {} as Record<string, AssetDto>,
    filter: { type: "", q: "" },
    selectedId: null as string | null,
    status: "idle" as LoadStatus,
    error: null as string | null,
    references: [] as AssetReferenceDto[],
    referenceStatus: "idle" as ReferenceStatus,
    importStatus: "idle" as ImportStatus,
    importError: null as string | null,
    deleteStatus: "idle" as DeleteStatus,
    deleteError: null as string | null
  }),
  getters: {
    selectedAsset(state): AssetDto | null {
      return (state.selectedId ? state.assetDetailsById[state.selectedId] : null) ??
        state.assets.find((asset) => asset.id === state.selectedId) ??
        null;
    },
    viewState(state): "loading" | "empty" | "ready" | "error" {
      if (state.status === "loading") {
        return "loading";
      }
      if (state.status === "error") {
        return "error";
      }
      return state.assets.length > 0 ? "ready" : "empty";
    },
    deleteState(state): DeleteStatus {
      return state.deleteStatus;
    }
  },
  actions: {
    async load() {
      this.status = "loading";
      this.error = null;
      try {
        this.assets = await fetchAssets(this.filter.type || undefined, this.filter.q || undefined);
        this.assetDetailsById = Object.fromEntries(this.assets.map((asset) => [asset.id, asset]));
        if (this.selectedId && !this.assets.some((asset) => asset.id === this.selectedId)) {
          this.selectedId = null;
          this.references = [];
          this.referenceStatus = "idle";
        }
        this.status = resolveCollectionStatus(this.assets.length);
      } catch (error) {
        this.status = "error";
        this.error = getErrorMessage(error);
      }
    },
    async importLocalFile(input: AssetImportInput): Promise<AssetDto> {
      this.importStatus = "importing";
      this.importError = null;
      this.error = null;
      try {
        const imported = await importAsset({
          source: "local",
          ...input
        });
        this.assets = upsertAsset(this.assets, imported);
        this.assetDetailsById = {
          ...this.assetDetailsById,
          [imported.id]: imported
        };
        this.selectedId = imported.id;
        this.references = [];
        this.referenceStatus = "idle";
        this.importStatus = "succeeded";
        this.status = "ready";
        return imported;
      } catch (error) {
        this.importStatus = "failed";
        this.importError = getErrorMessage(error);
        throw error;
      }
    },
    parseTags(asset: AssetDto): string[] {
      if (!asset.tags) return [];
      try {
        const parsed = JSON.parse(asset.tags) as unknown;
        return Array.isArray(parsed)
          ? parsed.filter((tag): tag is string => typeof tag === "string" && tag.trim().length > 0)
          : [];
      } catch {
        return [];
      }
    },
    async prepareDelete(id: string): Promise<boolean> {
      this.selectedId = id;
      this.deleteError = null;
      this.deleteStatus = "checking";
      this.error = null;
      try {
        const asset = this.assetDetailsById[id] || await fetchAsset(id);
        if (asset.referenceSummary?.blockingDelete) {
          this.references = await fetchAssetReferences(id);
          this.deleteError = `资产已被引用且禁止删除，请先处理 ${asset.referenceSummary.total} 条引用后再试`;
          this.deleteStatus = "blocked";
          return false;
        }
        this.deleteStatus = "ready";
        return true;
      } catch (error) {
        this.references = [];
        this.deleteError = getErrorMessage(error);
        this.deleteStatus = "error";
        return false;
      }
    },
    async deleteSelected() {
      if (!this.selectedId) {
        this.deleteError = "请先选择要删除的资产";
        return;
      }

      const id = this.selectedId;
      this.deleteStatus = "deleting";
      this.deleteError = null;
      this.error = null;
      try {
        await deleteRuntimeAsset(id);
        this.assets = this.assets.filter((asset) => asset.id !== id);
        delete this.assetDetailsById[id];
        this.selectedId = null;
        this.references = [];
        this.referenceStatus = "idle";
        this.deleteStatus = "ready";
        this.status = this.assets.length > 0 ? "ready" : "empty";
      } catch (error) {
        this.deleteError = getErrorMessage(error);
        this.deleteStatus = "error";
      }
    },
    async delete(id: string) {
      this.error = null;
      this.deleteStatus = "deleting";
      try {
        await deleteRuntimeAsset(id);
        this.assets = this.assets.filter((asset) => asset.id !== id);
        delete this.assetDetailsById[id];
        if (this.selectedId === id) {
          this.selectedId = null;
          this.references = [];
          this.referenceStatus = "idle";
        }
        this.deleteStatus = "ready";
        this.status = this.assets.length > 0 ? "ready" : "empty";
      } catch (error) {
        this.error = getErrorMessage(error);
        this.deleteStatus = "error";
      }
    },
    async select(id: string | null) {
      this.selectedId = id;
      this.error = null;
      if (!id) {
        this.references = [];
        this.referenceStatus = "idle";
        return;
      }

      try {
        this.referenceStatus = "loading";
        const [asset, references] = await Promise.all([
          fetchAsset(id),
          fetchAssetReferences(id)
        ]);
        this.assetDetailsById = {
          ...this.assetDetailsById,
          [id]: asset
        };
        this.assets = upsertAsset(this.assets, asset);
        this.references = references;
        this.referenceStatus = references.length > 0 ? "blocked" : "ready";
      } catch (error) {
        this.references = [];
        this.referenceStatus = "error";
        this.error = getErrorMessage(error);
      }
    },
    setFilterType(type: string) {
      this.filter.type = type;
      return this.load();
    },
    setSearchQuery(q: string) {
      this.filter.q = q;
      return this.load();
    }
  }
});
