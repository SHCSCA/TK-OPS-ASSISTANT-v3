import { defineStore } from "pinia";

import {
  deleteAsset as deleteRuntimeAsset,
  fetchAssetReferences,
  fetchAssets,
  importAsset
} from "@/app/runtime-client";
import type { AssetDto, AssetImportInput, AssetReferenceDto } from "@/types/runtime";

type LoadStatus = "idle" | "loading" | "ready" | "error";
type ImportStatus = "idle" | "importing" | "succeeded" | "failed";

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "资产操作失败";
}

function upsertAsset(assets: AssetDto[], next: AssetDto): AssetDto[] {
  const exists = assets.some((asset) => asset.id === next.id);
  if (!exists) return [next, ...assets];
  return assets.map((asset) => (asset.id === next.id ? next : asset));
}

export const useAssetLibraryStore = defineStore("asset-library", {
  state: () => ({
    assets: [] as AssetDto[],
    filter: { type: "", q: "" },
    selectedId: null as string | null,
    status: "idle" as LoadStatus,
    error: null as string | null,
    references: [] as AssetReferenceDto[],
    importStatus: "idle" as ImportStatus,
    importError: null as string | null,
    deleteError: null as string | null
  }),
  actions: {
    async load() {
      this.status = "loading";
      this.error = null;
      try {
        this.assets = await fetchAssets(this.filter.type || undefined, this.filter.q || undefined);
        this.status = "ready";
      } catch (error) {
        this.status = "error";
        this.error = getErrorMessage(error);
        console.error("资产列表加载失败", error);
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
        this.selectedId = imported.id;
        this.references = [];
        this.importStatus = "succeeded";
        return imported;
      } catch (error) {
        this.importStatus = "failed";
        this.importError = getErrorMessage(error);
        console.error("资产导入失败", error);
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
      this.error = null;
      try {
        this.references = await fetchAssetReferences(id);
        if (this.references.length > 0) {
          this.deleteError = `资产存在引用，请先处理 ${this.references.length} 条引用后再删除`;
          return false;
        }
        return true;
      } catch (error) {
        this.references = [];
        this.deleteError = getErrorMessage(error);
        console.error("资产引用检查失败", error);
        return false;
      }
    },
    async deleteSelected() {
      if (!this.selectedId) {
        this.deleteError = "请先选择要删除的资产";
        return;
      }

      const id = this.selectedId;
      this.deleteError = null;
      this.error = null;
      try {
        await deleteRuntimeAsset(id);
        this.assets = this.assets.filter((asset) => asset.id !== id);
        this.selectedId = null;
        this.references = [];
      } catch (error) {
        this.deleteError = getErrorMessage(error);
        console.error("资产删除失败", error);
      }
    },
    async delete(id: string) {
      this.error = null;
      try {
        await deleteRuntimeAsset(id);
        this.assets = this.assets.filter((asset) => asset.id !== id);
        if (this.selectedId === id) {
          this.selectedId = null;
          this.references = [];
        }
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("资产删除失败", error);
      }
    },
    async select(id: string | null) {
      this.selectedId = id;
      this.error = null;
      if (!id) {
        this.references = [];
        return;
      }

      try {
        this.references = await fetchAssetReferences(id);
      } catch (error) {
        this.references = [];
        this.error = getErrorMessage(error);
        console.error("资产引用加载失败", error);
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
