import { useEffect, useMemo, useState } from "react";
import { prototypeConfig } from "../config/prototypeConfig.js";
import { assetPurposeOptions, assetSourceOptions, assetStatusOptions, assetTypeOptions, filterAssets } from "../data/assets.js";

const initialFilters = { purpose: "", query: "", source: "", status: "", type: prototypeConfig.library.defaultType };

export function useAssetLibraryState(activeAccountId, workflow) {
  const [filters, setFilters] = useState(initialFilters);
  const [sort, setSort] = useState(prototypeConfig.library.defaultSort);
  const visibleAssets = useMemo(() => {
    const filtered = filterAssets(workflow.assets, filters);
    if (sort === "name") return [...filtered].sort((a, b) => a.title.localeCompare(b.title));
    if (sort === "type") return [...filtered].sort((a, b) => a.type.localeCompare(b.type));
    return filtered;
  }, [filters, sort, workflow.assets]);

  useEffect(() => {
    setFilters(initialFilters);
    setSort(prototypeConfig.library.defaultSort);
  }, [activeAccountId]);

  function setFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function clearFilter(field) {
    setFilter(field, field === "type" ? "all" : "");
  }

  function clearAllFilters() {
    setFilters(initialFilters);
  }

  return {
    allAssets: workflow.assets,
    clearFilter,
    clearAllFilters,
    filters,
    options: { purposes: assetPurposeOptions, sources: assetSourceOptions, statuses: assetStatusOptions, types: assetTypeOptions },
    setFilter,
    setSort,
    sort,
    visibleAssets,
  };
}
